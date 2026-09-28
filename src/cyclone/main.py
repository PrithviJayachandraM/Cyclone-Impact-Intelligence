"""Local entry point for the Phase 1–4 cyclone intelligence slice."""

from __future__ import annotations

from http.server import ThreadingHTTPServer

from cyclone.api import create_handler
from cyclone.config import AppConfig
from cyclone.enrichment import EnrichmentRepository
from cyclone.forecast import ForecastRepository
from cyclone.repository import HistoricalTrackRepository
from cyclone.risk import RiskRepository
from dotenv import load_dotenv
import os

load_dotenv()



def main() -> None:
    config = AppConfig.from_environment()
    enrichment = EnrichmentRepository(config.enrichment_data_directory)
    server = ThreadingHTTPServer(
        (config.host, config.port),
        create_handler(HistoricalTrackRepository(config.data_directory), os.getenv("GOOGLE_MAPS_API_KEY"), enrichment, RiskRepository(config.risk_data_directory, enrichment.locations), ForecastRepository(config.forecast_data_directory)),
    )
    print(f"Cyclone Phase 4 available at http://{config.host}:{config.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
