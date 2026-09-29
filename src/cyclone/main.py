"""Local entry point for the Phase 1–5 cyclone intelligence slice."""

from __future__ import annotations

import logging
from http.server import ThreadingHTTPServer

from cyclone.api import create_handler
from cyclone.alerts import AlertWorkflow, FirebaseNotificationSender, LocalEventPublisher, LocalNotificationSender, PubSubEventPublisher
from cyclone.config import AppConfig
from cyclone.enrichment import EnrichmentRepository
from cyclone.forecast import ForecastRepository
from cyclone.intelligence import AdvisoryRepository, GroundedAssistant, VertexGeminiResponder
from cyclone.repository import HistoricalTrackRepository
from cyclone.risk import RiskRepository
from cyclone.scenario import ScenarioService


def main() -> None:
    config = AppConfig.from_environment()
    logging.basicConfig(level=config.log_level, format="%(message)s")
    enrichment = EnrichmentRepository(config.enrichment_data_directory)
    responder = None
    if config.gemini_provider == "vertex":
        if not (config.gcp_project_id and config.vertex_ai_access_token):
            raise ValueError("GCP_PROJECT_ID and VERTEX_AI_ACCESS_TOKEN are required when GEMINI_PROVIDER=vertex")
        responder = VertexGeminiResponder(config.gcp_project_id, config.gcp_region, config.vertex_ai_model, config.vertex_ai_access_token)
    assistant = GroundedAssistant(HistoricalTrackRepository(config.data_directory), enrichment, RiskRepository(config.risk_data_directory, enrichment.locations), ForecastRepository(config.forecast_data_directory), AdvisoryRepository(config.advisory_data_directory), responder)
    scenarios = ScenarioService(assistant.tracks, enrichment, assistant.risk, assistant.forecast)
    if config.notification_provider == "firebase":
        if not (config.firebase_project_id and config.firebase_access_token):
            raise ValueError("FIREBASE_PROJECT_ID and FIREBASE_ACCESS_TOKEN are required when NOTIFICATION_PROVIDER=firebase")
        notifier = FirebaseNotificationSender(config.firebase_project_id, config.firebase_notification_topic, config.firebase_access_token)
    else:
        notifier = LocalNotificationSender()
    alerts = AlertWorkflow(assistant.risk, notifier, config.alert_risk_threshold, config.alert_stale_after_minutes)
    if config.alert_event_transport == "pubsub":
        if not (config.gcp_project_id and config.pubsub_topic and config.pubsub_access_token):
            raise ValueError("GCP_PROJECT_ID, PUBSUB_TOPIC, and PUBSUB_ACCESS_TOKEN are required when ALERT_EVENT_TRANSPORT=pubsub")
        publisher = PubSubEventPublisher(config.gcp_project_id, config.pubsub_topic, config.pubsub_access_token)
    else:
        publisher = LocalEventPublisher(alerts.process)
    server = ThreadingHTTPServer(
        (config.host, config.port),
        create_handler(assistant.tracks, config.google_maps_api_key, enrichment, assistant.risk, assistant.forecast, assistant, scenarios, alerts, publisher),
    )
    print(f"Cyclone Phase 7 available at http://{config.host}:{config.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
