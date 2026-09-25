"""Read-only access to normalized Phase 1 historical-track data."""

from __future__ import annotations

import json
from pathlib import Path


class HistoricalTrackRepository:
    def __init__(self, data_directory: Path) -> None:
        self.events = json.loads((data_directory / "cyclones.json").read_text(encoding="utf-8"))
        self.points = json.loads((data_directory / "track_points.json").read_text(encoding="utf-8"))

    def list_events(self) -> list[dict[str, object]]:
        return self.events

    def track_geojson(self, cyclone_id: str) -> dict[str, object] | None:
        event = next((item for item in self.events if item["cyclone_id"] == cyclone_id), None)
        if event is None:
            return None
        points = [point for point in self.points if point["cyclone_id"] == cyclone_id]
        features = [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [point["longitude"], point["latitude"]]},
                "properties": {key: value for key, value in point.items() if key not in {"longitude", "latitude"}},
            }
            for point in points
        ]
        if len(points) > 1:
            features.append({
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [[p["longitude"], p["latitude"]] for p in points]},
                "properties": {"cyclone_id": cyclone_id, "name": event["name"], "source": event["source"]},
            })
        return {"type": "FeatureCollection", "features": features}
