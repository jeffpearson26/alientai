import unittest
from datetime import datetime, timezone

from build_ai_semiconductor_catalyst_panel import (
    analyst_action_from_title,
    analyst_proxy_features,
    combine_base_options_calls,
    executable_label,
)
from evaluate_ai_semiconductor_ablations import basket_metrics
from create_ai_semiconductor_news_requests import create_requests
import numpy as np


class CatalystPanelTests(unittest.TestCase):
    def test_target_specific_upgrade_is_accepted(self):
        self.assertEqual(analyst_action_from_title("Goldman upgrades Nvidia to Buy", "NVDA"), 1)

    def test_target_specific_downgrade_is_accepted(self):
        self.assertEqual(analyst_action_from_title("AMD downgraded to Underweight by analyst", "AMD"), -1)

    def test_other_company_action_is_rejected(self):
        self.assertEqual(analyst_action_from_title("IBM upgraded to Buy; Oracle shares rise", "ORCL"), 0)

    def test_product_upgrade_is_rejected(self):
        self.assertEqual(analyst_action_from_title("Palantir launches major software upgrade", "PLTR"), 0)

    def test_future_headline_is_excluded(self):
        payload = {"feed": [{
            "title": "Goldman upgrades Nvidia to Buy",
            "time_published": "20260730T220000",
        }]}
        result = analyst_proxy_features(payload, "NVDA", datetime(2026, 7, 30, 21, tzinfo=timezone.utc))
        self.assertEqual(result["analyst_proxy_event_count_14d"], 0)

    def test_label_enters_next_open_and_exits_fifth_close(self):
        daily = [
            ("2026-01-05", 100.0, 101.0),
            ("2026-01-06", 102.0, 103.0),
            ("2026-01-07", 104.0, 105.0),
            ("2026-01-08", 106.0, 107.0),
            ("2026-01-09", 108.0, 109.0),
            ("2026-01-12", 110.0, 112.0),
        ]
        result = executable_label(daily, "2026-01-05")
        self.assertEqual(result["label_entry_market_date"], "2026-01-06")
        self.assertEqual(result["label_exit_market_date"], "2026-01-12")
        self.assertAlmostEqual(result["label_forward_return_5d_av_pct"], (112 / 102 - 1) * 100)

    def test_baskets_use_ranked_scores_and_net_returns(self):
        rows = [{"r": 10.0}, {"r": -2.0}, {"r": 6.0}, {"r": 1.0}]
        result = basket_metrics(rows, np.asarray([0.9, 0.1, 0.8, 0.2]), "r")
        self.assertEqual(result["0.5"]["count"], 2)
        self.assertEqual(result["0.5"]["winner_rate_5pct"], 1.0)
        self.assertEqual(result["0.5"]["mean_net_return_pct"], 8.0)

    def test_news_requests_are_deduplicated_and_after_close(self):
        result = create_requests([
            {"symbol": "NVDA", "market_date": "2026-01-05"},
            {"symbol": "NVDA", "market_date": "2026-01-05"},
        ])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["as_of_utc"], "2026-01-05T21:00:00+00:00")

    def test_option_join_requires_exact_call_history(self):
        base = [{"symbol": "NVDA", "market_date": "2026-01-05"}]
        options = [{"symbol": "NVDA", "market_date": "2026-01-05", "option_call_volume": 10}]
        with self.assertRaisesRegex(ValueError, "missing base=0, calls=1"):
            combine_base_options_calls(base, options, [])


if __name__ == "__main__":
    unittest.main()
