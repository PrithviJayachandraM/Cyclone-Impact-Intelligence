-- Replace PROJECT_ID and DATASET_ID before running with bq query --use_legacy_sql=false.
-- Phase 3 baseline outputs: structured, versioned, and explainable.
CREATE TABLE IF NOT EXISTS `PROJECT_ID.DATASET_ID.risk_scores` (
  cyclone_id STRING NOT NULL,
  location_id STRING NOT NULL,
  valid_time TIMESTAMP NOT NULL,
  score INT64 NOT NULL,
  band STRING NOT NULL,
  feature_contributions JSON NOT NULL,
  model_version STRING NOT NULL,
  calculated_at TIMESTAMP NOT NULL
)
CLUSTER BY cyclone_id, location_id;
