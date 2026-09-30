from __future__ import annotations

import json
import sys
from pathlib import Path

from cyclone.enrichment import EnrichmentRepository
from cyclone.forecast import ForecastRepository
from cyclone.repository import HistoricalTrackRepository
from cyclone.risk import MODEL_VERSION, calculate_scores


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit("Usage: python scripts/build_risk_scores.py NORMALIZED_DIR ENRICHED_DIR FORECAST_DIR OUTPUT_DIR")
    tracks = HistoricalTrackRepository(Path(sys.argv[1]))
    enrichment = EnrichmentRepository(Path(sys.argv[2]))
    forecasts = ForecastRepository(Path(sys.argv[3]))
    output_directory = Path(sys.argv[4])
    output_directory.mkdir(parents=True, exist_ok=True)
    scores = []
    cyclone_ids = {point["cyclone_id"] for point in tracks.points}
    for cyclone_id in cyclone_ids:
        observed = [point for point in tracks.points if point["cyclone_id"] == cyclone_id]
        scores.extend(calculate_scores(observed, enrichment.locations))
    for forecast in forecasts.points:
        scores.extend(calculate_scores([forecast], enrichment.locations))
    payload = {"model_version": MODEL_VERSION, "scores": scores}
    (output_directory / "risk_scores.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Built {len(payload['scores'])} baseline and forecast risk score(s).")
