"""Deterministic Phase 6 what-if simulation built on the existing risk engine."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import asdict, dataclass

from cyclone.enrichment import EnrichmentRepository
from cyclone.forecast import ForecastRepository
from cyclone.repository import HistoricalTrackRepository
from cyclone.risk import RiskRepository, calculate_scores


class ScenarioValidationError(ValueError):
    """Raised for an invalid or indistinguishable what-if scenario."""


@dataclass(frozen=True)
class ScenarioParameters:
    track_shift_km: float = 0.0
    intensity_multiplier: float = 1.0
    rainfall_multiplier: float = 1.0

    @classmethod
    def from_payload(cls, payload: object) -> "ScenarioParameters":
        if not isinstance(payload, dict):
            raise ScenarioValidationError("parameters must be an object")
        allowed = {"track_shift_km", "intensity_multiplier", "rainfall_multiplier"}
        unknown = set(payload) - allowed
        if unknown:
            raise ScenarioValidationError(f"unsupported scenario parameter: {sorted(unknown)[0]}")
        try:
            parameters = cls(**{name: float(payload.get(name, default)) for name, default in (("track_shift_km", 0.0), ("intensity_multiplier", 1.0), ("rainfall_multiplier", 1.0))})
        except (TypeError, ValueError) as error:
            raise ScenarioValidationError("scenario parameters must be numbers") from error
        if not all(math.isfinite(value) for value in asdict(parameters).values()):
            raise ScenarioValidationError("scenario parameters must be finite")
        if not -100 <= parameters.track_shift_km <= 100:
            raise ScenarioValidationError("track_shift_km must be between -100 and 100")
        if not 0.5 <= parameters.intensity_multiplier <= 1.5:
            raise ScenarioValidationError("intensity_multiplier must be between 0.5 and 1.5")
        if not 0.5 <= parameters.rainfall_multiplier <= 1.5:
            raise ScenarioValidationError("rainfall_multiplier must be between 0.5 and 1.5")
        if parameters == cls():
            raise ScenarioValidationError("scenario must change at least one parameter from baseline")
        return parameters


class ScenarioService:
    """Transforms copied inputs, then delegates all numerical scoring to Phase 3."""

    def __init__(self, tracks: HistoricalTrackRepository, enrichment: EnrichmentRepository, risk: RiskRepository, forecast: ForecastRepository) -> None:
        self.tracks, self.enrichment, self.risk, self.forecast = tracks, enrichment, risk, forecast

    def simulate(self, cyclone_id: str, parameters: ScenarioParameters, valid_time: str | None = None) -> dict[str, object] | None:
        event = next((event for event in self.tracks.list_events() if event["cyclone_id"] == cyclone_id), None)
        if event is None:
            return None
        selected_time, baseline_points = self._baseline_points(cyclone_id, valid_time)
        baseline_features = self.risk.risk_geojson(cyclone_id, selected_time)["features"]
        if not baseline_features:
            raise ScenarioValidationError("baseline risk is unavailable for the selected time")
        scenario_points = self._transform_track(copy.deepcopy(baseline_points), parameters)
        scenario_locations = self._transform_locations(copy.deepcopy(self.enrichment.locations), cyclone_id, parameters)
        scenario_scores = calculate_scores(scenario_points, scenario_locations)
        scenario_id = self._scenario_id(cyclone_id, selected_time, parameters)
        for score in scenario_scores:
            score.update({"source_type": "simulation", "scenario_id": scenario_id, "simulation_of": baseline_points[0].get("source_type", "observed")})
        baseline_scores = [copy.deepcopy(feature["properties"]) for feature in baseline_features]
        return {
            "scenario": {"scenario_id": scenario_id, "status": "simulation", "cyclone_id": cyclone_id, "valid_time": selected_time, "parameters": asdict(parameters)},
            "baseline": {"status": "baseline", "track": self._track_geojson(cyclone_id, baseline_points, "baseline"), "affected_locations": self._locations_geojson(self.enrichment.locations, cyclone_id), "risk_scores": baseline_scores},
            "simulation": {"status": "simulation", "track": self._track_geojson(cyclone_id, scenario_points, "simulation"), "affected_locations": self._locations_geojson(scenario_locations, cyclone_id), "risk_scores": scenario_scores},
            "comparison": self._comparison(baseline_scores, scenario_scores, self.enrichment.locations),
        }

    def _baseline_points(self, cyclone_id: str, valid_time: str | None) -> tuple[str, list[dict[str, object]]]:
        observed = [point for point in self.tracks.points if point["cyclone_id"] == cyclone_id]
        if not observed:
            raise ScenarioValidationError("cyclone track is unavailable")
        latest_observed = max(observed, key=lambda point: str(point["timestamp"]))
        selected_time = valid_time or str(latest_observed["timestamp"])
        forecast = next((point for point in self.forecast.forecast(cyclone_id) if point["valid_time"] == selected_time), None)
        if forecast:
            return selected_time, [copy.deepcopy(forecast)]
        if selected_time == latest_observed["timestamp"]:
            return selected_time, copy.deepcopy(observed)
        raise ScenarioValidationError("valid_time must be the latest observed state or an available forecast")

    @staticmethod
    def _transform_track(points: list[dict[str, object]], parameters: ScenarioParameters) -> list[dict[str, object]]:
        for point in points:
            latitude = float(point["latitude"])
            point["longitude"] = round(float(point["longitude"]) + parameters.track_shift_km / (111.32 * max(0.1, abs(math.cos(math.radians(latitude))))), 4)
            point["wind_speed_kph"] = round(float(point["wind_speed_kph"]) * parameters.intensity_multiplier, 1)
            if "intensity_kph" in point:
                point["intensity_kph"] = round(float(point["intensity_kph"]) * parameters.intensity_multiplier, 1)
        return points

    @staticmethod
    def _transform_locations(locations: list[dict[str, object]], cyclone_id: str, parameters: ScenarioParameters) -> list[dict[str, object]]:
        for location in locations:
            if location["cyclone_id"] == cyclone_id:
                for feature in location["features"]:
                    if feature["layer_id"] == "rainfall":
                        feature["value"] = round(float(feature["value"]) * parameters.rainfall_multiplier, 2)
        return locations

    @staticmethod
    def _track_geojson(cyclone_id: str, points: list[dict[str, object]], status: str) -> dict[str, object]:
        features = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [point["longitude"], point["latitude"]]}, "properties": {key: value for key, value in point.items() if key not in {"longitude", "latitude"}} | {"scenario_status": status}} for point in points]
        if len(points) > 1:
            features.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[point["longitude"], point["latitude"]] for point in points]}, "properties": {"cyclone_id": cyclone_id, "scenario_status": status}})
        return {"type": "FeatureCollection", "features": features}

    @staticmethod
    def _locations_geojson(locations: list[dict[str, object]], cyclone_id: str) -> dict[str, object]:
        features = []
        for location in locations:
            if location["cyclone_id"] == cyclone_id:
                features.append({
                    "type": "Feature",
                    "geometry": location["geometry"],
                    "properties": {
                        "location_id": location["location_id"],
                        "name": location["name"],
                        "feature_values": {feature["layer_id"]: feature["value"] for feature in location["features"]},
                    },
                })
        return {"type": "FeatureCollection", "features": features}

    @staticmethod
    def _comparison(baseline: list[dict[str, object]], simulation: list[dict[str, object]], locations: list[dict[str, object]]) -> dict[str, object]:
        location_names = {str(location["location_id"]): str(location["name"]) for location in locations}
        simulated = {str(score["location_id"]): score for score in simulation}
        rows = []
        for original in baseline:
            changed = simulated[str(original["location_id"])]
            original_contributions = {item["feature_id"]: item for item in original["feature_contributions"]}
            rows.append({"location_id": original["location_id"], "name": location_names[str(original["location_id"])], "baseline_risk_score": original["risk_score"], "simulation_risk_score": changed["risk_score"], "risk_score_delta": changed["risk_score"] - original["risk_score"], "baseline_band": original["band"], "simulation_band": changed["band"], "contribution_deltas": [{"feature_id": item["feature_id"], "score_points_delta": round(item["score_points"] - original_contributions[item["feature_id"]]["score_points"], 2)} for item in changed["feature_contributions"]]})
        return {"locations": rows, "changed_location_ids": [row["location_id"] for row in rows if row["risk_score_delta"] != 0], "higher_risk_location_ids": [row["location_id"] for row in rows if row["risk_score_delta"] > 0]}

    @staticmethod
    def _scenario_id(cyclone_id: str, valid_time: str, parameters: ScenarioParameters) -> str:
        source = json.dumps({"cyclone_id": cyclone_id, "valid_time": valid_time, "parameters": asdict(parameters)}, sort_keys=True, separators=(",", ":"))
        return f"scenario-{hashlib.sha256(source.encode()).hexdigest()[:12]}"
