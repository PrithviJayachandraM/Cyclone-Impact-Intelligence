# Cyclone Impact Intelligence

Cyclone Impact Intelligence is a decision-support prototype that joins a historical cyclone track, contextual features, and an explainable location-risk baseline. It is not an official warning system, forecast, evacuation authority, or scientifically calibrated impact model; official IMD and government guidance remains authoritative.

## Current implementation

The repository implements Phases 0–3 only.

- Phase 1: sourced Phailin 2013 replay data, deterministic track normalization, track API, and map.
- Phase 2: persisted rainfall, elevation, and population feature vectors for demonstration grids, with provenance and layer controls.
- Phase 3: a deterministic 0–100 baseline risk score, bands, stored factor contributions, risk API, and clickable grid heatmap. Formula and limitations: [docs/phase3-risk.md](docs/phase3-risk.md).

Forecasting, Gemini, scenarios, alerts, route optimization, and every Phase 4+ feature remain out of scope.

## Architecture

`data/raw` remains immutable replay input. Phase 1 normalizes it to `data/normalized`; Phase 2 supplies structured location features from `data/enriched`; Phase 3 combines both inputs in a dependency-free risk engine and persists transparent outputs in `data/risk`. The API serves these artifacts to the browser.

For cloud deployment, Cloud Storage retains raw data, Earth Engine produces selected regional raster statistics, BigQuery GIS stores structured features, and a Cloud Run service hosts the API. The local baseline never contacts GCP, Earth Engine, Vertex AI, or Gemini. This preserves the TDD boundary: prediction, risk, and explanation remain separate.

## Project layout

```text
data/raw/             Versioned historical replay input
data/normalized/      Historical events and observed track points
data/enriched/        Phase 2 contextual-feature fixture
data/risk/            Phase 3 persisted baseline scores and contributions
src/cyclone/          Normalization, enrichment, risk, configuration, and API
scripts/              Rebuild commands for derived local artifacts
web/                  Map, contextual-layer, and risk-heatmap UI
infra/bigquery/       BigQuery GIS/data schemas for Phases 1–3
tests/                Deterministic unit and HTTP integration tests
```

## Local run

Python 3.11 or later is required; no third-party Python package is required. Export values from `.env.example` as needed.

```powershell
$env:PYTHONPATH = "src"
python -m cyclone.main
```

Open `http://127.0.0.1:8080`, select Phailin, leave **Baseline risk heatmap** enabled, then click a colored grid. The panel shows the 0–100 score, band, model version, valid time, and five stored contributions. Contextual layers remain independently selectable. Without `GOOGLE_MAPS_API_KEY`, the offline coordinate-map fallback works normally.

Rebuild the risk artifact after modifying the source fixtures:

```powershell
$env:PYTHONPATH = "src"
python scripts/build_risk_scores.py data/normalized data/enriched data/risk
```

## Configuration and cloud prerequisites

`CYCLONE_DATA_PATH`, `ENRICHMENT_DATA_PATH`, and `RISK_DATA_PATH` select local artifacts. `GOOGLE_MAPS_API_KEY` is optional and must be browser restricted. `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_STORAGE_BUCKET`, `BIGQUERY_DATASET`, and `EARTH_ENGINE_PROJECT` are identifiers only, never credentials.

Cloud risk persistence is defined in [infra/bigquery/phase3_schema.sql](infra/bigquery/phase3_schema.sql). A live cloud pipeline needs a team-owned GCP project, service identity, and approved datasets, but is not required for local development or tests.

## API

- `GET /health`
- `GET /cyclones`
- `GET /cyclones/{cyclone_id}/track`
- `GET /cyclones/{cyclone_id}/layers`
- `GET /cyclones/{cyclone_id}/locations`
- `GET /locations/{location_id}/features?cyclone_id={cyclone_id}`
- `GET /cyclones/{cyclone_id}/risk` — heatmap GeoJSON with scores and contributions
- `GET /locations/{location_id}/risk?cyclone_id={cyclone_id}` — one location's score explanation

All endpoints are read-only. There is no prediction, ML endpoint, Gemini call, scenario mutation, or alerting.

## Testing

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

The suite covers deterministic score calculation, score bands, contribution storage, invalid/missing features, Phase 1–3 API contracts, configuration, and historical-track normalization. It runs without Google Cloud, Earth Engine, Maps, Vertex AI, or Gemini.

## Security

`.env.example` documents configuration only. `.env`, private keys, service-account files, and common credential formats are Git-ignored. Production deployments must use least-privilege service identities and Secret Manager; no credentials belong in this repository.
