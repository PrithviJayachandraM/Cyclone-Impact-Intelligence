"""Environment-backed application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    host: str
    port: int
    data_directory: Path
    enrichment_data_directory: Path
    risk_data_directory: Path
    google_maps_api_key: str | None

    @classmethod
    def from_environment(cls) -> "AppConfig":
        port = int(os.getenv("PORT", os.getenv("APP_PORT", "8080")))
        if not 1 <= port <= 65535:
            raise ValueError("APP_PORT must be between 1 and 65535")
        return cls(
            host=os.getenv("APP_HOST", "127.0.0.1"),
            port=port,
            data_directory=Path(os.getenv("CYCLONE_DATA_PATH", "data/normalized")),
            enrichment_data_directory=Path(os.getenv("ENRICHMENT_DATA_PATH", "data/enriched")),
            risk_data_directory=Path(os.getenv("RISK_DATA_PATH", "data/risk")),
            google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY") or None,
        )
