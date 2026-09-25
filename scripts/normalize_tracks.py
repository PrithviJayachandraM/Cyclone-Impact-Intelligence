from pathlib import Path
import sys

from cyclone.normalize_tracks import normalize_file


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python scripts/normalize_tracks.py INPUT.csv OUTPUT_DIRECTORY")
    result = normalize_file(Path(sys.argv[1]), Path(sys.argv[2]))
    print(f"Normalized {result.point_count} track points for {result.event_count} cyclone event(s).")
