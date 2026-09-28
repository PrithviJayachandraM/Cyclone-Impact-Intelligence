"""Read-only access to persisted Phase 2 location features."""

from __future__ import annotations

import json
from pathlib import Path


class EnrichmentRepository:
    def __init__(self, data_directory: Path) -> None:
        payload = json.loads((data_directory / "location_features.json").read_text(encoding="utf-8"))
        self.layers_metadata: list[dict[str, object]] = payload["layers"]
        self.locations: list[dict[str, object]] = payload["locations"]
        self.layers_by_id = {str(layer["layer_id"]): layer for layer in self.layers_metadata}

    def layers(self, cyclone_id: str) -> list[dict[str, object]]:
        return self.layers_metadata if any(location["cyclone_id"] == cyclone_id for location in self.locations) else []

    def locations_geojson(self, cyclone_id: str) -> dict[str, object]:
        features = []
        for location in self.locations:
            if location["cyclone_id"] != cyclone_id:
                continue
            values = {item["layer_id"]: item["value"] for item in location["features"]}
            features.append({
                "type": "Feature",
                "geometry": location["geometry"],
                "properties": {
                    "location_id": location["location_id"],
                    "name": location["name"],
                    "administrative_level": location["administrative_level"],
                    "feature_values": values,
                },
            })
        return {"type": "FeatureCollection", "features": features}

    def feature_vector(self, cyclone_id: str, location_id: str) -> dict[str, object] | None:
        location = next(
            (item for item in self.locations if item["cyclone_id"] == cyclone_id and item["location_id"] == location_id),
            None,
        )
        if location is None:
            return None
        vector = [{**self.layers_by_id[str(item["layer_id"])], **item} for item in location["features"]]
        return {
            "location": {
                "location_id": location["location_id"],
                "name": location["name"],
                "administrative_level": location["administrative_level"],
            },
            "features": vector,
        }
