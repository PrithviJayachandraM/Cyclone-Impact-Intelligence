# Cyclone Impact Intelligence

Cyclone Impact Intelligence is a decision-support prototype that turns historical cyclone tracks into a small, inspectable map experience. It is not an official warning system, forecast, or evacuation authority; official IMD and government guidance remains authoritative.

## Current implementation

The repository implements Phase 0 foundation and Phase 1 only.

- A versioned, sourced historical replay CSV for Cyclone Phailin (2013); see [docs/data-sources.md](docs/data-sources.md).
- Deterministic validation and normalization into `CycloneEvent` and `CycloneTrackPoint` documents.
- BigQuery GIS schema for events, points, and the future location-boundary contract.
- Read-only endpoints for health, cyclone selection, and GeoJSON tracks.
- A browser page that selects a historical cyclone and displays timestamps and metadata. It renders on Google Maps when `GOOGLE_MAPS_API_KEY` is set; otherwise it uses a local coordinate-map fallback so the demo works without a key or network access.
- A Cloud Run container definition and GCP setup notes, without credentials or live cloud resources.

Hazard layers, exposure, risk scores, forecasting, Gemini, scenarios, alerts, and all Phase 2+ features remain out of scope.

## Architecture

`data/raw` is the immutable replay input. `cyclone.normalize_tracks` validates it and writes normalized documents to `data/normalized`. The read-only HTTP API loads only the normalized data and provides it to the map page as JSON/GeoJSON. `infra/bigquery/phase1_schema.sql` is the production analytical-storage equivalent, using BigQuery `GEOGRAPHY` fields; `infra/cloud-run/Dockerfile` packages the same API for Cloud Run.

The canonical entity contract is in [docs/data-contract.md](docs/data-contract.md). This keeps prediction, risk calculation, and Gemini explanation separate from the Phase 1 data path, as required by the Technical Design Document.

## Project layout

```text
data/raw/             Versioned historical replay input
data/normalized/      Normalized local development dataset
src/cyclone/          Normalization, configuration, repository, and HTTP API
web/                  Map page
infra/bigquery/       BigQuery GIS data definition
infra/cloud-run/      Cloud Run container definition
infra/gcp/            Cloud deployment prerequisites
tests/                Deterministic unit and HTTP integration tests
```

## Local setup and run

Prerequisite: Python 3.11 or later. No third-party Python packages are required.

1. Copy `.env.example` to `.env` if you want to record local values. Export its values in your shell; the application intentionally does not load `.env` files itself.
2. From the repository root, set the source path and start the service:

```powershell
$env:PYTHONPATH = "src"
python -m cyclone.main
```

3. Open `http://127.0.0.1:8080`.

Set a browser-restricted Google Maps JavaScript API key in `GOOGLE_MAPS_API_KEY` for a tiled Google map. Leaving it empty uses the local fallback and is the recommended default for an offline demo. Do not use a server credential or unrestricted key.

## Rebuild the normalized dataset

```powershell
$env:PYTHONPATH = "src"
python scripts/normalize_tracks.py data/raw/phailin_2013_track.csv data/normalized
```

This repeatable transformation is the local counterpart to the Phase 1 Cloud Storage to BigQuery load. The BigQuery target schema and GIS expressions are in [infra/bigquery/phase1_schema.sql](infra/bigquery/phase1_schema.sql). Team-owned GCP setup is documented in [infra/gcp/README.md](infra/gcp/README.md).

## API

- `GET /health` returns service status.
- `GET /cyclones` lists available historical events.
- `GET /cyclones/{cyclone_id}/track` returns observed track points and a path as GeoJSON.

The API is deliberately read-only in this phase. It contains no risk, forecast, Gemini, or scenario endpoint.

## Testing

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

Tests validate normalization rules, environment configuration, API responses, GeoJSON structure, map-page delivery, and the unknown-cyclone error path. They run without Google Cloud, Google Maps, or live APIs.

## Configuration and security

`.env.example` documents all supported environment variables. `.env`, private keys, service-account files, and common credential formats are ignored by Git. GCP identifiers are configuration values, not credentials. Any deployment must use least-privilege service accounts and Secret Manager as described in the Technical Design Document.
