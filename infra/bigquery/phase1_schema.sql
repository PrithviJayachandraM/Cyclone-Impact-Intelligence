-- Replace PROJECT_ID and DATASET_ID before running with bq query --use_legacy_sql=false.
-- Geometry values are derived during normalization/loading, never entered by a browser client.

CREATE TABLE IF NOT EXISTS `PROJECT_ID.DATASET_ID.cyclone_events` (
  cyclone_id STRING NOT NULL,
  name STRING NOT NULL,
  basin STRING NOT NULL,
  source STRING NOT NULL,
  observed_at TIMESTAMP NOT NULL,
  processing_version STRING NOT NULL,
  loaded_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS `PROJECT_ID.DATASET_ID.cyclone_track_points` (
  cyclone_id STRING NOT NULL,
  timestamp TIMESTAMP NOT NULL,
  latitude FLOAT64 NOT NULL,
  longitude FLOAT64 NOT NULL,
  wind_speed_kph FLOAT64,
  pressure_hpa FLOAT64,
  source_type STRING NOT NULL,
  geography GEOGRAPHY NOT NULL,
  source STRING NOT NULL,
  processing_version STRING NOT NULL,
  loaded_at TIMESTAMP NOT NULL
)
CLUSTER BY cyclone_id, timestamp;

-- The Phase 1 API does not expose boundaries yet; this table establishes the GIS contract
-- needed when a vetted boundary source is added in a later phase.
CREATE TABLE IF NOT EXISTS `PROJECT_ID.DATASET_ID.location_boundaries` (
  location_id STRING NOT NULL,
  name STRING NOT NULL,
  administrative_level STRING NOT NULL,
  geometry GEOGRAPHY NOT NULL,
  source STRING NOT NULL,
  source_timestamp TIMESTAMP,
  processing_version STRING NOT NULL
);

-- Loader reference: ST_GEOGPOINT(longitude, latitude) for each normalized track point.
-- A complete track can be formed on demand with ST_MAKELINE(ARRAY_AGG(geography ORDER BY timestamp)).
