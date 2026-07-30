import unittest

from prepare_stratified_natural_news_requests import select_dates, select_rows


def row(day, symbol):
    return {"market_date": day, "symbol": symbol, "as_of_utc": f"{day}T21:00:00+00:00"}


class StratifiedNaturalNewsRequestTests(unittest.TestCase):
    def test_selects_evenly_spaced_complete_dates(self):
        rows = [row(f"2026-01-{day:02d}", f"S{index}") for day in range(1, 11) for index in range(4)]
        self.assertEqual(select_dates(rows, 3, 4), ["2026-01-01", "2026-01-05", "2026-01-10"])

    def test_excludes_sparse_days_and_preserves_unique_keys(self):
        rows = [row("2026-01-01", "A")] + [row("2026-01-02", f"S{index}") for index in range(3)] + [row("2026-01-03", f"T{index}") for index in range(3)] + [row("2026-01-04", f"U{index}") for index in range(3)]
        dates = select_dates(rows, 3, 3)
        selected = select_rows(rows, dates)
        self.assertEqual(dates, ["2026-01-02", "2026-01-03", "2026-01-04"])
        self.assertEqual(len(selected), 9)

    def test_rejects_duplicate_point_in_time_keys(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            select_rows([row("2026-01-01", "A"), row("2026-01-01", "A")], ["2026-01-01"])


if __name__ == "__main__":
    unittest.main()
