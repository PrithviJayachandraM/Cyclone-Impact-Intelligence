# Cyclone Impact Intelligence

Cyclone Impact Intelligence is a decision-support prototype that combines a historical cyclone track with inspectable contextual data. It is not an official warning system, forecast, risk score, or evacuation authority; official IMD and government guidance remains authoritative.

## Current implementation

The repository implements Phase 0, Phase 1, and Phase 2 only.

- A versioned, sourced historical replay CSV for Cyclone Phailin (2013); see [docs/data-sources.md](docs/data-sources.md).
- Deterministic normalization into `CycloneEvent` and `CycloneTrackPoint` documents.
- A map page with cyclone selection, track timestamps, metadata, and optional Google Maps rendering.
- Persisted local location feature vectors for rainfall, elevation, and population, with layer toggles and click-through feature details. The bundled enriched data are explicitly non-operational fixtures; see [docs/phase2-enrichment.md](docs/phase2-enrichment.md).
- Read-only endpoints for tracks, layers, locations, and location feature vectors.
- BigQuery GIS schemas for Phase 1 and Phase 2 derived location features, plus a Cloud Run container definition and GCP setup notes.

Risk scores, risk heatmaps, forecasting, Gemini, scenarios, alerts, and all Phase 3+ features remain out of scope.

## Architecture

`data/raw` is immutable replay input. `cyclone.normalize_tracks` validates it and writes normalized track documents to `data/normalized`. Phase 2 persists derived contextual feature values in `data/enriched`; the read-only API joins them to a small geographic grid for the map.

In a cloud deployment, Cloud Storage retains raw files, Earth Engine calculates selected raster statistics, and BigQuery GIS persists structured points, boundaries, and regional features. The app does not access Earth Engine or BigQuery during local execution. The canonical entity contract is in [docs/data-contract.md](docs/data-contract.md).

## Project layout

```text
data/raw/             Versioned historical replay input
data/normalized/      Normalized historical events and track points
data/enriched/        Phase 2 local contextual-feature fixture
src/cyclone/          Normalization, configuration, repositories, and HTTP API
web/                  Map page and layer controls
infra/bigquery/       BigQuery GIS data definitions
infra/cloud-run/      Cloud Run container definition
infra/gcp/            Cloud deployment prerequisites
tests/                Deterministic unit and HTTP integration tests
```

## Local setup and run

Prerequisite: Python 3.11 or later. No third-party Python packages are required.

Export the desired values from `.env.example` in your shell. The application intentionally does not read `.env` files, avoiding an undeclared runtime dependency.

```powershell
$env:PYTHONPATH = "src"
python -m cyclone.main
```

Open `http://127.0.0.1:8080`, choose Phailin, toggle contextual layers, and click a grid to view its feature vector. Without `GOOGLE_MAPS_API_KEY`, the application uses an offline coordinate-map fallback. A browser-restricted Maps JavaScript API key enables basemap tiles; do not use server credentials or unrestricted keys.

## Data and cloud configuration

`CYCLONE_DATA_PATH` and `ENRICHMENT_DATA_PATH` select the local datasets. `EARTH_ENGINE_PROJECT` documents the future Earth Engine project identifier but is not used by the local fixture. It is not a credential.

For a cloud workflow, use the Phase 1 schema for events/tracks/boundaries and [infra/bigquery/phase2_schema.sql](infra/bigquery/phase2_schema.sql) for derived location features. [docs/phase2-enrichment.md](docs/phase2-enrichment.md) describes the intended Earth Engine-to-BigQuery boundary. Service identities and secrets must remain outside the repository.

## API

- `GET /health` returns service status.
- `GET /cyclones` lists available historical events.
- `GET /cyclones/{cyclone_id}/track` returns observed track points and a path as GeoJSON.
- `GET /cyclones/{cyclone_id}/layers` returns layer metadata and provenance.
- `GET /cyclones/{cyclone_id}/locations` returns grid locations and their layer values as GeoJSON.
- `GET /locations/{location_id}/features?cyclone_id={cyclone_id}` returns a selected location's complete feature vector.

The API is deliberately read-only. It does not calculate risk, invoke ML/Gemini, or create scenarios.

## Testing

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

Tests cover Phase 1 normalization and map/API behavior, Phase 2 feature metadata/provenance, GeoJSON locations, location vectors, unknown locations, and HTTP endpoint integration. They run without Google Cloud, Earth Engine, Google Maps, or live APIs.

## Configuration and security

`.env.example` documents supported environment variables. `.env`, private keys, service-account files, and common credential formats are ignored by Git. GCP identifiers are configuration values, not credentials. Deployments must use least-privilege service accounts and Secret Manager as described in the Technical Design Document.
