# Phase 4 forecast baseline

Phase 4 uses a deterministic constant-velocity and intensity-drift baseline. It extrapolates the latest two observed track points to 6, 12, and 18 hour horizons. Each output stores `forecast_created_at`, `valid_time`, `horizon_hours`, predicted coordinates, intensity, uncertainty, source type, and model version.

The baseline is evaluated chronologically with the single available Phailin replay: first three points for training history, the next point for validation, and the final two points for test. Evaluation uses rolling one-step predictions with no observations from the target or future windows. Recorded metrics are mean track error in kilometres and wind mean absolute error in kph.

The small single-event fixture means these metrics are reproducibility evidence only; they do not establish forecast accuracy or operational readiness. The model is deliberately a transparent hackathon baseline rather than a numerical weather model.

Rebuild forecast then projected-risk artifacts after changing track fixtures:

```powershell
$env:PYTHONPATH = "src"
python scripts/build_forecasts.py data/normalized data/forecast
python scripts/build_risk_scores.py data/normalized data/enriched data/forecast data/risk
```

Cloud deployment can package the same inference/API logic in the existing Cloud Run service. `infra/bigquery/phase4_schema.sql` defines target forecast and evaluation tables. A Vertex AI endpoint is not required for this baseline; a more complex future model may use one after adequate data and evaluation are available.
