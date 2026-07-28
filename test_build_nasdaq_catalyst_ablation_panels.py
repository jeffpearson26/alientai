import unittest

from build_nasdaq_catalyst_ablation_panels import paired_panels


class NasdaqCatalystAblationPanelTests(unittest.TestCase):
    def test_exact_key_join_creates_identical_paired_rows(self):
        base = [{"symbol": "AAA", "market_date": "2026-01-02", "technical_rsi_2": 5}]
        catalyst = [{
            "symbol": "AAA",
            "market_date": "2026-01-02",
            "as_of_utc": "2026-01-02T20:00:00+00:00",
            "insider_purchase_count_30d": 2,
        }]
        baseline, enriched, summary = paired_panels(
            base, catalyst, ("insider_purchase_count_30d",)
        )
        self.assertEqual(baseline, base)
        self.assertEqual(len(enriched), 1)
        self.assertEqual(
            enriched[0]["technical_catalyst_insider_purchase_count_30d"], 2
        )
        self.assertEqual(summary["paired_rows"], 1)

    def test_future_catalyst_row_is_rejected(self):
        base = [{"symbol": "AAA", "market_date": "2026-01-02"}]
        catalyst = [{
            "symbol": "AAA",
            "market_date": "2026-01-02",
            "as_of_utc": "2026-01-03T00:00:00+00:00",
        }]
        baseline, enriched, summary = paired_panels(base, catalyst, ())
        self.assertEqual(baseline, [])
        self.assertEqual(enriched, [])
        self.assertEqual(summary["rejected_future_or_invalid_rows"], 1)

    def test_duplicate_catalyst_keys_fail_closed(self):
        base = [{"symbol": "AAA", "market_date": "2026-01-02"}]
        catalyst = [{
            "symbol": "AAA", "market_date": "2026-01-02",
            "as_of_utc": "2026-01-02T20:00:00+00:00",
        }] * 2
        with self.assertRaises(ValueError):
            paired_panels(base, catalyst, ())

    def test_missing_values_are_explicit_zeroes(self):
        base = [{"symbol": "AAA", "market_date": "2026-01-02"}]
        catalyst = [{
            "symbol": "AAA", "market_date": "2026-01-02",
            "as_of_utc": "2026-01-02T20:00:00+00:00",
            "insider_days_since_latest_purchase": None,
        }]
        _, enriched, _ = paired_panels(
            base, catalyst, ("insider_days_since_latest_purchase",)
        )
        self.assertEqual(
            enriched[0]["technical_catalyst_insider_days_since_latest_purchase"], 0.0
        )


if __name__ == "__main__":
    unittest.main()
