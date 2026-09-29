"""Read-only local and Cloud Run-compatible HTTP API."""

from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from cyclone.enrichment import EnrichmentRepository
from cyclone.forecast import ForecastRepository
from cyclone.intelligence import GroundedAssistant
from cyclone.repository import HistoricalTrackRepository
from cyclone.risk import RiskRepository
from cyclone.scenario import ScenarioService, ScenarioValidationError, ScenarioParameters


STATIC_DIRECTORY = Path(__file__).parents[2] / "web"


def create_handler(repository: HistoricalTrackRepository, google_maps_api_key: str | None = None, enrichment_repository: EnrichmentRepository | None = None, risk_repository: RiskRepository | None = None, forecast_repository: ForecastRepository | None = None, assistant: GroundedAssistant | None = None, scenario_service: ScenarioService | None = None) -> type[BaseHTTPRequestHandler]:
    class CycloneHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            request = urlparse(self.path)
            path, query = request.path, parse_qs(request.query)
            if path == "/health":
                self.send_json(HTTPStatus.OK, {"status": "ok"})
            elif path == "/cyclones":
                self.send_json(HTTPStatus.OK, repository.list_events())
            elif path == "/map-config":
                self.send_json(HTTPStatus.OK, {"google_maps_api_key": google_maps_api_key})
            elif path.startswith("/cyclones/") and path.endswith("/forecast/metrics"):
                self.send_available(forecast_repository.metrics(self.cyclone_id(path, "forecast/metrics")) if forecast_repository else None, "Forecast data is not configured")
            elif path.startswith("/cyclones/") and path.endswith("/forecast"):
                self.send_available({"points": forecast_repository.forecast(self.cyclone_id(path, "forecast"))} if forecast_repository else None, "Forecast data is not configured")
            elif path.startswith("/cyclones/") and path.endswith("/layers"):
                self.send_available(enrichment_repository.layers(self.cyclone_id(path, "layers")) if enrichment_repository else None, "Enrichment data is not configured")
            elif path.startswith("/cyclones/") and path.endswith("/locations"):
                self.send_available(enrichment_repository.locations_geojson(self.cyclone_id(path, "locations")) if enrichment_repository else None, "Enrichment data is not configured")
            elif path.startswith("/cyclones/") and path.endswith("/risk"):
                self.send_available(risk_repository.risk_geojson(self.cyclone_id(path, "risk"), query.get("valid_time", [None])[0]) if risk_repository else None, "Risk data is not configured")
            elif path.startswith("/locations/") and path.endswith("/features"):
                self.location_response(enrichment_repository.feature_vector(query.get("cyclone_id", [""])[0], self.location_id(path, "features")) if enrichment_repository else None, "Location feature vector not found")
            elif path.startswith("/locations/") and path.endswith("/risk"):
                self.location_response(risk_repository.location_risk(query.get("cyclone_id", [""])[0], self.location_id(path, "risk"), query.get("valid_time", [None])[0]) if risk_repository else None, "Location risk not found")
            elif path.startswith("/cyclones/") and path.endswith("/track"):
                self.location_response(repository.track_geojson(self.cyclone_id(path, "track")), "Cyclone not found")
            elif path in {"/", "/index.html"}:
                self.send_file(STATIC_DIRECTORY / "index.html")
            elif path == "/app.js":
                self.send_file(STATIC_DIRECTORY / "app.js")
            else:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path not in {"/query", "/scenario"}:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"}); return
            if self.path == "/query" and assistant is None:
                self.send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "Grounded assistant is not configured"}); return
            if self.path == "/scenario" and (scenario_service is None or assistant is None):
                self.send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "Scenario service is not configured"}); return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 4096:
                    raise ValueError("request body must be between 1 and 4096 bytes")
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                if self.path == "/scenario":
                    result = scenario_service.simulate(str(payload.get("cyclone_id", "")), ScenarioParameters.from_payload(payload.get("parameters")), payload.get("valid_time"))
                    if result is not None:
                        result["explanation"] = assistant.explain_scenario(result)
                else:
                    result = assistant.answer(str(payload.get("question", "")), str(payload.get("cyclone_id", "")), payload.get("valid_time"))
                if result is None:
                    self.send_json(HTTPStatus.NOT_FOUND, {"error": "Cyclone not found"})
                else:
                    self.send_json(HTTPStatus.OK, result)
            except (UnicodeDecodeError, json.JSONDecodeError, ScenarioValidationError, ValueError) as error:
                self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

        @staticmethod
        def cyclone_id(path: str, suffix: str) -> str:
            return path.removeprefix("/cyclones/").removesuffix(f"/{suffix}").strip("/")

        @staticmethod
        def location_id(path: str, suffix: str) -> str:
            return path.removeprefix("/locations/").removesuffix(f"/{suffix}").strip("/")

        def send_available(self, payload: object, message: str) -> None:
            self.send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": message}) if payload is None else self.send_json(HTTPStatus.OK, payload)

        def location_response(self, payload: object, message: str) -> None:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": message}) if payload is None else self.send_json(HTTPStatus.OK, payload)

        def send_json(self, status: HTTPStatus, payload: object) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

        def send_file(self, path: Path) -> None:
            if not path.is_file():
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"}); return
            body = path.read_bytes()
            self.send_response(HTTPStatus.OK); self.send_header("Content-Type", f"{mimetypes.guess_type(path.name)[0] or 'application/octet-stream'}; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    return CycloneHandler
