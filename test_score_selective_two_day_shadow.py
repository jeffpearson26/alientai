import unittest

from score_selective_two_day_shadow import select_shadow_candidates


class TwoDayShadowScorerTests(unittest.TestCase):
    def test_incomplete_universe_fails_closed(self):
        result = select_shadow_candidates(
            [{"symbol": "AAA", "market_date": "2026-07-27"}],
            [0.9],
            score_cutoff=0.5,
            expected_universe_size=2,
            minimum_coverage_fraction=0.95,
        )
        self.assertEqual(result["status"], "INCOMPLETE_UNIVERSE_HOLD")
        self.assertEqual(result["candidates"], [])

    def test_keeps_every_independently_qualified_candidate(self):
        rows = [
            {"symbol": "AAA", "market_date": "2026-07-27"},
            {"symbol": "BBB", "market_date": "2026-07-27"},
        ]
        result = select_shadow_candidates(
            rows, [0.8, 0.7], score_cutoff=0.6,
            expected_universe_size=2, minimum_coverage_fraction=0.95,
        )
        self.assertEqual([row["symbol"] for row in result["candidates"]], ["AAA", "BBB"])
        self.assertFalse(result["execution_enabled"])

    def test_mixed_dates_and_duplicates_are_rejected(self):
        with self.assertRaises(ValueError):
            select_shadow_candidates(
                [
                    {"symbol": "AAA", "market_date": "2026-07-27"},
                    {"symbol": "AAA", "market_date": "2026-07-28"},
                ],
                [0.8, 0.7], score_cutoff=0.6,
                expected_universe_size=2, minimum_coverage_fraction=0.95,
            )


if __name__ == "__main__":
    unittest.main()
