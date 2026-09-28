from __future__ import annotations

import json
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

from cyclone.api import create_handler
from cyclone.enrichment import EnrichmentRepository
from cyclone.forecast import ForecastRepository
from cyclone.repository import HistoricalTrackRepository
from cyclone.risk import RiskRepository


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).parents[1]
        tracks = HistoricalTrackRepository(root / "data" / "normalized")
        enrichment = EnrichmentRepository(root / "data" / "enriched")
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(tracks, enrichment_repository=enrichment, risk_repository=RiskRepository(root / "data" / "risk", enrichment.locations), forecast_repository=ForecastRepository(root / "data" / "forecast")))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown(); cls.thread.join(); cls.server.server_close()

    def get(self, path: str) -> tuple[int, dict[str, str], bytes]:
        connection = HTTPConnection("127.0.0.1", self.server.server_port)
        connection.request("GET", path)
        response = connection.getresponse(); body = response.read(); headers = dict(response.getheaders()); connection.close()
        return response.status, headers, body

    def test_lists_cyclones(self) -> None:
        status, _, body = self.get("/cyclones")
        self.assertEqual(status, 200); self.assertEqual(json.loads(body)[0]["cyclone_id"], "phailin-2013")

    def test_returns_track_geojson(self) -> None:
        status, _, body = self.get("/cyclones/phailin-2013/track")
        self.assertEqual(status, 200); self.assertEqual(json.loads(body)["features"][0]["geometry"]["type"], "Point")

    def test_rejects_unknown_cyclone(self) -> None:
        status, _, body = self.get("/cyclones/not-found/track")
        self.assertEqual(status, 404); self.assertEqual(json.loads(body)["error"], "Cyclone not found")

    def test_serves_map_page(self) -> None:
        status, headers, body = self.get("/")
        self.assertEqual(status, 200); self.assertIn("text/html", headers["Content-Type"]); self.assertIn(b"Historical cyclone tracks", body)

    def test_returns_phase_two_layers_and_location_feature_vector(self) -> None:
        status, _, body = self.get("/cyclones/phailin-2013/layers")
        self.assertEqual(status, 200); self.assertEqual(json.loads(body)[0]["layer_id"], "rainfall")
        status, _, body = self.get("/locations/phailin-grid-01/features?cyclone_id=phailin-2013")
        self.assertEqual(status, 200); self.assertEqual(len(json.loads(body)["features"]), 3)

    def test_returns_phase_three_risk_heatmap_and_explanation(self) -> None:
        status, _, body = self.get("/cyclones/phailin-2013/risk?valid_time=2013-10-13T00:00:00Z")
        self.assertEqual(status, 200); self.assertEqual(json.loads(body)["features"][0]["properties"]["band"], "high")
        status, _, body = self.get("/locations/phailin-grid-01/risk?cyclone_id=phailin-2013&valid_time=2013-10-13T00:00:00Z")
        payload = json.loads(body)
        self.assertEqual(status, 200); self.assertEqual(payload["risk_score"], 85); self.assertEqual(len(payload["feature_contributions"]), 5)

    def test_returns_phase_four_forecast_and_projected_risk(self) -> None:
        status, _, body = self.get("/cyclones/phailin-2013/forecast")
        forecast = json.loads(body)
        self.assertEqual(status, 200); self.assertEqual(forecast["points"][0]["source_type"], "forecast"); self.assertIn("uncertainty_km", forecast["points"][0])
        status, _, body = self.get("/cyclones/phailin-2013/forecast/metrics")
        self.assertEqual(status, 200); self.assertIn("test", json.loads(body))
        valid_time = forecast["points"][0]["valid_time"]
        status, _, body = self.get(f"/cyclones/phailin-2013/risk?valid_time={valid_time}")
        self.assertEqual(status, 200); self.assertEqual(json.loads(body)["features"][0]["properties"]["source_type"], "forecast")
