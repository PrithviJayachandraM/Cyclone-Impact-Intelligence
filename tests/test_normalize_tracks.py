from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from cyclone.normalize_tracks import normalize_file


class NormalizeTracksTests(unittest.TestCase):
    def write_csv(self, directory: Path, rows: list[dict[str, str]]) -> Path:
        path = directory / "tracks.csv"
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_normalizes_rows_into_event_and_track_documents(self) -> None:
        rows = [
            {
                "cyclone_id": "demo-1", "name": "Demo", "basin": "North Indian Ocean",
                "source": "IMD historical replay", "observed_at": "2024-05-25T00:00:00Z",
                "timestamp": "2024-05-25T00:00:00Z", "latitude": "18.1", "longitude": "87.2",
                "wind_speed_kph": "90", "pressure_hpa": "990",
            },
            {
                "cyclone_id": "demo-1", "name": "Demo", "basin": "North Indian Ocean",
                "source": "IMD historical replay", "observed_at": "2024-05-25T00:00:00Z",
                "timestamp": "2024-05-25T06:00:00Z", "latitude": "18.8", "longitude": "86.5",
                "wind_speed_kph": "100", "pressure_hpa": "984",
            },
        ]
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            result = normalize_file(self.write_csv(directory, rows), directory / "normalized")
            events = json.loads(result.events_path.read_text(encoding="utf-8"))
            points = json.loads(result.track_points_path.read_text(encoding="utf-8"))

        self.assertEqual(result.event_count, 1)
        self.assertEqual(result.point_count, 2)
        self.assertEqual(events[0]["cyclone_id"], "demo-1")
        self.assertEqual(points[0]["latitude"], 18.1)
        self.assertEqual(points[1]["timestamp"], "2024-05-25T06:00:00Z")

    def test_rejects_invalid_coordinates(self) -> None:
        row = {
            "cyclone_id": "demo-1", "name": "Demo", "basin": "North Indian Ocean",
            "source": "IMD", "observed_at": "2024-05-25T00:00:00Z",
            "timestamp": "2024-05-25T00:00:00Z", "latitude": "95", "longitude": "87.2",
            "wind_speed_kph": "90", "pressure_hpa": "990",
        }
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            with self.assertRaisesRegex(ValueError, "latitude"):
                normalize_file(self.write_csv(directory, [row]), directory / "normalized")

