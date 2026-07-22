from __future__ import annotations

import unittest

from build_matched_catalyst_features import unique_rows


class CatalystJoinTests(unittest.TestCase):
    def test_news_key_uses_as_of_date(self):
        result = unique_rows([{"symbol": "AAA", "as_of_utc": "2024-01-02T20:00:00+00:00"}], news=True)
        self.assertIn(("AAA", "2024-01-02"), result)

    def test_duplicate_feature_keys_fail_closed(self):
        with self.assertRaises(ValueError):
            unique_rows([{"symbol": "AAA", "market_date": "2024-01-02"}, {"symbol": "AAA", "market_date": "2024-01-02"}])


if __name__ == "__main__":
    unittest.main()
