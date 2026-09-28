-- Replace PROJECT_ID and DATASET_ID before running with bq query --use_legacy_sql=false.
-- This table persists derived regional statistics, not large raw rasters.
CREATE TABLE IF NOT EXISTS `PROJECT_ID.DATASET_ID.location_features` (
  cyclone_id STRING NOT NULL,
  location_id STRING NOT NULL,
  layer_id STRING NOT NULL,
  value FLOAT64 NOT NULL,
  unit STRING NOT NULL,
  source STRING NOT NULL,
  observed_at TIMESTAMP NOT NULL,
  resolution STRING NOT NULL,
  processing_version STRING NOT NULL,
  loaded_at TIMESTAMP NOT NULL
)
CLUSTER BY cyclone_id, location_id, layer_id;
