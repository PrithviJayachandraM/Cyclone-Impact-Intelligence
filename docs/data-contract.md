# Phase 0 data contract

This document defines the canonical names and minimum fields from the Technical Design Document. Phase 1 implements only `CycloneEvent`, `CycloneTrackPoint`, and an empty `Location` boundary table. It does not calculate exposure, risk, predictions, advisories, or scenarios.

| Entity | Minimum fields | Phase 1 status |
| --- | --- | --- |
| CycloneEvent | `cyclone_id`, `name`, `basin`, `source`, `observed_at` | Implemented |
| CycloneTrackPoint | `cyclone_id`, `timestamp`, `latitude`, `longitude`, `wind_speed_kph`, `pressure_hpa`, `source_type` | Implemented |
| ForecastPoint | `cyclone_id`, `forecast_created_at`, `valid_time`, `latitude`, `longitude`, `intensity_kph`, `uncertainty_km` | Implemented in Phase 4 |
| WeatherObservation | `location_id`, `timestamp`, `rainfall`, `wind`, `pressure`, `temperature`, `source` | Phase 2 |
| Location | `location_id`, `geometry`, `administrative_level`, `name` | GIS DDL only |
| Exposure | `location_id`, `population`, `roads`, `buildings`, `critical_assets` | Phase 2 |
| RiskScore | `location_id`, `cyclone_id`, `valid_time`, `score`, `band`, `feature_contributions` | Implemented in Phase 3 |
| Advisory | `advisory_id`, `source`, `issued_at`, `valid_from`, `valid_to`, `content/reference` | Phase 5 |
| Scenario | `scenario_id`, `base_event`, `parameter_changes`, `created_at`, `owner` | Phase 6 |

Every processed record must retain its source, relevant data timestamp, and processing version. The BigQuery DDL uses `GEOGRAPHY` for points and boundaries; application JSON uses WGS84 longitude/latitude coordinates.
