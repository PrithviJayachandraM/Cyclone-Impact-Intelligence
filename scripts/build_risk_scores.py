from __future__ import annotations

import json
import sys
from pathlib import Path

from cyclone.enrichment import EnrichmentRepository
from cyclone.repository import HistoricalTrackRepository
from cyclone.risk import MODEL_VERSION, calculate_scores


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("Usage: python scripts/build_risk_scores.py NORMALIZED_DIR ENRICHED_DIR OUTPUT_DIR")
    tracks = HistoricalTrackRepository(Path(sys.argv[1]))
    enrichment = EnrichmentRepository(Path(sys.argv[2]))
    output_directory = Path(sys.argv[3])
    output_directory.mkdir(parents=True, exist_ok=True)
    payload = {"model_version": MODEL_VERSION, "scores": calculate_scores(tracks.points, enrichment.locations)}
    (output_directory / "risk_scores.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Built {len(payload['scores'])} deterministic risk score(s).")
