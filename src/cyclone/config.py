"""Environment-backed application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class AppConfig:
    host: str
    port: int
    data_directory: Path
    enrichment_data_directory: Path
    risk_data_directory: Path
    forecast_data_directory: Path
    advisory_data_directory: Path
    google_maps_api_key: str | None
    gemini_provider: str
    gcp_project_id: str | None
    gcp_region: str
    vertex_ai_model: str
    vertex_ai_access_token: str | None

    @classmethod
    def from_environment(cls) -> "AppConfig":
        port = int(os.getenv("PORT", os.getenv("APP_PORT", "8080")))
        if not 1 <= port <= 65535:
            raise ValueError("APP_PORT must be between 1 and 65535")
        gemini_provider = os.getenv("GEMINI_PROVIDER", "local").lower()
        if gemini_provider not in {"local", "vertex"}:
            raise ValueError("GEMINI_PROVIDER must be local or vertex")
        return cls(
            host=os.getenv("APP_HOST", "127.0.0.1"), port=port,
            data_directory=Path(os.getenv("CYCLONE_DATA_PATH", "data/normalized")),
            enrichment_data_directory=Path(os.getenv("ENRICHMENT_DATA_PATH", "data/enriched")),
            risk_data_directory=Path(os.getenv("RISK_DATA_PATH", "data/risk")),
            forecast_data_directory=Path(os.getenv("FORECAST_DATA_PATH", "data/forecast")),
            advisory_data_directory=Path(os.getenv("ADVISORY_DATA_PATH", "data/advisories")),
            google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY") or None,
            gemini_provider=gemini_provider,
            gcp_project_id=os.getenv("GCP_PROJECT_ID") or None,
            gcp_region=os.getenv("GCP_REGION", "asia-south1"),
            vertex_ai_model=os.getenv("VERTEX_AI_MODEL", "gemini-2.5-flash"),
            vertex_ai_access_token=os.getenv("VERTEX_AI_ACCESS_TOKEN") or None,
        )
