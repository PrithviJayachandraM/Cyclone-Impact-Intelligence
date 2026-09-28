"""Local entry point for the Phase 1–5 cyclone intelligence slice."""

from __future__ import annotations

from http.server import ThreadingHTTPServer

from cyclone.api import create_handler
from cyclone.config import AppConfig
from cyclone.enrichment import EnrichmentRepository
from cyclone.forecast import ForecastRepository
from cyclone.intelligence import AdvisoryRepository, GroundedAssistant, VertexGeminiResponder
from cyclone.repository import HistoricalTrackRepository
from cyclone.risk import RiskRepository
def main() -> None:
    config = AppConfig.from_environment()
    enrichment = EnrichmentRepository(config.enrichment_data_directory)
    responder = None
    print(f"config:{config}")
    if config.gemini_provider == "vertex":
        if not (config.gcp_project_id and config.vertex_ai_access_token):
            raise ValueError("GCP_PROJECT_ID and VERTEX_AI_ACCESS_TOKEN are required when GEMINI_PROVIDER=vertex")
        responder = VertexGeminiResponder(config.gcp_project_id, config.gcp_region, config.vertex_ai_model, config.vertex_ai_access_token)
    assistant = GroundedAssistant(HistoricalTrackRepository(config.data_directory), enrichment, RiskRepository(config.risk_data_directory, enrichment.locations), ForecastRepository(config.forecast_data_directory), AdvisoryRepository(config.advisory_data_directory), responder)
    server = ThreadingHTTPServer(
        (config.host, config.port),
        create_handler(assistant.tracks, config.google_maps_api_key, enrichment, assistant.risk, assistant.forecast, assistant),
    )
    print(f"Cyclone Phase 5 available at http://{config.host}:{config.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
