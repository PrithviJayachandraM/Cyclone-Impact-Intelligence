from __future__ import annotations

import unittest
from pathlib import Path

from cyclone.enrichment import EnrichmentRepository


class EnrichmentRepositoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repository = EnrichmentRepository(Path(__file__).parents[1] / "data" / "enriched")

    def test_returns_three_layer_metadata_records(self) -> None:
        layers = self.repository.layers("phailin-2013")
        self.assertEqual([layer["layer_id"] for layer in layers], ["rainfall", "elevation", "population"])
        self.assertTrue(all(layer["source"] for layer in layers))
        self.assertTrue(all(layer["observed_at"] for layer in layers))

    def test_returns_geospatial_locations_and_feature_vector(self) -> None:
        locations = self.repository.locations_geojson("phailin-2013")
        vector = self.repository.feature_vector("phailin-2013", "phailin-grid-01")
        self.assertEqual(locations["type"], "FeatureCollection")
        self.assertEqual(locations["features"][0]["geometry"]["type"], "Polygon")
        self.assertEqual(vector["location"]["location_id"], "phailin-grid-01")
        self.assertEqual(len(vector["features"]), 3)

    def test_returns_none_for_unknown_location_or_cyclone(self) -> None:
        self.assertIsNone(self.repository.feature_vector("phailin-2013", "not-found"))
        self.assertEqual(self.repository.locations_geojson("not-found")["features"], [])
