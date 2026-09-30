# Cyclone Impact Intelligence

Cyclone Impact Intelligence is a decision-support prototype that joins historical cyclone tracks, contextual features, transparent risk, and a modest forecast baseline. It is not an official warning system, forecast authority, evacuation authority, or scientifically calibrated impact model; official IMD and government guidance remains authoritative.

## Current implementation

The repository implements Phases 0–9 only.

- Phase 1: sourced Phailin 2013 replay data, deterministic track normalization, read API, and map.
- Phase 2: rainfall, elevation, and population feature vectors for demonstration grids with provenance and layer controls.
- Phase 3: deterministic 0–100 baseline risk scores, bands, factor contributions, and clickable heatmap.
- Phase 4: reproducible constant-velocity/intensity-drift forecasts at 6, 12, and 18 hours; forecast timestamps, horizons, uncertainty metadata, chronological backtest metrics, projected-risk calculation, and observed-versus-forecast map rendering. Details: [docs/phase4-forecast.md](docs/phase4-forecast.md).
- Phase 5: grounded situation briefings and natural-language Q&A. The assistant uses narrow read-only backend tools for cyclone state, location risk, exposure, and curated approved advisory references. Every result returns structured context, provenance/timestamps, uncertainty, and a safety boundary.
- Phase 6: deterministic what-if simulation for copied track, intensity, and rainfall inputs. It reruns the Phase 3 risk engine, returns baseline-versus-simulation deltas, renders side-by-side maps, and grounds a concise simulation explanation in both result sets.
- Phase 7: event-driven, threshold-based risk alerts with local Pub/Sub-style processing, Eventarc-compatible event handling, dashboard freshness state, deduplication, and an optional Firebase Cloud Messaging adapter.
- Phase 8: reproducible feasibility evaluation, frozen Phailin demo evidence, data/risk/geospatial checks, grounded-assistant golden questions, local performance measurements, reliability results, and documented limitations.
- Phase 9: a responsive, map-first Cyclone Intelligence Command Center that presents the existing replay, forecast, risk, grounded-assistant, simulation, and alert workflows as one demonstration experience.

The replay catalog now includes verified sampled IMD best-track data for Phailin (2013), Hudhud (2014), and Fani (2019). Phailin remains the only fully enriched and risk-scored demo. Hudhud and Fani deliberately display as track-only historical replays until equivalent location, rainfall, elevation, and population coverage is ingested; the UI does not fabricate risk, exposure, scenario, or alert results for them.

Evacuation/route advice and future functionality remain out of scope.

## Command Center frontend

The browser experience is a dependency-free responsive web application served by the existing Python API. It uses the current endpoints and deterministic Phailin replay only; it does not add fake values or change risk, forecast, Gemini, simulation, or alert logic.

- **Overview** presents cyclone identity, peak risk, selected-grid population exposure, observed wind, and replay/system status.
- **Cyclone Map** is the visual center. It distinguishes solid red observed tracks from dashed purple predicted tracks, toggles existing environmental/exposure layers, and supports grid-level risk investigation.
- **Forecast**, **Risk Analysis**, **What-If Simulation**, **Gemini Intelligence**, and **Alerts** are focused views over the existing backend contracts.
- Observed, predicted, and simulated values use explicit badges and language throughout. The scenario remains clearly labelled as a simulation, not a forecast.

Click **Start Phailin replay demo** for the stable walkthrough: map, grid investigation, grounded question, 20 km east / 1.2x intensity / 1.1x rainfall simulation, comparison, then local alert evaluation. Use the cyclone selector to browse the additional track-only historical replays.

## Architecture and data flow

`data/raw` is immutable replay input. Phase 1 normalizes it to `data/normalized`; Phase 2 supplies structured location features from `data/enriched`; Phase 4 generates forecast points and evaluation metrics in `data/forecast`; Phase 3's formula is applied to each forecast state and persists projected location scores in `data/risk`.

The browser distinguishes observed tracks (solid red) from predicted paths (dashed purple). Selecting an observed or forecast time switches the heatmap to the matching valid time. The Phase 5 assistant sends that selected time to the backend, which retrieves structured evidence before creating a briefing. Forecast facts are labelled as forecasts and include uncertainty; observed facts remain distinct.

