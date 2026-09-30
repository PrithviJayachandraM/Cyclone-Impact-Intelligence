from __future__ import annotations

import json
import unittest
from pathlib import Path

from cyclone.forecast import evaluate_backtest, forecast_points


class ForecastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        all_points = json.loads((Path(__file__).parents[1] / "data" / "normalized" / "track_points.json").read_text(encoding="utf-8"))
        cls.points = [point for point in all_points if point["cyclone_id"] == "phailin-2013"]

    def test_generates_reproducible_future_points_with_metadata(self) -> None:
        first = forecast_points(self.points, (6, 12, 18))
        second = forecast_points(self.points, (6, 12, 18))
        self.assertEqual(first, second)
        self.assertEqual([point["horizon_hours"] for point in first], [6, 12, 18])
        self.assertTrue(all(point["source_type"] == "forecast" for point in first))
        self.assertTrue(all(point["uncertainty_km"] > 0 for point in first))
        self.assertGreater(first[0]["valid_time"], self.points[-1]["timestamp"])

    def test_records_chronological_splits_and_metrics(self) -> None:
        evaluation = evaluate_backtest(self.points)
        self.assertLess(evaluation["splits"]["train"]["end"], evaluation["splits"]["validation"]["start"])
        self.assertLess(evaluation["splits"]["validation"]["end"], evaluation["splits"]["test"]["start"])
        self.assertGreaterEqual(evaluation["validation"]["mean_track_error_km"], 0)
        self.assertGreaterEqual(evaluation["test"]["mean_wind_mae_kph"], 0)

    def test_rejects_insufficient_history(self) -> None:
        with self.assertRaisesRegex(ValueError, "two"):
            forecast_points(self.points[:1])
