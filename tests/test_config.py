from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from cyclone.config import AppConfig


class ConfigTests(unittest.TestCase):
    def test_reads_environment_configuration(self) -> None:
        environment = {"APP_PORT": "9090", "CYCLONE_DATA_PATH": "fixture", "ENRICHMENT_DATA_PATH": "enriched-fixture", "RISK_DATA_PATH": "risk-fixture", "FORECAST_DATA_PATH": "forecast-fixture", "ADVISORY_DATA_PATH": "advisory-fixture", "GOOGLE_MAPS_API_KEY": "browser-key", "GEMINI_PROVIDER": "vertex", "GCP_PROJECT_ID": "project", "VERTEX_AI_MODEL": "model", "VERTEX_AI_ACCESS_TOKEN": "token", "ALERT_RISK_THRESHOLD": "80", "ALERT_EVENT_TRANSPORT": "pubsub", "PUBSUB_TOPIC": "risk-events", "NOTIFICATION_PROVIDER": "firebase", "FIREBASE_PROJECT_ID": "firebase-project", "FIREBASE_NOTIFICATION_TOPIC": "demo", "LOG_LEVEL": "debug"}
        with patch.dict(os.environ, environment, clear=True):
            config = AppConfig.from_environment()
        self.assertEqual(config.port, 9090); self.assertEqual(str(config.data_directory), "fixture"); self.assertEqual(str(config.enrichment_data_directory), "enriched-fixture"); self.assertEqual(str(config.risk_data_directory), "risk-fixture"); self.assertEqual(str(config.forecast_data_directory), "forecast-fixture"); self.assertEqual(str(config.advisory_data_directory), "advisory-fixture"); self.assertEqual(config.google_maps_api_key, "browser-key"); self.assertEqual(config.gemini_provider, "vertex"); self.assertEqual(config.gcp_project_id, "project"); self.assertEqual(config.alert_risk_threshold, 80); self.assertEqual(config.alert_event_transport, "pubsub"); self.assertEqual(config.notification_provider, "firebase"); self.assertEqual(config.log_level, "DEBUG")

    def test_rejects_invalid_port(self) -> None:
        with patch.dict(os.environ, {"APP_PORT": "0"}, clear=True):
            with self.assertRaisesRegex(ValueError, "APP_PORT"):
                AppConfig.from_environment()

    def test_rejects_unknown_gemini_provider(self) -> None:
        with patch.dict(os.environ, {"GEMINI_PROVIDER": "unknown"}, clear=True):
            with self.assertRaisesRegex(ValueError, "GEMINI_PROVIDER"):
                AppConfig.from_environment()

    def test_rejects_invalid_alert_configuration(self) -> None:
        for environment, expected in (({"ALERT_RISK_THRESHOLD": "101"}, "ALERT_RISK_THRESHOLD"), ({"ALERT_EVENT_TRANSPORT": "queue"}, "ALERT_EVENT_TRANSPORT"), ({"NOTIFICATION_PROVIDER": "email"}, "NOTIFICATION_PROVIDER"), ({"LOG_LEVEL": "trace"}, "LOG_LEVEL")):
            with patch.dict(os.environ, environment, clear=True):
                with self.assertRaisesRegex(ValueError, expected):
                    AppConfig.from_environment()
