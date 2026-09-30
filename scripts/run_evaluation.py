"""Generate the Phase 8 local feasibility evidence for the frozen demo replay."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cyclone.alerts import AlertWorkflow, LocalNotificationSender, RiskEvaluationEvent
from cyclone.enrichment import EnrichmentRepository
from cyclone.evaluation import data_quality_report, golden_question_results, measure
from cyclone.forecast import ForecastRepository
from cyclone.intelligence import AdvisoryRepository, GroundedAssistant
from cyclone.repository import HistoricalTrackRepository
from cyclone.risk import RiskRepository
from cyclone.scenario import ScenarioParameters, ScenarioService


def main() -> None:
    tracks = HistoricalTrackRepository(ROOT / "data" / "normalized")
    enrichment = EnrichmentRepository(ROOT / "data" / "enriched")
    risk = RiskRepository(ROOT / "data" / "risk", enrichment.locations)
    forecast = ForecastRepository(ROOT / "data" / "forecast")
    assistant = GroundedAssistant(tracks, enrichment, risk, forecast, AdvisoryRepository(ROOT / "data" / "advisories"))
    scenarios = ScenarioService(tracks, enrichment, risk, forecast)
    event = RiskEvaluationEvent.from_payload({"event_id": "evaluation-alert", "cyclone_id": "phailin-2013", "valid_time": "2013-10-13T00:00:00Z"})

    scenario_parameters = ScenarioParameters(track_shift_km=20, intensity_multiplier=1.2, rainfall_multiplier=1.1)
    scenario = scenarios.simulate(event.cyclone_id, scenario_parameters, event.valid_time)
    assert scenario is not None
    representative_scores = risk.risk_geojson(event.cyclone_id, event.valid_time)["features"]
    persisted_scores = [record["risk_score"] for record in risk.scores]
    alert = AlertWorkflow(risk, LocalNotificationSender(), threshold=67, stale_after_minutes=60)
    alert_result = alert.process(event)
    results = {
        "dataset": {"cyclone_id": "phailin-2013", "source": "IMD RSMC Annual Review 2013 Table 2.2.1", "observed_at": "2013-10-13T00:00:00Z", "scope": "frozen local historical replay"},
        "data_quality": data_quality_report(tracks, enrichment),
        "forecast": {"approach": "Phase 4 constant-velocity baseline; no ML-enhanced model is implemented", "evaluation": forecast.metrics("phailin-2013"), "observed_vs_forecast_ui": "observed red solid track; forecast purple dashed track; forecast risk source_type is explicit"},
        "risk": {
            "model_version": representative_scores[0]["properties"]["model_version"],
            "representative_scores": [record["properties"] for record in representative_scores],
            "persisted_score_count": len(persisted_scores),
            "range_check": all(0 <= score <= 100 for score in persisted_scores),
        },
        "scenario": {"parameters": {"track_shift_km": 20, "intensity_multiplier": 1.2, "rainfall_multiplier": 1.1}, "comparison": scenario["comparison"], "simulation_label": scenario["scenario"]["status"]},
        "alerts": {"threshold": 67, "first_delivery": alert_result, "duplicate_delivery": alert.process(event), "stale_after_minutes": 60},
        "golden_questions": golden_question_results(assistant, scenarios),
        "performance": {
            "risk_geojson": measure(lambda: risk.risk_geojson("phailin-2013", event.valid_time)),
            "scenario_simulation": measure(lambda: scenarios.simulate(event.cyclone_id, scenario_parameters, event.valid_time)),
            "grounded_local_answer": measure(lambda: assistant.answer("Why is this location high risk?", event.cyclone_id, event.valid_time)),
            "local_alert_processing": measure(lambda: AlertWorkflow(risk, LocalNotificationSender(), 67, 60).process(event)),
        },
        "not_executed": ["Live BigQuery, Earth Engine, Vertex AI, Pub/Sub, Eventarc, Firebase, and Cloud Scheduler tests require a configured GCP project and credentials.", "ML-enhanced versus baseline comparison is not applicable: Phase 4 implements a transparent constant-velocity baseline, not an ML-enhanced model.", "Cyclone_Feasibility_Testing_Document.docx was requested but was not present in this repository at evaluation time."],
    }
    destination = ROOT / "docs" / "evaluation"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    (destination / "gemini-golden-set.json").write_text(json.dumps(results["golden_questions"], indent=2) + "\n", encoding="utf-8")
    (destination / "performance-results.json").write_text(json.dumps(results["performance"], indent=2) + "\n", encoding="utf-8")
    print(f"Wrote Phase 8 evidence to {destination}")


if __name__ == "__main__":
    main()
