# Geospatial feasibility

Existing and Phase 8 tests verify deterministic track GeoJSON construction, valid coordinates, polygon/grid boundaries, proximity contributions through the risk engine, observed/forecast risk heatmap geometry, and a shifted scenario track using the same geometry passed to scoring.

Scenario tests cover a 20 km shift and boundary validation from -100 to 100 km. The two static demonstration grids deliberately limit geographic coverage; locations outside them have no risk result rather than fabricated coverage. Live raster-to-region statistics and district aggregation are **Not Executed** because Earth Engine and BigQuery are not configured in this replay repository.
