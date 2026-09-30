from __future__ import annotations

import json
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

from cyclone.api import create_handler
from cyclone.alerts import AlertWorkflow, LocalEventPublisher, LocalNotificationSender
from cyclone.enrichment import EnrichmentRepository
from cyclone.forecast import ForecastRepository
from cyclone.intelligence import AdvisoryRepository, GroundedAssistant
from cyclone.repository import HistoricalTrackRepository
from cyclone.risk import RiskRepository
from cyclone.scenario import ScenarioService


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).parents[1]
        tracks = HistoricalTrackRepository(root / "data" / "normalized")
        enrichment = EnrichmentRepository(root / "data" / "enriched")
        risk = RiskRepository(root / "data" / "risk", enrichment.locations)
        forecast = ForecastRepository(root / "data" / "forecast")
        assistant = GroundedAssistant(tracks, enrichment, risk, forecast, AdvisoryRepository(root / "data" / "advisories"))
        scenarios = ScenarioService(tracks, enrichment, risk, forecast)
        alerts = AlertWorkflow(risk, LocalNotificationSender(), threshold=67, stale_after_minutes=60)
        publisher = LocalEventPublisher(alerts.process)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(tracks, enrichment_repository=enrichment, risk_repository=risk, forecast_repository=forecast, assistant=assistant, scenario_service=scenarios, alert_workflow=alerts, event_publisher=publisher))
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

    def post(self, path: str, payload: dict[str, object]) -> tuple[int, bytes]:
        connection = HTTPConnection("127.0.0.1", self.server.server_port)
        connection.request("POST", path, body=json.dumps(payload), headers={"Content-Type": "application/json"})
        response = connection.getresponse(); body = response.read(); status = response.status; connection.close()
        return status, body

    def test_lists_cyclones(self) -> None:
        status, _, body = self.get("/cyclones")
        self.assertEqual(status, 200); self.assertEqual({event["cyclone_id"] for event in json.loads(body)}, {"phailin-2013", "hudhud-2014", "fani-2019"})

    def test_returns_added_historical_track_without_inventing_risk_coverage(self) -> None:
        status, _, body = self.get("/cyclones/hudhud-2014/track")
        self.assertEqual(status, 200); self.assertEqual(len(json.loads(body)["features"]), 7)
        status, _, body = self.get("/cyclones/hudhud-2014/risk")
        self.assertEqual(status, 200); self.assertEqual(json.loads(body)["features"], [])

    def test_returns_track_geojson(self) -> None:
        status, _, body = self.get("/cyclones/phailin-2013/track")
        self.assertEqual(status, 200); self.assertEqual(json.loads(body)["features"][0]["geometry"]["type"], "Point")

    def test_rejects_unknown_cyclone(self) -> None:
        status, _, body = self.get("/cyclones/not-found/track")
        self.assertEqual(status, 404); self.assertEqual(json.loads(body)["error"], "Cyclone not found")

    def test_serves_map_page(self) -> None:
        status, headers, body = self.get("/")
        self.assertEqual(status, 200); self.assertIn("text/html", headers["Content-Type"]); self.assertIn(b"Cyclone Intelligence Command Center", body)

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

    def test_returns_grounded_phase_five_answer(self) -> None:
        status, body = self.post("/query", {"question": "Why is the risk high?", "cyclone_id": "phailin-2013", "valid_time": "2013-10-13T00:00:00Z"})
        payload = json.loads(body)
        self.assertEqual(status, 200); self.assertTrue(payload["supported"]); self.assertEqual(payload["tool"], "get_location_risk"); self.assertTrue(payload["evidence"])

    def test_returns_phase_six_simulation_and_rejects_invalid_parameters(self) -> None:
        status, body = self.post("/scenario", {"cyclone_id": "phailin-2013", "valid_time": "2013-10-13T00:00:00Z", "parameters": {"track_shift_km": 20, "intensity_multiplier": 1.2, "rainfall_multiplier": 1.1}})
        payload = json.loads(body)
        self.assertEqual(status, 200); self.assertEqual(payload["scenario"]["status"], "simulation"); self.assertTrue(payload["explanation"]["simulation"])
        status, body = self.post("/scenario", {"cyclone_id": "phailin-2013", "parameters": {"intensity_multiplier": 3}})
        self.assertEqual(status, 400); self.assertIn("intensity_multiplier", json.loads(body)["error"])

    def test_runs_local_phase_seven_alert_trigger_and_suppresses_duplicate(self) -> None:
        request = {"event_id": "api-alert-1", "cyclone_id": "phailin-2013", "valid_time": "2013-10-13T00:00:00Z"}
        status, body = self.post("/alerts/trigger", request)
        payload = json.loads(body)
        self.assertEqual(status, 200); self.assertEqual(payload["delivery"], "local"); self.assertEqual(payload["result"]["outcomes"][0]["status"], "alert_sent")
        status, body = self.post("/alerts/trigger", request)
        self.assertEqual(status, 200); self.assertEqual(json.loads(body)["result"]["outcomes"][0]["status"], "duplicate_suppressed")
        status, _, body = self.get("/alerts/status")
        self.assertEqual(status, 200); self.assertFalse(json.loads(body)["stale"])
