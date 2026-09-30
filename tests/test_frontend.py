from __future__ import annotations

import unittest
from pathlib import Path


class FrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).parents[1]
        cls.html = (root / "web" / "index.html").read_text(encoding="utf-8")
        cls.script = (root / "web" / "runtime.js").read_text(encoding="utf-8")

    def test_command_center_exposes_real_workflow_sections(self) -> None:
        for heading in ("Cyclone map", "Forecast trajectory", "Risk analysis", "What-if scenario simulation", "Gemini intelligence", "Alerts center"):
            self.assertIn(heading, self.html)
        self.assertIn('src="/runtime.js"', self.html)

    def test_frontend_uses_existing_backend_contracts(self) -> None:
        for endpoint in ("/cyclones", "/locations/", "/scenario", "/query", "/alerts/status", "/alerts/trigger"):
            self.assertIn(endpoint, self.script)
        self.assertNotIn("AIza", self.html + self.script)

    def test_frontend_labels_data_types_and_has_accessible_map(self) -> None:
        for label in ("OBSERVED", "PREDICTED", "SIMULATION"):
            self.assertIn(label, self.html)
        self.assertIn('role="img"', self.html)
        self.assertIn('aria-label="Observed cyclone track', self.html)

    def test_mobile_responsive_rules_are_present(self) -> None:
        self.assertIn("@media(max-width:620px)", self.html)
        self.assertIn(".map-frame,#map{min-height:360px}", self.html)
