"""Modest, reproducible Phase 4 forecast baseline."""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from pathlib import Path


MODEL_VERSION = "phase4-constant-velocity-1"
UNCERTAINTY_KM_PER_HOUR = 10.0


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _as_utc(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _distance_km(first: dict[str, object], second: dict[str, object]) -> float:
    latitude_1, longitude_1 = map(math.radians, (float(first["latitude"]), float(first["longitude"])))
    latitude_2, longitude_2 = map(math.radians, (float(second["latitude"]), float(second["longitude"])))
    half_chord = math.sin((latitude_2 - latitude_1) / 2) ** 2 + math.cos(latitude_1) * math.cos(latitude_2) * math.sin((longitude_2 - longitude_1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(half_chord))


def _ordered(points: list[dict[str, object]]) -> list[dict[str, object]]:
    if len(points) < 2:
        raise ValueError("Forecasting requires at least two observed points")
    cyclone_ids = {point["cyclone_id"] for point in points}
    if len(cyclone_ids) != 1:
        raise ValueError("Forecasting accepts one cyclone at a time")
    return sorted(points, key=lambda point: str(point["timestamp"]))


def _forecast_from_history(history: list[dict[str, object]], horizons: tuple[int, ...]) -> list[dict[str, object]]:
    previous, latest = history[-2:]
    elapsed_hours = (_timestamp(str(latest["timestamp"])) - _timestamp(str(previous["timestamp"]))).total_seconds() / 3600
    if elapsed_hours <= 0:
        raise ValueError("Observed timestamps must increase")
    latitude_rate = (float(latest["latitude"]) - float(previous["latitude"])) / elapsed_hours
    longitude_rate = (float(latest["longitude"]) - float(previous["longitude"])) / elapsed_hours
    wind_rate = (float(latest["wind_speed_kph"]) - float(previous["wind_speed_kph"])) / elapsed_hours
    created_at = _timestamp(str(latest["timestamp"]))
    return [
        {
            "cyclone_id": latest["cyclone_id"],
            "forecast_created_at": _as_utc(created_at),
            "valid_time": _as_utc(created_at + timedelta(hours=horizon)),
            "horizon_hours": horizon,
            "latitude": round(max(-90, min(90, float(latest["latitude"]) + latitude_rate * horizon)), 4),
            "longitude": round(max(-180, min(180, float(latest["longitude"]) + longitude_rate * horizon)), 4),
            "intensity_kph": round(max(0, float(latest["wind_speed_kph"]) + wind_rate * horizon), 1),
            "wind_speed_kph": round(max(0, float(latest["wind_speed_kph"]) + wind_rate * horizon), 1),
            "uncertainty_km": round(UNCERTAINTY_KM_PER_HOUR * horizon, 1),
            "source_type": "forecast",
            "model_version": MODEL_VERSION,
        }
        for horizon in horizons
    ]


def forecast_points(points: list[dict[str, object]], horizons: tuple[int, ...] = (6, 12, 18)) -> list[dict[str, object]]:
    """Extrapolate the latest two observed positions and wind intensity."""
    if not horizons or any(horizon <= 0 for horizon in horizons):
        raise ValueError("Forecast horizons must be positive hours")
    return _forecast_from_history(_ordered(points), horizons)


def _metrics(predictions: list[dict[str, object]], actuals: list[dict[str, object]]) -> dict[str, float]:
    return {
        "mean_track_error_km": round(sum(_distance_km(prediction, actual) for prediction, actual in zip(predictions, actuals)) / len(actuals), 2),
        "mean_wind_mae_kph": round(sum(abs(float(prediction["wind_speed_kph"]) - float(actual["wind_speed_kph"])) for prediction, actual in zip(predictions, actuals)) / len(actuals), 2),
    }


def evaluate_backtest(points: list[dict[str, object]]) -> dict[str, object]:
    """Use chronological train/validation/test windows without future leakage."""
    ordered = _ordered(points)
    if len(ordered) < 6:
        raise ValueError("Backtesting requires at least six observed points")
    train, validation, test = ordered[:3], ordered[3:4], ordered[4:]
    validation_prediction = _forecast_from_history(train, (round((_timestamp(str(validation[0]["timestamp"])) - _timestamp(str(train[-1]["timestamp"]))).total_seconds() / 3600),))
    test_predictions = []
    for index, actual in enumerate(test, start=4):
        horizon = round((_timestamp(str(actual["timestamp"])) - _timestamp(str(ordered[index - 1]["timestamp"]))).total_seconds() / 3600)
        test_predictions.extend(_forecast_from_history(ordered[:index], (horizon,)))
    return {
        "model_version": MODEL_VERSION,
        "splits": {
            "train": {"start": train[0]["timestamp"], "end": train[-1]["timestamp"], "count": len(train)},
            "validation": {"start": validation[0]["timestamp"], "end": validation[-1]["timestamp"], "count": len(validation)},
            "test": {"start": test[0]["timestamp"], "end": test[-1]["timestamp"], "count": len(test)},
        },
        "validation": _metrics(validation_prediction, validation),
        "test": _metrics(test_predictions, test),
    }


class ForecastRepository:
    def __init__(self, data_directory: Path) -> None:
        payload = json.loads((data_directory / "forecast_points.json").read_text(encoding="utf-8"))
        self.points: list[dict[str, object]] = payload["points"]
        self.evaluation: dict[str, object] = payload["evaluation"]

    def forecast(self, cyclone_id: str) -> list[dict[str, object]]:
        return [point for point in self.points if point["cyclone_id"] == cyclone_id]

    def metrics(self, cyclone_id: str) -> dict[str, object] | None:
        if not self.forecast(cyclone_id):
            return None
        if "model_version" in self.evaluation:
            return self.evaluation
        return self.evaluation.get(cyclone_id)
