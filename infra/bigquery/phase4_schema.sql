-- Replace PROJECT_ID and DATASET_ID before running with bq query --use_legacy_sql=false.
CREATE TABLE IF NOT EXISTS `PROJECT_ID.DATASET_ID.forecast_points` (
  cyclone_id STRING NOT NULL,
  forecast_created_at TIMESTAMP NOT NULL,
  valid_time TIMESTAMP NOT NULL,
  horizon_hours INT64 NOT NULL,
  latitude FLOAT64 NOT NULL,
  longitude FLOAT64 NOT NULL,
  intensity_kph FLOAT64 NOT NULL,
  uncertainty_km FLOAT64 NOT NULL,
  model_version STRING NOT NULL,
  source_type STRING NOT NULL
)
CLUSTER BY cyclone_id, valid_time;

CREATE TABLE IF NOT EXISTS `PROJECT_ID.DATASET_ID.forecast_evaluations` (
  cyclone_id STRING NOT NULL,
  model_version STRING NOT NULL,
  split_name STRING NOT NULL,
  split_start TIMESTAMP NOT NULL,
  split_end TIMESTAMP NOT NULL,
  mean_track_error_km FLOAT64 NOT NULL,
  mean_wind_mae_kph FLOAT64 NOT NULL
);
