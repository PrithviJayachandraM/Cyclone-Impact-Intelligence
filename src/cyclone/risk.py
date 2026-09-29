"""Transparent, deterministic Phase 3 risk baseline with Phase 4 forecast inputs."""

from __future__ import annotations

import json
import math
from pathlib import Path


MODEL_VERSION = "phase3-baseline-1"
HIGH_RISK_THRESHOLD = 67
FEATURES = (
    ("wind", "Maximum observed wind", 0.20),
    ("rainfall", "Accumulated rainfall", 0.25),
    ("proximity", "Track proximity", 0.25),
    ("flood_susceptibility", "Low-elevation flood susceptibility", 0.15),
    ("population", "Population exposure", 0.15),
)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _distance_km(first: tuple[float, float], second: tuple[float, float]) -> float:
    latitude_1, longitude_1 = map(math.radians, first)
    latitude_2, longitude_2 = map(math.radians, second)
    half_chord = math.sin((latitude_2 - latitude_1) / 2) ** 2 + math.cos(latitude_1) * math.cos(latitude_2) * math.sin((longitude_2 - longitude_1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(half_chord))


def _centroid(location: dict[str, object]) -> tuple[float, float]:
    coordinates = location["geometry"]["coordinates"][0][:-1]
    return sum(point[1] for point in coordinates) / len(coordinates), sum(point[0] for point in coordinates) / len(coordinates)


def _band(score: int) -> str:
    return "high" if score >= HIGH_RISK_THRESHOLD else "medium" if score >= 34 else "low"


def calculate_scores(track_points: list[dict[str, object]], locations: list[dict[str, object]]) -> list[dict[str, object]]:
    """Calculate a documented baseline from one observed or forecast track state."""
    if not track_points:
        raise ValueError("Risk calculation requires track points")
    cyclone_id = str(track_points[0]["cyclone_id"])
    cyclone_points = [point for point in track_points if point["cyclone_id"] == cyclone_id]
    max_wind = max(float(point["wind_speed_kph"]) for point in cyclone_points)
    track_coordinates = [(float(point["latitude"]), float(point["longitude"])) for point in cyclone_points]
    valid_time = max(str(point.get("valid_time", point.get("timestamp"))) for point in cyclone_points)
    source_type = str(cyclone_points[0].get("source_type", "observed"))
    forecast_created_at = cyclone_points[0].get("forecast_created_at")
    scores = []
    for location in locations:
        if location["cyclone_id"] != cyclone_id:
            continue
        values = {str(feature["layer_id"]): float(feature["value"]) for feature in location["features"]}
        for required in ("rainfall", "elevation", "population"):
            if required not in values:
                raise ValueError(f"Location {location['location_id']} is missing {required}")
        distance = min(_distance_km(_centroid(location), point) for point in track_coordinates)
        raw_values = {"wind": max_wind, "rainfall": values["rainfall"], "proximity": distance, "flood_susceptibility": values["elevation"], "population": values["population"]}
        normalized = {"wind": _clamp(max_wind / 250), "rainfall": _clamp(values["rainfall"] / 300), "proximity": _clamp(1 - distance / 250), "flood_susceptibility": _clamp(1 - values["elevation"] / 100), "population": _clamp(values["population"] / 100_000)}
        contributions = [{"feature_id": feature_id, "name": name, "raw_value": round(raw_values[feature_id], 2), "normalised_value": round(normalized[feature_id], 4), "weight": weight, "score_points": round(normalized[feature_id] * weight * 100, 2)} for feature_id, name, weight in FEATURES]
        score = round(sum(item["score_points"] for item in contributions))
        scores.append({"cyclone_id": cyclone_id, "location_id": location["location_id"], "valid_time": valid_time, "risk_score": score, "band": _band(score), "model_version": MODEL_VERSION, "source_type": source_type, "forecast_created_at": forecast_created_at, "feature_contributions": contributions})
    return sorted(scores, key=lambda score: str(score["location_id"]))


class RiskRepository:
    def __init__(self, data_directory: Path, locations: list[dict[str, object]]) -> None:
        self.scores = json.loads((data_directory / "risk_scores.json").read_text(encoding="utf-8"))["scores"]
        self.locations = {str(location["location_id"]): location for location in locations}

    def _scores_for(self, cyclone_id: str, valid_time: str | None) -> list[dict[str, object]]:
        scores = [score for score in self.scores if score["cyclone_id"] == cyclone_id]
        selected_time = valid_time or max((str(score["valid_time"]) for score in scores), default="")
        return [score for score in scores if score["valid_time"] == selected_time]

    def risk_geojson(self, cyclone_id: str, valid_time: str | None = None) -> dict[str, object]:
        features = []
        for score in self._scores_for(cyclone_id, valid_time):
            location = self.locations.get(str(score["location_id"]))
            if location:
                features.append({"type": "Feature", "geometry": location["geometry"], "properties": score})
        return {"type": "FeatureCollection", "features": features}

    def location_risk(self, cyclone_id: str, location_id: str, valid_time: str | None = None) -> dict[str, object] | None:
        return next((score for score in self._scores_for(cyclone_id, valid_time) if score["location_id"] == location_id), None)
