from __future__ import annotations

import json
import sys
from pathlib import Path

from cyclone.forecast import MODEL_VERSION, evaluate_backtest, forecast_points
from cyclone.repository import HistoricalTrackRepository


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python scripts/build_forecasts.py NORMALIZED_DIR OUTPUT_DIR")
    tracks = HistoricalTrackRepository(Path(sys.argv[1]))
    output_directory = Path(sys.argv[2])
    output_directory.mkdir(parents=True, exist_ok=True)
    payload = {"model_version": MODEL_VERSION, "points": forecast_points(tracks.points), "evaluation": evaluate_backtest(tracks.points)}
    (output_directory / "forecast_points.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Built {len(payload['points'])} forecast point(s) and chronological evaluation metrics.")
