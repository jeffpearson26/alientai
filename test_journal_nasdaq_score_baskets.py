from __future__ import annotations

import unittest

from journal_nasdaq_score_baskets import basket_for_score


class NasdaqScoreBasketJournalTests(unittest.TestCase):
    def test_assigns_non_overlapping_frozen_baskets(self) -> None:
        edges = [0, 50, 60, 100]
        cutoffs = {0: 0.0, 50: 0.5, 60: 0.6, 100: 1.0}
        self.assertEqual(basket_for_score(0.25, cutoffs, edges), "0-50")
        self.assertEqual(basket_for_score(0.5, cutoffs, edges), "50-60")
        self.assertEqual(basket_for_score(0.6, cutoffs, edges), "60-100")
        self.assertEqual(basket_for_score(1.0, cutoffs, edges), "60-100")

    def test_rejects_score_outside_frozen_range(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not fit"):
            basket_for_score(1.1, {0: 0.0, 100: 1.0}, [0, 100])


if __name__ == "__main__":
    unittest.main()
