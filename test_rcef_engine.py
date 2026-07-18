from __future__ import annotations

import unittest

from alientai_v2.engines.rcef_engine import classify_regime, evaluate_evidence, scan


def strong_evidence():
    return {
        "market_context": {
            "spy_return_20d_pct": 4.0,
            "spy_return_5d_pct": 1.0,
            "vix": 16.0,
            "breadth_above_50d_pct": 64.0,
        },
        "specialists": {
            "price": {"expected_excess_return_pct": 2.2, "probability_up": 0.72, "confidence": 0.90},
            "events": {"expected_excess_return_pct": 2.8, "probability_up": 0.75, "confidence": 0.92},
            "news": {"expected_excess_return_pct": 1.5, "probability_up": 0.67, "confidence": 0.80},
            "market": {"expected_excess_return_pct": 1.4, "probability_up": 0.65, "confidence": 0.85},
        },
        "analogs": {"cases": 90, "avg_excess_return_pct": 1.8, "win_rate": 0.68},
        "predicted_drawdown_pct": -1.1,
        "data_quality": 0.97,
        "liquidity_score": 0.95,
        "round_trip_cost_pct": 0.25,
    }


class RCEFEngineTests(unittest.TestCase):
    def test_regime_router(self):
        self.assertEqual(classify_regime({"vix": 35}), "high_volatility")
        self.assertEqual(
            classify_regime({"vix": 18, "spy_return_20d_pct": 4, "breadth_above_50d_pct": 60}),
            "bull_trend",
        )

    def test_strong_consistent_evidence_is_watch_only(self):
        result = evaluate_evidence(strong_evidence())
        self.assertTrue(result["eligible"])
        self.assertEqual(result["decision"], "WATCH")
        self.assertTrue(result["research_only"])
        self.assertGreater(result["expected_net_excess_return_pct"], 0.5)

    def test_missing_specialists_fails_closed(self):
        evidence = strong_evidence()
        evidence["specialists"] = {"price": evidence["specialists"]["price"]}
        result = evaluate_evidence(evidence)
        self.assertEqual(result["decision"], "AVOID")
        self.assertIn("insufficient_specialists", result["abstention_reasons"])

    def test_too_few_analogs_fails_closed(self):
        evidence = strong_evidence()
        evidence["analogs"]["cases"] = 5
        result = evaluate_evidence(evidence)
        self.assertEqual(result["decision"], "AVOID")
        self.assertIn("insufficient_analog_cases", result["abstention_reasons"])

    def test_analog_disagreement_reduces_eligibility(self):
        evidence = strong_evidence()
        evidence["analogs"]["avg_excess_return_pct"] = -2.0
        evidence["analogs"]["win_rate"] = 0.35
        result = evaluate_evidence(evidence)
        self.assertFalse(result["eligible"])
        self.assertIn("specialists_or_analogs_disagree", result["abstention_reasons"])

    def test_scan_never_emits_buy_candidate(self):
        rows = scan([{"symbol": "XYZ", "price": 10, "rcef_evidence": strong_evidence()}], {})
        self.assertEqual(len(rows), 1)
        self.assertNotEqual(rows[0]["decision"], "BUY_CANDIDATE")
        self.assertIn("RESEARCH_ONLY", rows[0]["warnings"])


if __name__ == "__main__":
    unittest.main()

