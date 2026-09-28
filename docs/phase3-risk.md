# Phase 3 risk baseline

The Phase 3 engine is a transparent, deterministic baseline for the demo. It is not a scientifically calibrated impact model, official warning, evacuation recommendation, or forecast.

For each Phase 2 location, it calculates a 0–100 score from five normalized inputs:

| Input | Normalization | Weight |
| --- | --- | ---: |
| Maximum observed wind | wind speed / 250 kph, capped at 1 | 20% |
| Accumulated rainfall | rainfall / 300 mm, capped at 1 | 25% |
| Track proximity | 1 - nearest observed track distance / 250 km, capped at 0–1 | 25% |
| Low-elevation flood susceptibility | 1 - elevation / 100 m, capped at 0–1 | 15% |
| Population exposure | population / 100,000 people, capped at 1 | 15% |

Bands are low (0–33), medium (34–66), and high (67–100). Each persisted score records every raw input, normalized input, weight, and score-point contribution, plus a model version and valid time. The constants are intentionally documented rather than hidden; calibration and historical backtesting are future work.

Build the committed local risk artifact after changing its input fixtures:

```powershell
$env:PYTHONPATH = "src"
python scripts/build_risk_scores.py data/normalized data/enriched data/risk
```

In Google Cloud, a batch/service process should read BigQuery track/location features and persist results into `risk_scores` using [infra/bigquery/phase3_schema.sql](../infra/bigquery/phase3_schema.sql). No GCP SDK, ML endpoint, or Gemini service is required for the local baseline.
