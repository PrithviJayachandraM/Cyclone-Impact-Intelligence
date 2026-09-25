"""Validate and normalize a small historical cyclone-track CSV."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path


REQUIRED_COLUMNS = {
    "cyclone_id", "name", "basin", "source", "observed_at", "timestamp",
    "latitude", "longitude", "wind_speed_kph", "pressure_hpa",
}


@dataclass(frozen=True)
class NormalizationResult:
    events_path: Path
    track_points_path: Path
    event_count: int
    point_count: int


def _number(value: str, field: str, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field} must be a number") from error
    if not minimum <= number <= maximum:
        raise ValueError(f"{field} must be between {minimum} and {maximum}")
    return number


def normalize_file(source_path: Path, output_directory: Path) -> NormalizationResult:
    """Create canonical event and point documents from a replay CSV."""
    with source_path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

        events: dict[str, dict[str, str]] = {}
        points: list[dict[str, object]] = []
        for line_number, row in enumerate(reader, start=2):
            cyclone_id = (row["cyclone_id"] or "").strip()
            if not cyclone_id:
                raise ValueError(f"line {line_number}: cyclone_id is required")
            timestamp = (row["timestamp"] or "").strip()
            if not timestamp.endswith("Z"):
                raise ValueError(f"line {line_number}: timestamp must be UTC ISO-8601")
            events.setdefault(cyclone_id, {
                "cyclone_id": cyclone_id,
                "name": (row["name"] or "").strip(),
                "basin": (row["basin"] or "").strip(),
                "source": (row["source"] or "").strip(),
                "observed_at": (row["observed_at"] or "").strip(),
            })
            points.append({
                "cyclone_id": cyclone_id,
                "timestamp": timestamp,
                "latitude": _number(row["latitude"], "latitude", -90, 90),
                "longitude": _number(row["longitude"], "longitude", -180, 180),
                "wind_speed_kph": _number(row["wind_speed_kph"], "wind_speed_kph", 0, 500),
                "pressure_hpa": _number(row["pressure_hpa"], "pressure_hpa", 800, 1100),
                "source_type": "observed",
            })

    if not points:
        raise ValueError("Track source contains no rows")
    points.sort(key=lambda point: (str(point["cyclone_id"]), str(point["timestamp"])))
    output_directory.mkdir(parents=True, exist_ok=True)
    events_path = output_directory / "cyclones.json"
    track_points_path = output_directory / "track_points.json"
    events_path.write_text(json.dumps(list(events.values()), indent=2) + "\n", encoding="utf-8")
    track_points_path.write_text(json.dumps(points, indent=2) + "\n", encoding="utf-8")
    return NormalizationResult(events_path, track_points_path, len(events), len(points))
