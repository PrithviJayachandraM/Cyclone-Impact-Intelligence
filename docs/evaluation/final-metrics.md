# Final metrics summary

| Area | Method and population | Result | Limitation |
| --- | --- | --- | --- |
| Data quality | One Phailin historical replay, 6 track points, 2 grids | Pass; no detected required-field, ordering, geometry, or provenance issues | Historical 2013 fixture only |
| Geospatial | Track/grid GeoJSON, deterministic proximity scoring, scenario shift tests | Pass | No live Earth Engine or district aggregation |
| Risk | Phase 3 unit/evaluation tests, normal and extreme inputs | 0-100 bounded and contribution sums remain explainable | Uncalibrated demonstration baseline |
| Forecast | Chronological Phase 4 split | Validation: 30.78 km track error, 29.0 kph wind MAE; test: 73.71 km, 78.85 kph | Constant-velocity baseline; no ML comparison |
| Gemini grounding | Seven local golden/unsupported questions | 7/7 pass with structured context or safe uncertainty | No live Vertex execution |
| Simulation | Fixed 20 km east, 1.2x intensity, 1.1x rainfall | Grid 01: 85 to 88; grid 02: 66 to 70 | Two static grids only |
| Alerts | Threshold 67; duplicate local event | One alert sent, duplicate suppressed; medium score remains no-alert | Receipts are process-local |
| Performance | 20 local single-process runs | Values in [performance-results.json](performance-results.json) | Not a production load test |
| Usability | Developer walkthrough of one end-to-end flow | Core journey complete | No external-user study |

All live GCP service checks are explicitly **Not Executed** in [results.json](results.json), not treated as successful proxies.
