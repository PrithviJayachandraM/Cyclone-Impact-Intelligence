from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from cyclone.enrichment import EnrichmentRepository
from cyclone.evaluation import data_quality_report, golden_question_results
from cyclone.forecast import ForecastRepository
from cyclone.intelligence import AdvisoryRepository, GroundedAssistant
from cyclone.repository import HistoricalTrackRepository
from cyclone.risk import calculate_scores, RiskRepository
from cyclone.scenario import ScenarioService


class FeasibilityEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).parents[1]
        cls.tracks = HistoricalTrackRepository(root / "data" / "normalized")
        cls.enrichment = EnrichmentRepository(root / "data" / "enriched")
        cls.risk = RiskRepository(root / "data" / "risk", cls.enrichment.locations)
        forecast = ForecastRepository(root / "data" / "forecast")
        cls.assistant = GroundedAssistant(cls.tracks, cls.enrichment, cls.risk, forecast, AdvisoryRepository(root / "data" / "advisories"))
        cls.scenarios = ScenarioService(cls.tracks, cls.enrichment, cls.risk, forecast)

    def test_frozen_replay_data_quality_and_geometry(self) -> None:
        report = data_quality_report(self.tracks, self.enrichment)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["track_points"], 18)
        self.assertEqual(report["events"], 3)
        self.assertEqual(report["locations"], 2)
        self.assertEqual(self.tracks.track_geojson("phailin-2013")["features"][-1]["geometry"]["type"], "LineString")

    def test_risk_extremes_stay_bounded_and_explainable(self) -> None:
        locations = copy.deepcopy(self.enrichment.locations)
        for location in locations:
            for feature in location["features"]:
                if feature["layer_id"] in {"rainfall", "population"}:
                    feature["value"] = 10_000_000
                elif feature["layer_id"] == "elevation":
                    feature["value"] = 0
        points = [point for point in copy.deepcopy(self.tracks.points) if point["cyclone_id"] == "phailin-2013"]
        for point in points:
            point["wind_speed_kph"] = 10_000
        scores = calculate_scores(points, locations)
        self.assertTrue(all(0 <= score["risk_score"] <= 100 for score in scores))
        self.assertTrue(all(round(sum(item["score_points"] for item in score["feature_contributions"])) == score["risk_score"] for score in scores))

    def test_golden_questions_are_grounded_and_failure_safe(self) -> None:
        results = golden_question_results(self.assistant, self.scenarios)
        self.assertEqual(len(results), 7)
        self.assertTrue(all(result["pass"] for result in results), json.dumps(results, indent=2))
