# Final demo runbook

## Fixed scenario

- Cyclone: `phailin-2013`.
- Source: IMD RSMC Annual Review 2013 Table 2.2.1.
- Selected observed time: `2013-10-13T00:00:00Z`.
- Area: two coastal demonstration grids.
- Baseline risk: grid 01 is 85/high; grid 02 is 66/medium.
- Scenario: 20 km east shift, 1.2x intensity, 1.1x rainfall.
- Expected scenario result: deterministic changed track and risk comparison, clearly labelled Simulation.
- Alert: threshold 67 sends one local alert for grid 01; re-running the unchanged event suppresses the duplicate.

## Run

```powershell
$env:PYTHONPATH = "src"
python scripts/build_forecasts.py data/normalized data/forecast
python scripts/build_risk_scores.py data/normalized data/enriched data/forecast data/risk
python scripts/run_evaluation.py
python -m cyclone.main
```

Open `http://127.0.0.1:8080`. Select Phailin and the observed timestamp. Inspect a grid, ask **Why is this location high risk?**, run the fixed simulation, then click **Run local risk evaluation**. The evidence response should distinguish observed data, forecast data, and simulation data throughout.

## Five-minute architecture story

Historical source data is normalized into immutable replay records. Contextual features and risk scores remain structured and deterministic; the forecast produces a separate, uncertainty-labelled projection. Gemini receives only compact controlled context to explain those results. Scenarios copy and transform inputs before reusing the risk engine, so the baseline stays immutable. The dashboard renders the layers, comparison, and local alert state. In cloud deployment, Scheduler, Pub/Sub, Eventarc, Cloud Run, and Firebase decouple periodic evaluation and notification, while local adapters keep the same workflow demonstrable without cloud credentials.
