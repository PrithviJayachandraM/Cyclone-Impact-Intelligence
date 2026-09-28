# Cyclone Impact Intelligence

Cyclone Impact Intelligence is a decision-support prototype that joins historical cyclone tracks, contextual features, transparent risk, and a modest forecast baseline. It is not an official warning system, forecast authority, evacuation authority, or scientifically calibrated impact model; official IMD and government guidance remains authoritative.

## Current implementation

The repository implements Phases 0–4 only.

- Phase 1: sourced Phailin 2013 replay data, deterministic track normalization, read API, and map.
- Phase 2: rainfall, elevation, and population feature vectors for demonstration grids with provenance and layer controls.
- Phase 3: deterministic 0–100 baseline risk scores, bands, factor contributions, and clickable heatmap.
- Phase 4: reproducible constant-velocity/intensity-drift forecasts at 6, 12, and 18 hours; forecast timestamps, horizons, uncertainty metadata, chronological backtest metrics, projected-risk calculation, and observed-versus-forecast map rendering. Details: [docs/phase4-forecast.md](docs/phase4-forecast.md).

Gemini, natural-language Q&A, advisories, scenarios, alerts, route optimization, and all Phase 5+ functionality remain out of scope.

## Architecture and data flow

`data/raw` is immutable replay input. Phase 1 normalizes it to `data/normalized`; Phase 2 supplies structured location features from `data/enriched`; Phase 4 generates forecast points and evaluation metrics in `data/forecast`; Phase 3's formula is applied to each forecast state and persists projected location scores in `data/risk`.

The browser distinguishes observed tracks (solid red) from predicted paths (dashed purple). Selecting an observed or forecast time switches the heatmap to the matching valid time. Prediction, risk, and future Gemini explanation remain separate, as required by the technical design.

In a cloud deployment, Cloud Storage holds raw data, BigQuery GIS stores structured features/forecast/risk outputs, and the existing Cloud Run service hosts this API and baseline inference. Local execution never contacts GCP, Earth Engine, Vertex AI, or Gemini.

## Project layout

```text
data/raw/             Immutable historical replay input
data/normalized/      Historical events and observed track points
data/enriched/        Phase 2 contextual-feature fixture
data/forecast/        Phase 4 forecast points and chronological evaluation
data/risk/            Baseline and forecast-projected risk scores
src/cyclone/          API, configuration, enrichment, forecast, and risk logic
scripts/              Commands rebuilding derived local artifacts
web/                  Observed/forecast map and risk UI
infra/bigquery/       BigQuery schemas for Phases 1–4
tests/                Deterministic unit and HTTP integration tests
```

## Local run

Python 3.11+ is required. No third-party Python packages are required. Export values from `.env.example` as needed.

```powershell
$env:PYTHONPATH = "src"
python scripts/build_forecasts.py data/normalized data/forecast
python scripts/build_risk_scores.py data/normalized data/enriched data/forecast data/risk
python -m cyclone.main
```

Open `http://127.0.0.1:8080`. The **Track/risk time** selector switches between the latest observed track state and 6/12/18-hour forecasts. The map renders observations as solid red and projections as dashed purple. Click a colored grid to inspect risk contributions for that selected time.

## Configuration and cloud prerequisites

`CYCLONE_DATA_PATH`, `ENRICHMENT_DATA_PATH`, `FORECAST_DATA_PATH`, and `RISK_DATA_PATH` choose local artifacts. `GOOGLE_MAPS_API_KEY` is optional and must be browser restricted. GCP variables in `.env.example` are identifiers, not credentials.

Cloud table definitions are available in [phase4_schema.sql](infra/bigquery/phase4_schema.sql). A live production model would need approved data, a team-owned GCP project, service identity, and defensible evaluation. The included baseline runs behind the existing Cloud Run packaging and does not need Vertex AI.

## API

- `GET /health`
- `GET /cyclones`
- `GET /cyclones/{cyclone_id}/track`
- `GET /cyclones/{cyclone_id}/layers`
- `GET /cyclones/{cyclone_id}/locations`
- `GET /locations/{location_id}/features?cyclone_id={cyclone_id}`
- `GET /cyclones/{cyclone_id}/risk?valid_time={ISO-8601}`
- `GET /locations/{location_id}/risk?cyclone_id={cyclone_id}&valid_time={ISO-8601}`
- `GET /cyclones/{cyclone_id}/forecast`
- `GET /cyclones/{cyclone_id}/forecast/metrics`

All endpoints remain read-only. There is no Gemini tool, advisory retrieval, scenario creation, or alerting.

## Testing

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

Tests cover Phase 1–3 functionality plus reproducible forecast output, horizon and uncertainty metadata, chronological split ordering, baseline metric recording, insufficient-history rejection, forecast API contracts, and projected risk integration. They run without live cloud or AI services.

## Security

`.env.example` contains configuration placeholders only. `.env`, private keys, service-account files, and common credential formats are Git-ignored. Production service identities must use least privilege and Secret Manager; no credentials belong in this repository.
