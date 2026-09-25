"""Small read-only HTTP API suitable for local use and Cloud Run packaging."""

from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

from cyclone.repository import HistoricalTrackRepository


STATIC_DIRECTORY = Path(__file__).parents[2] / "web"


def create_handler(
    repository: HistoricalTrackRepository, google_maps_api_key: str | None = None
) -> type[BaseHTTPRequestHandler]:
    class CycloneHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/health":
                self.send_json(HTTPStatus.OK, {"status": "ok"})
            elif path == "/cyclones":
                self.send_json(HTTPStatus.OK, repository.list_events())
            elif path == "/map-config":
                self.send_json(HTTPStatus.OK, {"google_maps_api_key": google_maps_api_key})
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
