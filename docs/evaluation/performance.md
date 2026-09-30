# Local performance snapshot

`scripts/run_evaluation.py` measures twenty local runs each for risk GeoJSON retrieval, deterministic scenario simulation, grounded local response construction, and local alert processing. It records minimum, maximum, mean, and p95 milliseconds in [performance-results.json](performance-results.json).

These figures are small-dataset, single-process feasibility evidence only. They do not measure network latency, browser rendering, BigQuery, Earth Engine, Vertex AI, Pub/Sub, Eventarc, Firebase, concurrency, or production capacity.
