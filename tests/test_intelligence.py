from __future__ import annotations

import unittest
from pathlib import Path

from cyclone.enrichment import EnrichmentRepository
from cyclone.forecast import ForecastRepository
from cyclone.intelligence import AdvisoryRepository, GeminiUnavailable, GroundedAssistant
from cyclone.repository import HistoricalTrackRepository
from cyclone.risk import RiskRepository


class GroundedAssistantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).parents[1]
        tracks = HistoricalTrackRepository(root / "data" / "normalized")
        enrichment = EnrichmentRepository(root / "data" / "enriched")
        cls.assistant = GroundedAssistant(tracks, enrichment, RiskRepository(root / "data" / "risk", enrichment.locations), ForecastRepository(root / "data" / "forecast"), AdvisoryRepository(root / "data" / "advisories"))

    def ask(self, question: str, valid_time: str | None = None) -> dict[str, object]:
        result = self.assistant.answer(question, "phailin-2013", valid_time)
        self.assertIsNotNone(result)
        return result or {}

    def test_risk_answer_is_grounded_in_structured_contributions(self) -> None:
        result = self.ask("Why is the risk high?", "2013-10-13T00:00:00Z")
        self.assertEqual(result["tool"], "get_location_risk")
        self.assertIn("24.44", str(result["answer"]))
        self.assertEqual(result["context"]["risk_scores"][0]["source_type"], "observed")
        self.assertTrue(result["evidence"])

    def test_exposure_answer_uses_existing_location_features(self) -> None:
        result = self.ask("Which location has the highest exposure?", "2013-10-13T00:00:00Z")
        self.assertEqual(result["tool"], "get_exposure_summary")
        self.assertIn("84000", str(result["answer"]))

    def test_forecast_summary_distinguishes_forecast_and_uncertainty(self) -> None:
        result = self.ask("Summarize the current situation", "2013-10-13T06:00:00Z")
        self.assertEqual(result["context"]["forecast"]["source_type"], "forecast")
        self.assertIn("±60.0 km", str(result["answer"]))
        self.assertTrue(result["uncertainty"])

    def test_advisory_query_returns_approved_reference(self) -> None:
        result = self.ask("What official guidance is available?")
        self.assertEqual(result["tool"], "search_advisories")
        self.assertEqual(result["context"]["advisories"][0]["approved"], True)
        self.assertIn("IMD", str(result["answer"]))

    def test_operational_instruction_is_safely_unsupported(self) -> None:
        result = self.ask("Should everyone evacuate now?")
        self.assertFalse(result["supported"])
        self.assertIn("cannot issue", str(result["answer"]))

    def test_unanswerable_question_returns_safe_uncertainty(self) -> None:
        result = self.ask("Will a bridge collapse?")
        self.assertFalse(result["supported"])
        self.assertIn("not an official warning", str(result["uncertainty"]))

    def test_external_responder_failure_uses_grounded_local_fallback(self) -> None:
        class UnavailableResponder:
            def respond(self, question: str, context: dict[str, object]) -> str:
                raise GeminiUnavailable("unavailable")

        fallback = GroundedAssistant(self.assistant.tracks, self.assistant.enrichment, self.assistant.risk, self.assistant.forecast, self.assistant.advisories, UnavailableResponder())
        result = fallback.answer("Why is the risk high?", "phailin-2013", "2013-10-13T00:00:00Z")
        self.assertIsNotNone(result)
        self.assertEqual((result or {})["provider"], "local-fallback")