In a cloud deployment, Cloud Storage holds raw data, BigQuery GIS stores structured features/forecast/risk outputs, and Cloud Run hosts the API. Gemini is isolated behind the backend's narrow controlled tools: it has neither direct BigQuery access nor browser credentials. Local execution uses deterministic local adapters and never contacts GCP, Earth Engine, Vertex AI, Gemini, Pub/Sub, or Firebase.

## What-If Scenario Simulation

Phase 6 treats every what-if request as a **simulation**, never an observation or official forecast. It copies the selected baseline track and Phase 2 location features, shifts the copied track east/west, scales copied wind intensity and/or rainfall, then invokes the existing Phase 3 `calculate_scores` risk engine. The persisted baseline track and risk artifacts are not changed.

Supported demo parameters are deliberately bounded for an interactive prototype: `track_shift_km` from -100 to 100 (positive is east), `intensity_multiplier` from 0.5 to 1.5, and `rainfall_multiplier` from 0.5 to 1.5. At least one value must differ from the baseline (0 km, 1.0x, 1.0x). These bounds are implementation safeguards; the source documents specify the parameter types but not operational limits.

Use the **What-If Scenario Simulation** controls below the map and run, for example, a 20 km east shift with 1.2x intensity. The page displays baseline and simulation maps at the same extent and lists the risk-score delta for each location. The Phase 5 assistant architecture receives the structured baseline, simulation, and comparison context to produce the accompanying explanation. Its numerical source remains the deterministic scenario engine.

## Event-Driven Alerting

Phase 7 evaluates the existing persisted Phase 3 risk results; it does not introduce another risk calculation. The default alert threshold is `67`, the existing boundary for the Phase 3 `high` band, and `ALERT_RISK_THRESHOLD` makes it configurable. Alert payloads include only the cyclone, location, score/band, threshold, valid time, model/source context, and bounded decision-support message.

```text
Cloud Scheduler -> /alerts/trigger -> Pub/Sub -> Eventarc -> /events/pubsub
    -> Cloud Run alert workflow -> Firebase Cloud Messaging
```

The local `ALERT_EVENT_TRANSPORT=local` path uses the same validated workflow synchronously. The dashboard's **Run local risk evaluation** button triggers it for the selected cyclone/time and displays threshold, freshness, and last-event state. `POST /events/pubsub` accepts an Eventarc-style Pub/Sub envelope for local integration testing.

Alert receipt IDs are derived from the unchanged alert condition, so duplicate Pub/Sub delivery does not send a second notification during the running service lifetime. Notification failures are not marked as sent; the Eventarc ingress returns `503` so the managed event platform may retry the message. Alerts are demo decision-support signals only, not official warnings or evacuation instructions. Deployment details and least-privilege service roles are in [phase7-eventing.md](infra/gcp/phase7-eventing.md).

## Feasibility evidence and final demo

Phase 8 freezes one reproducible historical replay: **Phailin 2013** at `2013-10-13T00:00:00Z`, with two local coastal demonstration grids. The fixed demo uses a 20 km east track shift, 1.2x intensity, and 1.1x rainfall. Its expected deterministic scenario results are 85 to 88 for grid 01 and 66 to 70 for grid 02; the configured alert threshold of 67 sends one alert for grid 01 and suppresses a repeated unchanged event.

The complete evidence pack is in [docs/evaluation](docs/evaluation/README.md), including data quality, geospatial, risk, forecast/model, Gemini, performance, reliability, usability, limitations, final metrics, the [architecture story](docs/evaluation/architecture.md), and the [demo runbook](docs/evaluation/final-demo.md). It records local evidence only and marks unconfigured live GCP/Vertex/Firebase services as **Not Executed**.

## Project layout

```text
data/raw/             Immutable historical replay input
data/normalized/      Historical events and observed track points
data/enriched/        Phase 2 contextual-feature fixture
data/forecast/        Phase 4 forecast points and chronological evaluation
data/risk/            Baseline and forecast-projected risk scores
data/advisories/      Curated approved advisory references for Phase 5 retrieval
src/cyclone/          API, alerts, configuration, intelligence, enrichment, forecast, and risk logic
scripts/              Commands rebuilding derived local artifacts
web/                  Responsive command-center map and frontend assets
infra/gcp/            Cloud deployment guidance, including Phase 7 eventing
docs/evaluation/      Phase 8 reproducible evidence and final demo runbook
tests/                Deterministic unit and HTTP integration tests
```

