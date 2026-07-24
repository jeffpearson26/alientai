import unittest

from audit_matched_premarket_labels import audit


def row(**changes):
    result = {"study_event_id": "e", "symbol": "ABC", "market_date": "2026-01-05", "future_market_date": "2026-01-12", "study_role": "winner", "premarket_label_available": True, "premarket_entry_bar_et": "2026-01-05 09:30:00", "premarket_exit_bar_et": "2026-01-12 16:00:00", "premarket_entry_price": 100, "premarket_exit_price": 110, "premarket_forward_return_5d_pct": 10}
    result.update(changes)
    return result


class PremarketLabelAuditTests(unittest.TestCase):
    def test_accepts_correct_label(self):
        self.assertTrue(audit([row()])["passes"])

    def test_flags_future_entry_and_wrong_return(self):
        report = audit([row(premarket_entry_bar_et="2026-01-05 09:35:00", premarket_forward_return_5d_pct=5)])
        self.assertFalse(report["passes"])
        self.assertEqual(1, report["failures"]["invalid_entry_timestamp"])
        self.assertEqual(1, report["failures"]["return_mismatch"])


if __name__ == "__main__":
    unittest.main()
