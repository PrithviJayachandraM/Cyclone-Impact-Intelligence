from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from cyclone.config import AppConfig


class ConfigTests(unittest.TestCase):
    def test_reads_environment_configuration(self) -> None:
        with patch.dict(os.environ, {"APP_PORT": "9090", "CYCLONE_DATA_PATH": "fixture", "ENRICHMENT_DATA_PATH": "enriched-fixture", "GOOGLE_MAPS_API_KEY": "browser-key"}, clear=True):
            config = AppConfig.from_environment()
        self.assertEqual(config.port, 9090)
        self.assertEqual(str(config.data_directory), "fixture")
        self.assertEqual(str(config.enrichment_data_directory), "enriched-fixture")
        self.assertEqual(config.google_maps_api_key, "browser-key")

    def test_rejects_invalid_port(self) -> None:
        with patch.dict(os.environ, {"APP_PORT": "0"}, clear=True):
            with self.assertRaisesRegex(ValueError, "APP_PORT"):
                AppConfig.from_environment()
