"""Phase 7 event-driven risk alert orchestration and boundary adapters."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from cyclone.risk import RiskRepository


LOGGER = logging.getLogger(__name__)


class EventValidationError(ValueError):
    """Raised when an event payload cannot safely enter the workflow."""


class NotificationError(RuntimeError):
    """Raised when the notification boundary reports a failure."""


def _log(stage: str, event_id: str, **fields: object) -> None:
    LOGGER.info("%s", json.dumps({"stage": stage, "event_id": event_id, **fields}, sort_keys=True))


@dataclass(frozen=True)
class RiskEvaluationEvent:
    event_id: str
    cyclone_id: str
    valid_time: str | None
    source: str

    @classmethod
    def from_payload(cls, payload: object, source: str = "manual") -> "RiskEvaluationEvent":
        if not isinstance(payload, dict):
            raise EventValidationError("event payload must be an object")
        cyclone_id = payload.get("cyclone_id")
        valid_time = payload.get("valid_time")
        event_id = payload.get("event_id")
        if not isinstance(cyclone_id, str) or not cyclone_id.strip():
            raise EventValidationError("cyclone_id is required")
        if valid_time is not None and (not isinstance(valid_time, str) or not valid_time.strip()):
            raise EventValidationError("valid_time must be a non-empty string when provided")
        if event_id is None:
            event_id = hashlib.sha256(f"risk-evaluation|{cyclone_id}|{valid_time or 'latest'}".encode()).hexdigest()[:24]
        if not isinstance(event_id, str) or not event_id.strip() or len(event_id) > 128:
            raise EventValidationError("event_id must be a non-empty string of at most 128 characters")
        return cls(event_id=event_id, cyclone_id=cyclone_id, valid_time=valid_time, source=source)

    def payload(self) -> dict[str, object]:
        return {"event_id": self.event_id, "event_type": "risk-evaluation-requested", "cyclone_id": self.cyclone_id, "valid_time": self.valid_time}


class NotificationSender(Protocol):
    def send(self, alert: dict[str, object]) -> None: ...


class LocalNotificationSender:
    """Local Firebase substitute used for deterministic development and tests."""

    def __init__(self) -> None:
        self.sent: list[dict[str, object]] = []

    def send(self, alert: dict[str, object]) -> None:
        self.sent.append(alert)


class FirebaseNotificationSender:
    """Minimal Firebase Cloud Messaging HTTP v1 adapter; credentials remain external."""

    def __init__(self, project_id: str, topic: str, access_token: str) -> None:
        self.project_id, self.topic, self.access_token = project_id, topic, access_token

    def send(self, alert: dict[str, object]) -> None:
        payload = {"message": {"topic": self.topic, "notification": {"title": "Cyclone risk alert", "body": str(alert["message"])}, "data": {key: str(value) for key, value in alert.items() if value is not None and key not in {"message", "attention"}}}}
        endpoint = f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"
        request = Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers={"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=15):  # nosec B310 - fixed Firebase HTTPS origin
                return
        except (HTTPError, URLError, OSError) as error:
            raise NotificationError("Firebase notification delivery failed") from error


class AlertReceiptStore:
    """Small process-local receipt set; the key is the unchanged alert condition."""

    def __init__(self) -> None:
        self.sent_alert_ids: set[str] = set()

    def already_sent(self, alert_id: str) -> bool:
        return alert_id in self.sent_alert_ids

    def record_sent(self, alert_id: str) -> None:
        self.sent_alert_ids.add(alert_id)


class AlertWorkflow:
    def __init__(self, risk: RiskRepository, notifier: NotificationSender, threshold: int, stale_after_minutes: int, receipts: AlertReceiptStore | None = None, now: Callable[[], datetime] | None = None) -> None:
        self.risk, self.notifier, self.threshold = risk, notifier, threshold
        self.stale_after = timedelta(minutes=stale_after_minutes)
        self.receipts = receipts or AlertReceiptStore()
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.last_processed_at: datetime | None = None
        self.last_event_id: str | None = None
        self.last_result: dict[str, object] | None = None

    def process(self, event: RiskEvaluationEvent) -> dict[str, object]:
        _log("event_received", event.event_id, cyclone_id=event.cyclone_id, valid_time=event.valid_time, source=event.source)
        features = self.risk.risk_geojson(event.cyclone_id, event.valid_time)["features"]
        if not features:
            result = {"event_id": event.event_id, "status": "no_risk_data", "outcomes": []}
            return self._complete(event, result)
        outcomes = []
        for feature in features:
            score = feature["properties"]
            if int(score["risk_score"]) < self.threshold:
                outcomes.append({"location_id": score["location_id"], "status": "below_threshold", "risk_score": score["risk_score"]})
                continue
            alert = self._alert(event, score)
            if self.receipts.already_sent(str(alert["alert_id"])):
                outcomes.append({"location_id": score["location_id"], "alert_id": alert["alert_id"], "status": "duplicate_suppressed"})
                _log("duplicate_suppressed", event.event_id, alert_id=alert["alert_id"], location_id=score["location_id"])
                continue
            try:
                self.notifier.send(alert)
            except NotificationError:
                _log("notification_failed", event.event_id, alert_id=alert["alert_id"], location_id=score["location_id"])
                outcomes.append({"location_id": score["location_id"], "alert_id": alert["alert_id"], "status": "notification_failed"})
                continue
            self.receipts.record_sent(str(alert["alert_id"]))
            outcomes.append({"location_id": score["location_id"], "alert": alert, "status": "alert_sent"})
            _log("notification_sent", event.event_id, alert_id=alert["alert_id"], location_id=score["location_id"], risk_score=score["risk_score"])
        result = {"event_id": event.event_id, "status": "processed", "outcomes": outcomes}
        return self._complete(event, result)

    def handle_pubsub(self, envelope: object) -> dict[str, object]:
        if not isinstance(envelope, dict):
            raise EventValidationError("Pub/Sub envelope must be an object")
        data = envelope.get("data", envelope)
        message = data.get("message") if isinstance(data, dict) else None
        encoded = message.get("data") if isinstance(message, dict) else None
        if not isinstance(encoded, str):
            raise EventValidationError("Pub/Sub message data is required")
        try:
            payload = json.loads(base64.b64decode(encoded, validate=True).decode("utf-8"))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise EventValidationError("Pub/Sub message data must be base64-encoded JSON") from error
        return self.process(RiskEvaluationEvent.from_payload(payload, source="pubsub"))

    def status(self) -> dict[str, object]:
        stale = self.last_processed_at is None or self.now() - self.last_processed_at > self.stale_after
        return {"threshold": self.threshold, "last_event_id": self.last_event_id, "last_processed_at": self.last_processed_at.isoformat().replace("+00:00", "Z") if self.last_processed_at else None, "stale": stale, "last_result": self.last_result}

    def _complete(self, event: RiskEvaluationEvent, result: dict[str, object]) -> dict[str, object]:
        self.last_processed_at, self.last_event_id, self.last_result = self.now(), event.event_id, result
        _log("risk_evaluation_complete", event.event_id, status=result["status"])
        return result

    def _alert(self, event: RiskEvaluationEvent, score: dict[str, object]) -> dict[str, object]:
        identity = {"cyclone_id": event.cyclone_id, "valid_time": score["valid_time"], "location_id": score["location_id"], "risk_score": score["risk_score"], "threshold": self.threshold, "model_version": score["model_version"], "source_type": score["source_type"]}
        alert_id = "alert-" + hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
        source_label = "forecast" if score["source_type"] == "forecast" else "observed"
        return {"alert_id": alert_id, "alert_type": "risk_threshold_crossed", "cyclone_id": event.cyclone_id, "location_id": score["location_id"], "risk_score": score["risk_score"], "risk_band": score["band"], "threshold": self.threshold, "valid_time": score["valid_time"], "source_type": score["source_type"], "model_version": score["model_version"], "message": f"{score['band'].upper()} risk ({score['risk_score']}/100) meets the configured threshold for {score['location_id']}; this is {source_label} decision-support data.", "attention": "Review the dashboard and current official IMD guidance. This is not an official warning or evacuation instruction."}


class EventPublisher(Protocol):
    def publish(self, event: RiskEvaluationEvent) -> dict[str, object]: ...


class LocalEventPublisher:
    def __init__(self, processor: Callable[[RiskEvaluationEvent], dict[str, object]]) -> None:
        self.processor = processor
        self.events: list[RiskEvaluationEvent] = []

    def publish(self, event: RiskEvaluationEvent) -> dict[str, object]:
        self.events.append(event)
        return {"delivery": "local", "result": self.processor(event)}


class PubSubEventPublisher:
    def __init__(self, project_id: str, topic: str, access_token: str) -> None:
        self.project_id, self.topic, self.access_token = project_id, topic, access_token

    def publish(self, event: RiskEvaluationEvent) -> dict[str, object]:
        encoded = base64.b64encode(json.dumps(event.payload(), separators=(",", ":")).encode()).decode()
        endpoint = f"https://pubsub.googleapis.com/v1/projects/{self.project_id}/topics/{self.topic}:publish"
        request = Request(endpoint, data=json.dumps({"messages": [{"data": encoded}]}).encode(), headers={"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=15):  # nosec B310 - fixed Google API HTTPS origin
                return {"delivery": "pubsub", "event_id": event.event_id, "status": "published"}
        except (HTTPError, URLError, OSError) as error:
            raise NotificationError("Pub/Sub publishing failed") from error
