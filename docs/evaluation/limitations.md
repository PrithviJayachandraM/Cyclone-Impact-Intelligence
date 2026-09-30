# Limitations and failure modes

- One historical 2013 Phailin replay and two local demonstration grids; no real-time ingestion.
- Rainfall, elevation, and population are explicitly labelled local deterministic fixtures, not operational observations.
- The forecast is a constant-velocity baseline with documented error and uncertainty, not a validated operational forecast or ML model.
- Risk is transparent but uncalibrated; no storm-surge, infrastructure, road, shelter, or district-scale coverage is implemented.
- Vertex Gemini, BigQuery, Earth Engine, Pub/Sub, Eventarc, Scheduler, and Firebase were not executed live because no team-owned GCP project/credentials were supplied.
- Local alert deduplication is process-local; production needs durable shared receipts.
- The requested feasibility testing DOCX was absent; its additional criteria could not be assessed.
