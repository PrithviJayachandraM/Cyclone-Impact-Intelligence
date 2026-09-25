from __future__ import annotations

import json
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from http.server import ThreadingHTTPServer

from cyclone.api import create_handler
from cyclone.repository import HistoricalTrackRepository


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        data_path = Path(__file__).parents[1] / "data" / "normalized"
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(HistoricalTrackRepository(data_path)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.thread.join()
        cls.server.server_close()

    def get(self, path: str) -> tuple[int, dict[str, str], bytes]:
        connection = HTTPConnection("127.0.0.1", self.server.server_port)
        connection.request("GET", path)
        response = connection.getresponse()
        body = response.read()
        headers = dict(response.getheaders())
        connection.close()
        return response.status, headers, body

    def test_lists_cyclones(self) -> None:
        status, _, body = self.get("/cyclones")
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(payload[0]["cyclone_id"], "phailin-2013")

    def test_returns_track_geojson(self) -> None:
        status, _, body = self.get("/cyclones/phailin-2013/track")
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(payload["type"], "FeatureCollection")
        self.assertGreater(len(payload["features"]), 1)
        self.assertEqual(payload["features"][0]["geometry"]["type"], "Point")

    def test_rejects_unknown_cyclone(self) -> None:
        status, _, body = self.get("/cyclones/not-found/track")
        self.assertEqual(status, 404)
        self.assertEqual(json.loads(body)["error"], "Cyclone not found")

    def test_serves_map_page(self) -> None:
        status, headers, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn(b"Historical cyclone tracks", body)
