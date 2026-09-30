"""Reusable Phase 8 feasibility checks for the frozen local replay dataset."""

from __future__ import annotations

import statistics
import time
from datetime import datetime
from typing import Callable

from cyclone.enrichment import EnrichmentRepository
from cyclone.intelligence import GroundedAssistant
from cyclone.repository import HistoricalTrackRepository
from cyclone.scenario import ScenarioParameters, ScenarioService


def data_quality_report(tracks: HistoricalTrackRepository, enrichment: EnrichmentRepository) -> dict[str, object]:
    events = tracks.list_events()
    points = tracks.points
    issues: list[str] = []
    required_event = {"cyclone_id", "name", "basin", "source", "observed_at"}
    required_point = {"cyclone_id", "timestamp", "latitude", "longitude", "wind_speed_kph", "pressure_hpa", "source_type"}
    for event in events:
        if required_event - set(event):
            issues.append(f"event {event.get('cyclone_id', '<unknown>')} is missing required fields")
        _parse_timestamp(str(event.get("observed_at", "")), issues, "event observed_at")
    seen = set()
    ordered_by_cyclone: dict[str, list[str]] = {}
    for point in points:
        if required_point - set(point):
            issues.append(f"track point {point.get('timestamp', '<unknown>')} is missing required fields")
        cyclone_id, timestamp = str(point.get("cyclone_id", "")), str(point.get("timestamp", ""))
        key = (cyclone_id, timestamp)
        if key in seen:
            issues.append(f"duplicate observation {cyclone_id} {timestamp}")
        seen.add(key)
        ordered_by_cyclone.setdefault(cyclone_id, []).append(timestamp)
        _parse_timestamp(timestamp, issues, "track timestamp")
        if not -90 <= float(point.get("latitude", 999)) <= 90 or not -180 <= float(point.get("longitude", 999)) <= 180:
            issues.append(f"invalid coordinates at {timestamp}")
    for cyclone_id, timestamps in ordered_by_cyclone.items():
        if timestamps != sorted(timestamps):
            issues.append(f"track timestamps are not ordered for {cyclone_id}")
    feature_count = 0
    required_layers = {"rainfall", "elevation", "population"}
    for layer in enrichment.layers_metadata:
        if any(not layer.get(name) for name in ("source", "observed_at", "resolution", "processing_version")):
            issues.append(f"layer {layer.get('layer_id')} is missing provenance metadata")
        _parse_timestamp(str(layer.get("observed_at", "")), issues, "layer observed_at")
    for location in enrichment.locations:
        values = {str(item["layer_id"]): item["value"] for item in location["features"]}
        feature_count += len(values)
        if required_layers - set(values):
            issues.append(f"location {location['location_id']} is missing required feature layers")
        if any(float(value) < 0 for value in values.values()):
            issues.append(f"location {location['location_id']} has a negative feature value")
        coordinates = location["geometry"].get("coordinates", [[]])[0]
        if len(coordinates) < 4 or coordinates[0] != coordinates[-1]:
            issues.append(f"location {location['location_id']} has an invalid grid boundary")
    geometry_ready = all(tracks.track_geojson(str(event["cyclone_id"])) is not None for event in events)
    if not geometry_ready:
        issues.append("track geometry could not be constructed")
    return {"status": "pass" if not issues else "fail", "events": len(events), "track_points": len(points), "locations": len(enrichment.locations), "feature_values": feature_count, "issues": issues, "historical_replay": True, "freshness": "Historical replay data; timestamps are intentionally from 2013 and must not be presented as current observations."}


def golden_question_results(assistant: GroundedAssistant, scenarios: ScenarioService) -> list[dict[str, object]]:
    questions = [
        ("Why is this location high risk?", "get_location_risk", "risk_scores"),
        ("Which locations have the highest exposure?", "get_exposure_summary", "affected_locations"),
        ("Summarize the current cyclone situation.", "get_cyclone_state", "latest_observed_state"),
        ("What is observed versus predicted?", "get_cyclone_state", "forecast"),
        ("What is the data timestamp and source context?", "get_cyclone_state", "evidence"),
    ]
    results = []
    for question, tool, evidence_key in questions:
        answer = assistant.answer(question, "phailin-2013", "2013-10-13T06:00:00Z")
        assert answer is not None
        context = answer["context"]
        passed = answer["supported"] and answer["tool"] == tool and evidence_key in context and bool(answer["evidence"])
        results.append({"question": question, "expected_information": tool, "actual_answer": answer["answer"], "supporting_context": evidence_key, "grounding_status": "pass" if passed else "fail", "unsupported_claims": [], "pass": passed})
    scenario = scenarios.simulate("phailin-2013", ScenarioParameters(track_shift_km=20), "2013-10-13T00:00:00Z")
    assert scenario is not None
    explanation = assistant.explain_scenario(scenario)
    results.append({"question": "What happens under this simulated scenario?", "expected_information": "baseline and simulation comparison", "actual_answer": explanation["answer"], "supporting_context": "baseline, simulation_result, comparison", "grounding_status": "pass" if explanation["simulation"] and "simulation" in str(explanation["context"]).lower() else "fail", "unsupported_claims": [], "pass": explanation["simulation"]})
    unsupported = assistant.answer("What is the condition of an unlisted bridge?", "phailin-2013")
    assert unsupported is not None
    results.append({"question": "What is the condition of an unlisted bridge?", "expected_information": "safe uncertainty", "actual_answer": unsupported["answer"], "supporting_context": "safety boundary", "grounding_status": "pass" if not unsupported["supported"] else "fail", "unsupported_claims": [], "pass": not unsupported["supported"]})
    return results


def measure(operation: Callable[[], object], runs: int = 20) -> dict[str, float | int]:
    samples = []
    for _ in range(runs):
        start = time.perf_counter()
        operation()
        samples.append((time.perf_counter() - start) * 1000)
    ordered = sorted(samples)
    return {"runs": runs, "mean_ms": round(statistics.mean(samples), 3), "min_ms": round(min(samples), 3), "max_ms": round(max(samples), 3), "p95_ms": round(ordered[round((runs - 1) * 0.95)], 3)}


def _parse_timestamp(value: str, issues: list[str], label: str) -> None:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        issues.append(f"invalid {label}: {value}")
