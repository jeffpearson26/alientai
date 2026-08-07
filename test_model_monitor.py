import unittest

from fastapi.testclient import TestClient

from alientai_v2.model_monitor import (
    MODEL_SPECS,
    build_model_monitor_payload,
)
from model_monitor_server import app


class ModelMonitorTests(unittest.TestCase):
    def test_payload_has_requested_model_fields_and_safety_state(self):
        payload = build_model_monitor_payload()
        self.assertEqual(payload["status"], "success")
        self.assertTrue(payload["research_only"])
        self.assertFalse(payload["execution_enabled"])
        self.assertEqual(payload["summary"]["models"], len(MODEL_SPECS))
        self.assertGreaterEqual(payload["summary"]["active"], 6)
        for model in payload["models"]:
            self.assertTrue(model["name"])
            self.assertTrue(model["description"])
            self.assertTrue(model["horizon"])
            self.assertTrue(model["universe"])
            self.assertIn(
                model["state"],
                {"active", "attention", "blocked", "development", "preview"},
            )
            self.assertIn("daily", model)
            self.assertIn("win_rate_pct", model)
            self.assertIn("final_pl_pct", model)

    def test_known_future_programs_are_visible(self):
        payload = build_model_monitor_payload()
        by_id = {row["model_id"]: row for row in payload["models"]}
        late = by_id[
            "ai_semiconductor_late_60m_premarket_schwab_frozen_20260803"
        ]
        self.assertEqual(late["state"], "active")
        self.assertGreaterEqual(late["completed_signals"], 4)
        self.assertIn("AMAT", late["latest_picks"])

        autonomous = by_id["autonomous_transparent_20session"]
        self.assertEqual(autonomous["latest_pick_date"], "2026-08-04")
        self.assertEqual(len(autonomous["latest_picks"]), 5)
        self.assertGreaterEqual(autonomous["pending_signals"], 5)

        contextual = by_id["contextual_options_top_quarter"]
        self.assertEqual(contextual["completed_signals"], 5)
        self.assertEqual(contextual["win_rate_pct"], 80.0)
        self.assertAlmostEqual(contextual["final_pl_pct"], 1.894382)

        alpha_clone = by_id[
            "external_lambdarank_120_h20_alpha_vantage_v2_20260806"
        ]
        self.assertEqual(alpha_clone["state"], "active")
        self.assertEqual(alpha_clone["horizon"], "20 sessions")
        self.assertEqual(alpha_clone["completed_signals"], 0)
        self.assertIsNone(alpha_clone["final_pl_pct"])
        self.assertEqual(alpha_clone["latest_picks"], [])

    def test_page_and_json_routes_are_read_only(self):
        client = TestClient(app)
        page = client.get("/v2/models")
        self.assertEqual(page.status_code, 200)
        self.assertIn("AlientAI", page.text)
        self.assertIn("Model Intelligence Monitor", page.text)
        self.assertIn("Preliminary P/L", page.text)

        data = client.get("/v2/models/data")
        self.assertEqual(data.status_code, 200)
        self.assertFalse(data.json()["execution_enabled"])
        self.assertEqual(client.post("/v2/models/data").status_code, 405)


if __name__ == "__main__":
    unittest.main()
