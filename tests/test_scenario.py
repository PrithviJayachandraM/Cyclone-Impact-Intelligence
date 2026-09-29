from __future__ import annotations

import copy
import unittest
from pathlib import Path

from cyclone.enrichment import EnrichmentRepository
from cyclone.forecast import ForecastRepository
from cyclone.intelligence import AdvisoryRepository, GroundedAssistant
from cyclone.repository import HistoricalTrackRepository
from cyclone.risk import RiskRepository
from cyclone.scenario import ScenarioParameters, ScenarioService, ScenarioValidationError


class ScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).parents[1]
        tracks = HistoricalTrackRepository(root / "data" / "normalized")
        enrichment = EnrichmentRepository(root / "data" / "enriched")
        risk = RiskRepository(root / "data" / "risk", enrichment.locations)
        forecast = ForecastRepository(root / "data" / "forecast")
        cls.service = ScenarioService(tracks, enrichment, risk, forecast)
        cls.assistant = GroundedAssistant(tracks, enrichment, risk, forecast, AdvisoryRepository(root / "data" / "advisories"))

    def simulate(self, parameters: dict[str, object]) -> dict[str, object]:
        result = self.service.simulate("phailin-2013", ScenarioParameters.from_payload(parameters), "2013-10-13T00:00:00Z")
        self.assertIsNotNone(result)
        return result or {}

    def test_validates_parameters_and_boundaries(self) -> None:
        self.assertEqual(ScenarioParameters.from_payload({"track_shift_km": -100, "intensity_multiplier": 0.5, "rainfall_multiplier": 1.5}).track_shift_km, -100)
        for payload in ({}, {"track_shift_km": 101}, {"intensity_multiplier": 0.4}, {"rainfall_multiplier": "bad"}, {"extra": 1}):
            with self.assertRaises(ScenarioValidationError):
                ScenarioParameters.from_payload(payload)

    def test_is_deterministic_and_preserves_baseline_data(self) -> None:
        before = copy.deepcopy(self.service.risk.risk_geojson("phailin-2013", "2013-10-13T00:00:00Z"))
        parameters = {"track_shift_km": 20, "intensity_multiplier": 1.2, "rainfall_multiplier": 1.1}
        self.assertEqual(self.simulate(parameters), self.simulate(parameters))
        self.assertEqual(before, self.service.risk.risk_geojson("phailin-2013", "2013-10-13T00:00:00Z"))

    def test_track_intensity_and_rainfall_transform_risk_inputs(self) -> None:
        baseline = self.simulate({"track_shift_km": 20})
        simulation = baseline["simulation"]
        self.assertNotEqual(baseline["baseline"]["track"], simulation["track"])
        self.assertTrue(baseline["comparison"]["changed_location_ids"])
        intensity = self.simulate({"intensity_multiplier": 1.5})
        self.assertGreater(intensity["simulation"]["risk_scores"][0]["feature_contributions"][0]["raw_value"], intensity["baseline"]["risk_scores"][0]["feature_contributions"][0]["raw_value"])
        rainfall = self.simulate({"rainfall_multiplier": 1.5})
        self.assertGreater(rainfall["simulation"]["risk_scores"][0]["feature_contributions"][1]["raw_value"], rainfall["baseline"]["risk_scores"][0]["feature_contributions"][1]["raw_value"])
        self.assertEqual(rainfall["simulation"]["affected_locations"]["features"][0]["properties"]["feature_values"]["rainfall"], 330.0)

    def test_comparison_and_grounded_explanation_are_simulation_labelled(self) -> None:
        result = self.simulate({"intensity_multiplier": 1.5})
        explanation = self.assistant.explain_scenario(result)
        self.assertEqual(result["comparison"]["locations"][0]["simulation_risk_score"] - result["comparison"]["locations"][0]["baseline_risk_score"], result["comparison"]["locations"][0]["risk_score_delta"])
        self.assertTrue(explanation["simulation"])
        self.assertIn("simulation", str(explanation["context"]).lower())

    def test_mocked_gemini_receives_baseline_and_simulation_context(self) -> None:
        class CapturingResponder:
            def __init__(self) -> None:
                self.context: dict[str, object] | None = None

            def respond(self, question: str, context: dict[str, object]) -> str:
                self.context = context
                return "Under this simulated scenario, the deterministic comparison changes risk."

        responder = CapturingResponder()
        assistant = GroundedAssistant(self.assistant.tracks, self.assistant.enrichment, self.assistant.risk, self.assistant.forecast, self.assistant.advisories, responder)
        explanation = assistant.explain_scenario(self.simulate({"track_shift_km": 20}))
        self.assertEqual(explanation["provider"], "vertex-gemini")
        self.assertIsNotNone(responder.context)
        self.assertIn("baseline", responder.context or {})
        self.assertIn("simulation_result", responder.context or {})
        self.assertTrue((responder.context or {})["simulation"])
