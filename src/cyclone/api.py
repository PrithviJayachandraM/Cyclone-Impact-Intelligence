"""Small read-only HTTP API suitable for local use and Cloud Run packaging."""

from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from cyclone.enrichment import EnrichmentRepository
from cyclone.repository import HistoricalTrackRepository


STATIC_DIRECTORY = Path(__file__).parents[2] / "web"


def create_handler(
    repository: HistoricalTrackRepository,
    google_maps_api_key: str | None = None,
    enrichment_repository: EnrichmentRepository | None = None,
) -> type[BaseHTTPRequestHandler]:
    class CycloneHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            request = urlparse(self.path)
            path = request.path
            if path == "/health":
                self.send_json(HTTPStatus.OK, {"status": "ok"})
            elif path == "/cyclones":
                self.send_json(HTTPStatus.OK, repository.list_events())
            elif path == "/map-config":
                self.send_json(HTTPStatus.OK, {"google_maps_api_key": google_maps_api_key})
            elif path.startswith("/cyclones/") and path.endswith("/layers"):
                self.send_enrichment(enrichment_repository.layers(path.removeprefix("/cyclones/").removesuffix("/layers").strip("/")) if enrichment_repository else None)
            elif path.startswith("/cyclones/") and path.endswith("/locations"):
                self.send_enrichment(enrichment_repository.locations_geojson(path.removeprefix("/cyclones/").removesuffix("/locations").strip("/")) if enrichment_repository else None)
            elif path.startswith("/locations/") and path.endswith("/features"):
                cyclone_id = parse_qs(request.query).get("cyclone_id", [""])[0]
                vector = enrichment_repository.feature_vector(cyclone_id, path.removeprefix("/locations/").removesuffix("/features").strip("/")) if enrichment_repository else None
                self.send_json(HTTPStatus.OK, vector) if vector else self.send_json(HTTPStatus.NOT_FOUND, {"error": "Location feature vector not found"})
            elif path.startswith("/cyclones/") and path.endswith("/track"):
                cyclone_id = path.removeprefix("/cyclones/").removesuffix("/track").strip("/")
                track = repository.track_geojson(cyclone_id)
                self.send_json(HTTPStatus.OK, track) if track else self.send_json(HTTPStatus.NOT_FOUND, {"error": "Cyclone not found"})
            elif path in {"/", "/index.html"}:
                self.send_file(STATIC_DIRECTORY / "index.html")
            elif path == "/app.js":
                self.send_file(STATIC_DIRECTORY / "app.js")
            else:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

        def send_enrichment(self, payload: object) -> None:
            if payload is None:
                self.send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "Enrichment data is not configured"})
            else:
                self.send_json(HTTPStatus.OK, payload)

        def send_json(self, status: HTTPStatus, payload: object) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def send_file(self, path: Path) -> None:
            if not path.is_file():
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
                return
            body = path.read_bytes()
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    return CycloneHandler
