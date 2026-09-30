from __future__ import annotations

import json
import unittest
from pathlib import Path

from cyclone.risk import calculate_scores


class RiskEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).parents[1]
        all_points = json.loads((root / "data" / "normalized" / "track_points.json").read_text(encoding="utf-8"))
        cls.points = [point for point in all_points if point["cyclone_id"] == "phailin-2013"]
        cls.locations = json.loads((root / "data" / "enriched" / "location_features.json").read_text(encoding="utf-8"))["locations"]

    def test_calculates_deterministic_explainable_scores(self) -> None:
        first = calculate_scores(self.points, self.locations)
        second = calculate_scores(self.points, self.locations)
        self.assertEqual(first, second)
        self.assertEqual([score["band"] for score in first], ["high", "medium"])
        self.assertEqual(first[0]["risk_score"], 85)
        self.assertEqual({item["feature_id"] for item in first[0]["feature_contributions"]}, {"wind", "rainfall", "proximity", "flood_susceptibility", "population"})
        self.assertEqual(round(sum(item["score_points"] for item in first[0]["feature_contributions"])), first[0]["risk_score"])

    def test_rejects_missing_phase_two_feature(self) -> None:
        incomplete = [{**self.locations[0], "features": self.locations[0]["features"][:-1]}]
        with self.assertRaisesRegex(ValueError, "population"):
            calculate_scores(self.points, incomplete)
