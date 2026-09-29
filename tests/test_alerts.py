from __future__ import annotations

import base64
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from cyclone.alerts import AlertWorkflow, EventValidationError, FirebaseNotificationSender, LocalNotificationSender, NotificationError, RiskEvaluationEvent
from cyclone.enrichment import EnrichmentRepository
from cyclone.risk import RiskRepository


class AlertWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).parents[1]
        enrichment = EnrichmentRepository(root / "data" / "enriched")
        cls.risk = RiskRepository(root / "data" / "risk", enrichment.locations)

    @staticmethod
    def event(event_id: str = "event-1") -> RiskEvaluationEvent:
        return RiskEvaluationEvent.from_payload({"event_id": event_id, "cyclone_id": "phailin-2013", "valid_time": "2013-10-13T00:00:00Z"})

    def test_threshold_boundary_and_multiple_locations(self) -> None:
        notifier = LocalNotificationSender()
        at_boundary = AlertWorkflow(self.risk, notifier, threshold=85, stale_after_minutes=60)
        result = at_boundary.process(self.event())
        self.assertEqual(result["outcomes"][0]["status"], "alert_sent")
        self.assertEqual(result["outcomes"][1]["status"], "below_threshold")
        below = AlertWorkflow(self.risk, LocalNotificationSender(), threshold=86, stale_after_minutes=60)
        self.assertEqual([item["status"] for item in below.process(self.event("event-2"))["outcomes"]], ["below_threshold", "below_threshold"])
        all_locations = AlertWorkflow(self.risk, LocalNotificationSender(), threshold=0, stale_after_minutes=60)
        self.assertEqual([item["status"] for item in all_locations.process(self.event("event-3"))["outcomes"]], ["alert_sent", "alert_sent"])

    def test_duplicate_delivery_sends_only_one_notification(self) -> None:
        notifier = LocalNotificationSender()
        workflow = AlertWorkflow(self.risk, notifier, threshold=67, stale_after_minutes=60)
        self.assertEqual(workflow.process(self.event())["outcomes"][0]["status"], "alert_sent")
        self.assertEqual(workflow.process(self.event())["outcomes"][0]["status"], "duplicate_suppressed")
        self.assertEqual(len(notifier.sent), 1)

    def test_valid_and_malformed_pubsub_messages(self) -> None:
        notifier = LocalNotificationSender()
        workflow = AlertWorkflow(self.risk, notifier, threshold=67, stale_after_minutes=60)
        encoded = base64.b64encode(json.dumps(self.event().payload()).encode()).decode()
        self.assertEqual(workflow.handle_pubsub({"data": {"message": {"data": encoded}}})["status"], "processed")
        for payload in ({}, {"message": {"data": "not base64"}}, {"message": {"data": base64.b64encode(b"[]").decode()}}):
            with self.assertRaises(EventValidationError):
                workflow.handle_pubsub(payload)

    def test_notification_failure_is_visible_and_not_recorded_as_sent(self) -> None:
        class FailingNotifier:
            def send(self, alert: dict[str, object]) -> None:
                raise NotificationError("temporary failure")

        workflow = AlertWorkflow(self.risk, FailingNotifier(), threshold=67, stale_after_minutes=60)
        result = workflow.process(self.event())
        self.assertEqual(result["outcomes"][0]["status"], "notification_failed")
        self.assertFalse(workflow.receipts.already_sent(result["outcomes"][0]["alert_id"]))

    def test_event_validation_and_stale_status(self) -> None:
        with self.assertRaises(EventValidationError):
            RiskEvaluationEvent.from_payload({"cyclone_id": ""})
        with self.assertRaises(EventValidationError):
            RiskEvaluationEvent.from_payload({"cyclone_id": "phailin-2013", "event_id": "x" * 129})
        now = lambda: datetime(2026, 1, 1, tzinfo=timezone.utc)
        workflow = AlertWorkflow(self.risk, LocalNotificationSender(), threshold=67, stale_after_minutes=60, now=now)
        self.assertTrue(workflow.status()["stale"])
        workflow.process(self.event())
        self.assertFalse(workflow.status()["stale"])

    def test_firebase_adapter_uses_configured_project_and_topic(self) -> None:
        class Response:
            def __enter__(self) -> "Response": return self
            def __exit__(self, *args: object) -> None: return None

        alert = {"message": "attention", "alert_id": "alert-1", "cyclone_id": "phailin-2013"}
        with patch("cyclone.alerts.urlopen", return_value=Response()) as request:
            FirebaseNotificationSender("demo-project", "demo-topic", "token").send(alert)
        self.assertIn("projects/demo-project/messages:send", request.call_args.args[0].full_url)
        body = json.loads(request.call_args.args[0].data)
        self.assertEqual(body["message"]["topic"], "demo-topic")