## Local run

Python 3.11+ is required. No third-party Python packages are required. Export values from `.env.example` as needed.

```powershell
$env:PYTHONPATH = "src"
python scripts/build_forecasts.py data/normalized data/forecast
python scripts/build_risk_scores.py data/normalized data/enriched data/forecast data/risk
python scripts/run_evaluation.py
python -m cyclone.main
```

Open `http://127.0.0.1:8080`. The **Track/risk time** selector switches between the latest observed track state and 6/12/18-hour forecasts. The map renders observations as solid red and projections as dashed purple. Click a colored grid to inspect risk contributions for that selected time. Use the **Grounded assistant** section to ask for a situation summary, why risk is high, highest exposure, or approved guidance. Use **Run local risk evaluation** to exercise the Phase 7 trigger, processing, threshold decision, notification adapter, and freshness display locally.

The dashboard is optimized for desktop and laptop presentation, while its navigation and map panels collapse for tablet-sized layouts. It requires no browser-exposed secrets or additional frontend environment variables. `GOOGLE_MAPS_API_KEY` remains optional for the existing map integration; without it the command center uses its local coordinate-map fallback.

## Configuration and cloud prerequisites

`CYCLONE_DATA_PATH`, `ENRICHMENT_DATA_PATH`, `FORECAST_DATA_PATH`, `RISK_DATA_PATH`, and `ADVISORY_DATA_PATH` choose local artifacts. `GOOGLE_MAPS_API_KEY` is optional and must be browser restricted. The normal GCP variables in `.env.example` are identifiers, not credentials; `VERTEX_AI_ACCESS_TOKEN` is a deliberately blank runtime secret placeholder for the optional Vertex mode.

Cloud table definitions are available in [phase4_schema.sql](infra/bigquery/phase4_schema.sql). `GEMINI_PROVIDER=local` is the default and keeps development deterministic. To opt into Vertex, set `GEMINI_PROVIDER=vertex`, `GCP_PROJECT_ID`, `GCP_REGION`, `VERTEX_AI_MODEL`, and a runtime-only `VERTEX_AI_ACCESS_TOKEN`; never commit the token. Production should use a least-privilege service identity and Secret Manager to supply credentials. The API falls back to the local grounded response if Vertex is unavailable, preserving the evidence and safety boundary.

For Phase 7, retain `ALERT_EVENT_TRANSPORT=local` and `NOTIFICATION_PROVIDER=local` for normal development. Cloud deployment sets them to `pubsub` and `firebase`, respectively, and supplies `PUBSUB_TOPIC`, `FIREBASE_PROJECT_ID`, `FIREBASE_NOTIFICATION_TOPIC`, and runtime-only access tokens through Secret Manager or the service environment. `LOG_LEVEL=INFO` emits JSON stage logs without secrets. The Scheduler caller must have only Cloud Run invocation access; the publisher only topic publishing access; Eventarc only event delivery access; and the service only the data-read/Firebase Messaging permissions it requires.

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
- `POST /query` with `question`, `cyclone_id`, and optional `valid_time`
- `POST /scenario` with `cyclone_id`, optional `valid_time`, and `parameters`
- `GET /alerts/status`
- `POST /alerts/trigger` with a risk-evaluation event
- `POST /events/pubsub` with an Eventarc-style Pub/Sub envelope

`POST /query` supports situation summaries, risk explanations, exposure summaries, and curated advisory retrieval. `POST /scenario` calculates but does not persist a simulation, returning map-ready baseline/simulation tracks, risk scores, deltas, and a grounded explanation. `POST /alerts/trigger` is the Scheduler/manual ingress and publishes a validated event; `/events/pubsub` is the Eventarc delivery ingress. The service refuses to issue evacuation orders, routes, or operational instructions.

## Testing

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python scripts/run_evaluation.py
```

Tests cover Phases 1–7 plus Phase 8 frozen data-quality validation, extreme risk bounds/contribution checks, a seven-question grounded assistant evaluation, and Phase 9 frontend asset/contracts for the command-center workflow. They run without live cloud or AI services. `scripts/run_evaluation.py` refreshes the JSON evidence pack used by the final demo.

## Security

`.env.example` contains configuration placeholders only. `.env`, private keys, service-account files, and common credential formats are Git-ignored. Production service identities must use least privilege and Secret Manager; no credentials belong in this repository.
