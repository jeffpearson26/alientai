import unittest

from audit_natural_panel_integrity import audit


def row(**changes):
    value = {
        "symbol": "ABC", "market_date": "2026-01-05", "as_of_utc": "2026-01-05T21:00:00Z",
        "future_market_date": "2026-01-12", "option_available": True,
        "short_interest_available": True, "short_interest_available_at_utc": "2025-12-24T23:59:59Z",
    }
    value.update(changes)
    return value


class NaturalPanelIntegrityTests(unittest.TestCase):
    def test_accepts_complete_point_in_time_row(self):
        report = audit([row()])
        self.assertTrue(report["passes"])

    def test_flags_duplicate_future_short_interest_and_bad_label(self):
        report = audit([row(), row(as_of_utc="2026-01-06T00:00:00Z", future_market_date="2026-01-05", short_interest_available_at_utc="2026-01-06T23:59:59Z")])
        self.assertFalse(report["passes"])
        self.assertEqual(report["failures"]["duplicate_symbol_market_date_keys"], 1)
        self.assertEqual(report["failures"]["as_of_after_market_date"], 1)
        self.assertEqual(report["failures"]["invalid_or_nonfuture_label_date"], 1)
        self.assertEqual(report["failures"]["short_interest_after_decision"], 1)


if __name__ == "__main__":
    unittest.main()
