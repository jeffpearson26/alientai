from __future__ import annotations

import unittest

from import_finra_short_interest import normalize, parse_iso


class FinraShortInterestImporterTests(unittest.TestCase):
    def test_preserves_publication_not_settlement_as_availability(self) -> None:
        row = normalize({"Symbol": "abc", "ShortInterest": "1,250"}, symbol_column="Symbol", shares_column="ShortInterest",
                        settlement_date="2026-01-15", publication_timestamp_utc="2026-01-27T18:00:00Z")
        self.assertEqual(row["available_at_utc"], "2026-01-27T18:00:00Z")
        self.assertEqual(row["short_interest_shares"], 1250.0)

    def test_requires_offset_aware_publication_time(self) -> None:
        with self.assertRaises(ValueError):
            parse_iso("2026-01-27T18:00:00")


if __name__ == "__main__":
    unittest.main()
