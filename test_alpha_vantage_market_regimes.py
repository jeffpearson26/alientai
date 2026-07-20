import unittest

from download_alpha_vantage_market_regimes import requests_to_archive, safe_message


class AlphaVantageMarketRegimeTests(unittest.TestCase):
    def test_request_names_and_parameters_are_unique(self):
        requests_ = requests_to_archive()
        names = [name for name, _ in requests_]
        parameters = [tuple(sorted(params.items())) for _, params in requests_]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len(parameters), len(set(parameters)))

    def test_core_regime_series_are_included(self):
        by_name = dict(requests_to_archive())
        self.assertEqual(by_name["real_gdp_quarterly"]["interval"], "quarterly")
        self.assertEqual(by_name["treasury_yield_10year_daily"]["maturity"], "10year")
        self.assertEqual(by_name["wti_monthly"]["function"], "WTI")
        self.assertIn("nonfarm_payroll_monthly", by_name)

    def test_api_key_is_redacted_from_errors(self):
        key = "secret-premium-key"
        message = safe_message(f"request failed for {key}", key)
        self.assertNotIn(key, message)
        self.assertIn("[REDACTED]", message)


if __name__ == "__main__":
    unittest.main()
