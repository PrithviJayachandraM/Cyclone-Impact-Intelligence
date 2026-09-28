# Phase 2 enrichment data

Phase 2 keeps the raw raster source outside the application API. An Earth Engine workflow should calculate selected regional statistics for a small, reviewed geographic area, then persist only the derived location feature values to BigQuery and the application dataset. This matches the technical design: Earth Engine handles raster analysis while BigQuery stores queryable structured/geospatial outputs.

The checked-in `data/enriched/location_features.json` is a deterministic local fixture. It is not an Earth Engine result, forecast, official observation, risk assessment, or population estimate. Each layer includes its source label, timestamp, resolution, and processing version so the UI and API can surface provenance even when data are incomplete.

The persisted feature contract is:

- location identity and grid/admin geometry
- cyclone identifier
- layer identifier and numeric value
- unit, source, data timestamp, resolution, and processing version

A live Earth Engine integration requires a team-owned project, approved data collections, authenticated service identity, and a reviewed export/import job. It is intentionally not invoked by normal local tests.
