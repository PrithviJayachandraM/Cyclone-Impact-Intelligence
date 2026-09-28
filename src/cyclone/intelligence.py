"""Grounded Phase 5 cyclone briefing and question-answering service.

The assistant deliberately obtains all facts through narrow backend tools.  A
model receives the resulting structured context only; it has no direct access
to BigQuery, local files, or browser-supplied credentials.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen

from cyclone.enrichment import EnrichmentRepository
from cyclone.forecast import ForecastRepository
from cyclone.repository import HistoricalTrackRepository
from cyclone.risk import RiskRepository


class GeminiUnavailable(RuntimeError):
    """Raised when an optional configured Gemini request cannot be completed."""


class NarrativeResponder(Protocol):
    def respond(self, question: str, context: dict[str, object]) -> str: ...


class VertexGeminiResponder:
    """Small Vertex REST adapter, used only when explicitly configured."""

    def __init__(self, project_id: str, region: str, model: str, access_token: str) -> None:
        self.project_id, self.region, self.model, self.access_token = project_id, region, model, access_token

    def respond(self, question: str, context: dict[str, object]) -> str:
        prompt = (
            "Answer only from the supplied structured context. State whether values are observed or forecast, "
            "do not add facts or numerical values, and never issue an official warning or evacuation order. "
            f"Question: {question}\nStructured context: {json.dumps(context, separators=(',', ':'))}"
        )
        endpoint = (
            f"https://{self.region}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/"
            f"{self.region}/publishers/google/models/{self.model}:generateContent"
        )
        request = Request(endpoint, data=json.dumps({"contents": [{"role": "user", "parts": [{"text": prompt}]}]}).encode(), headers={"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=15) as response:  # nosec B310 - HTTPS endpoint is constructed above
                payload = json.loads(response.read().decode("utf-8"))
            return str(payload["candidates"][0]["content"]["parts"][0]["text"]).strip()
        except (KeyError, IndexError, OSError, URLError, ValueError) as error:
            raise GeminiUnavailable("Vertex Gemini did not return a usable response") from error


class AdvisoryRepository:
    """Curated, approved advisory references.  This is intentionally read-only."""

    def __init__(self, data_directory: Path) -> None:
        self.advisories: list[dict[str, object]] = json.loads((data_directory / "approved_advisories.json").read_text(encoding="utf-8"))["advisories"]

    def search(self, cyclone_id: str, query: str) -> list[dict[str, object]]:
        terms = {term for term in query.lower().split() if len(term) > 2}
        matches = [advisory for advisory in self.advisories if advisory.get("cyclone_id") in {None, cyclone_id} and advisory.get("approved")]
        ranked = [advisory for advisory in matches if terms.intersection(str(advisory.get("topics", "")).lower().split())]
        return ranked or matches


@dataclass(frozen=True)
class GroundedAssistant:
    tracks: HistoricalTrackRepository
    enrichment: EnrichmentRepository
    risk: RiskRepository
    forecast: ForecastRepository
    advisories: AdvisoryRepository
    responder: NarrativeResponder | None = None

    def answer(self, question: str, cyclone_id: str, valid_time: str | None = None) -> dict[str, object] | None:
        event = next((item for item in self.tracks.list_events() if item["cyclone_id"] == cyclone_id), None)
        if event is None:
            return None
        cleaned = question.strip()
        if not cleaned:
            raise ValueError("question is required")
        if len(cleaned) > 500:
            raise ValueError("question must be at most 500 characters")
        tool = self._select_tool(cleaned)
        if tool == "unsupported":
            return self._unsupported(cleaned, event)
        context = self._context(event, valid_time, tool, cleaned)
        answer = self._local_answer(tool, context)
        provider = "local-grounded"
        if self.responder:
            try:
                candidate = self.responder.respond(cleaned, context)
                if self._safe_narrative(candidate, context):
                    answer, provider = candidate, "vertex-gemini"
            except GeminiUnavailable:
                provider = "local-fallback"
        return {"answer": answer, "supported": True, "tool": tool, "provider": provider, "context": context, "evidence": context["evidence"], "uncertainty": context["uncertainty"], "safety_notice": "Decision-support only. Official IMD and local government guidance remains authoritative."}

    @staticmethod
    def _select_tool(question: str) -> str:
        lower = question.lower()
        if any(word in lower for word in ("evacuat", "order", "route", "shelter", "alert")):
            return "unsupported"
        if any(word in lower for word in ("advis", "guidance", "official")):
            return "search_advisories"
        if any(word in lower for word in ("exposure", "population", "highest")):
            return "get_exposure_summary"
        if any(word in lower for word in ("why", "risk", "high")):
            return "get_location_risk"
        if any(word in lower for word in ("summar", "current", "situation", "status", "state", "track", "forecast", "cyclone")):
            return "get_cyclone_state"
        return "unsupported"

    def _context(self, event: dict[str, object], valid_time: str | None, tool: str, question: str) -> dict[str, object]:
        track = self.tracks.track_geojson(str(event["cyclone_id"])) or {"features": []}
        observed = [feature for feature in track["features"] if feature["geometry"]["type"] == "Point"]
        latest_feature = max(observed, key=lambda feature: str(feature["properties"]["timestamp"]))
        latest_observed = {
            **latest_feature["properties"],
            "longitude": latest_feature["geometry"]["coordinates"][0],
            "latitude": latest_feature["geometry"]["coordinates"][1],
        }
        selected_time = valid_time or str(latest_observed["timestamp"])
        risk_features = self.risk.risk_geojson(str(event["cyclone_id"]), selected_time)["features"]
        if not risk_features:
            selected_time = str(latest_observed["timestamp"])
            risk_features = self.risk.risk_geojson(str(event["cyclone_id"]), selected_time)["features"]
        scores = [feature["properties"] for feature in risk_features]
        locations = self.enrichment.locations_geojson(str(event["cyclone_id"]))["features"]
        evidence = [{"kind": "cyclone_state", "source": event["source"], "timestamp": latest_observed["timestamp"], "source_type": "observed"}, {"kind": "risk", "source": "Phase 3 deterministic risk baseline", "timestamp": selected_time, "processing_version": scores[0]["model_version"] if scores else None, "source_type": scores[0]["source_type"] if scores else None}]
        context: dict[str, object] = {"cyclone": event, "latest_observed_state": latest_observed, "selected_valid_time": selected_time, "risk_scores": scores, "affected_locations": locations, "evidence": evidence, "uncertainty": ["Risk scores are a deterministic demonstration baseline, not calibrated impact predictions."]}
        forecast = next((point for point in self.forecast.forecast(str(event["cyclone_id"])) if point["valid_time"] == selected_time), None)
        if forecast:
            context["forecast"] = forecast
            context["uncertainty"].append(f"Selected state is a {forecast['horizon_hours']}-hour forecast with ±{forecast['uncertainty_km']} km track uncertainty.")
            evidence.append({"kind": "forecast", "source": "Phase 4 constant-velocity baseline", "timestamp": forecast["forecast_created_at"], "valid_time": forecast["valid_time"], "processing_version": forecast["model_version"], "source_type": "forecast"})
        if tool == "search_advisories":
            advisories = self.advisories.search(str(event["cyclone_id"]), question)
            context["advisories"] = advisories
            evidence.extend({"kind": "advisory", "source": item["source"], "timestamp": item["published_at"], "url": item["url"]} for item in advisories)
        return context

    @staticmethod
    def _local_answer(tool: str, context: dict[str, object]) -> str:
        scores = list(context["risk_scores"])
        highest = max(scores, key=lambda score: int(score["risk_score"])) if scores else None
        locations = {item["properties"]["location_id"]: item["properties"] for item in context["affected_locations"]}
        if tool == "get_location_risk" and highest:
            factors = sorted(highest["feature_contributions"], key=lambda item: float(item["score_points"]), reverse=True)[:2]
            return f"{locations[highest['location_id']]['name']} has the highest listed risk at {highest['risk_score']}/100 ({highest['band']}) for {highest['valid_time']}. Its largest baseline contributors are {factors[0]['name']} ({factors[0]['score_points']} points) and {factors[1]['name']} ({factors[1]['score_points']} points). This is {highest['source_type']} data."
        if tool == "get_exposure_summary":
            populated = max(context["affected_locations"], key=lambda item: item["properties"]["feature_values"]["population"])
            values = populated["properties"]["feature_values"]
            return f"{populated['properties']['name']} has the highest listed demonstration population exposure: {values['population']} people. Its selected-time risk score is {next(score['risk_score'] for score in scores if score['location_id'] == populated['properties']['location_id'])}/100."
        if tool == "search_advisories":
            advisories = list(context.get("advisories", []))
            return str(advisories[0]["guidance"]) if advisories else "No approved advisory is available for this question. Consult current IMD and local government guidance."
        observed = context["latest_observed_state"]
        state = f"{context['cyclone']['name']} was last observed at {observed['timestamp']} near {observed['latitude']}, {observed['longitude']} with {observed['wind_speed_kph']} km/h wind."
        if "forecast" in context:
            forecast = context["forecast"]
            state += f" The selected {forecast['horizon_hours']}-hour forecast is valid at {forecast['valid_time']} and has ±{forecast['uncertainty_km']} km track uncertainty."
        return state + " The listed risk scores are baseline decision-support outputs, not official warnings."

    @staticmethod
    def _safe_narrative(candidate: str, context: dict[str, object]) -> bool:
        prohibited = ("evacuate", "evacuation order", "official warning", "must leave")
        allowed_numbers = set(re.findall(r"\d+(?:\.\d+)?", json.dumps(context)))
        candidate_numbers = set(re.findall(r"\d+(?:\.\d+)?", candidate))
        return bool(candidate and len(candidate) <= 2000 and candidate_numbers.issubset(allowed_numbers) and not any(term in candidate.lower() for term in prohibited))

    @staticmethod
    def _unsupported(question: str, event: dict[str, object]) -> dict[str, object]:
        return {"answer": "I cannot issue evacuation orders, alerts, routes, or other operational instructions. Consult current IMD bulletins and local government authorities.", "supported": False, "tool": None, "provider": "safety-boundary", "context": {"cyclone": event, "question": question}, "evidence": [], "uncertainty": ["The prototype is not an official warning or evacuation authority."], "safety_notice": "Official IMD and local government guidance remains authoritative."}
