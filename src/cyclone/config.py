"""Environment-backed application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from cyclone.risk import *
from dotenv import load_dotenv

load_dotenv()  # Load .env file if present

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
    alert_risk_threshold: int
    alert_stale_after_minutes: int
    alert_event_transport: str
    pubsub_topic: str | None
    pubsub_access_token: str | None
    notification_provider: str
    firebase_project_id: str | None
    firebase_notification_topic: str
    firebase_access_token: str | None
    log_level: str

    @classmethod
    def from_environment(cls) -> "AppConfig":
        port = int(os.getenv("PORT", os.getenv("APP_PORT", "8080")))
        if not 1 <= port <= 65535:
            raise ValueError("APP_PORT must be between 1 and 65535")
        gemini_provider = os.getenv("GEMINI_PROVIDER", "local").lower()
        if gemini_provider not in {"local", "vertex"}:
            raise ValueError("GEMINI_PROVIDER must be local or vertex")
        alert_event_transport = os.getenv("ALERT_EVENT_TRANSPORT", "local").lower()
        if alert_event_transport not in {"local", "pubsub"}:
            raise ValueError("ALERT_EVENT_TRANSPORT must be local or pubsub")
        notification_provider = os.getenv("NOTIFICATION_PROVIDER", "local").lower()
        if notification_provider not in {"local", "firebase"}:
            raise ValueError("NOTIFICATION_PROVIDER must be local or firebase")
        alert_risk_threshold = int(os.getenv("ALERT_RISK_THRESHOLD", str(HIGH_RISK_THRESHOLD)))
        if not 0 <= alert_risk_threshold <= 100:
            raise ValueError("ALERT_RISK_THRESHOLD must be between 0 and 100")
        alert_stale_after_minutes = int(os.getenv("ALERT_STALE_AFTER_MINUTES", "60"))
        if alert_stale_after_minutes <= 0:
            raise ValueError("ALERT_STALE_AFTER_MINUTES must be positive")
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
            raise ValueError("LOG_LEVEL must be DEBUG, INFO, WARNING, or ERROR")
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
            alert_risk_threshold=alert_risk_threshold,
            alert_stale_after_minutes=alert_stale_after_minutes,
            alert_event_transport=alert_event_transport,
            pubsub_topic=os.getenv("PUBSUB_TOPIC") or None,
            pubsub_access_token=os.getenv("PUBSUB_ACCESS_TOKEN") or None,
            notification_provider=notification_provider,
            firebase_project_id=os.getenv("FIREBASE_PROJECT_ID") or None,
            firebase_notification_topic=os.getenv("FIREBASE_NOTIFICATION_TOPIC", "cyclone-alerts"),
            firebase_access_token=os.getenv("FIREBASE_ACCESS_TOKEN") or None,
            log_level=log_level,
        )
