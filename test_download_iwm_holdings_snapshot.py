import unittest

from download_iwm_holdings_snapshot import snapshot_from_csv


CSV_TEXT = '''iShares Russell 2000 ETF\nFund Holdings as of Jul 22, 2026\nTicker,Name,Asset Class,Sector\nAAA,Example A,Equity,Industrials\nBBB,Example B,Equity,Health Care\n,Cash,Cash and/or Derivatives,Cash and/or Derivatives\nAAA,Duplicate,Equity,Industrials\n'''


class IwmHoldingsSnapshotTests(unittest.TestCase):
    def test_builds_dated_equity_only_provenanced_snapshot(self):
        snapshot = snapshot_from_csv(CSV_TEXT, source_url="https://example.com/iwm.csv", retrieved_at_utc="2026-07-23T20:00:00Z")
        self.assertEqual(snapshot["as_of_date"], "2026-07-22")
        self.assertEqual(snapshot["symbols"], ["AAA", "BBB"])
        self.assertEqual(snapshot["source_row_count"], 4)
        self.assertEqual(snapshot["equity_row_count"], 3)

    def test_fails_closed_when_csv_has_no_ticker_header(self):
        with self.assertRaisesRegex(ValueError, "Ticker header"):
            snapshot_from_csv("not,a,holdings,file\n", source_url="https://example.com", retrieved_at_utc="2026-07-23T20:00:00Z")

    def test_fails_closed_when_provider_returns_html(self):
        with self.assertRaisesRegex(ValueError, "returned HTML"):
            snapshot_from_csv("<!DOCTYPE html><html></html>", source_url="https://example.com", retrieved_at_utc="2026-07-23T20:00:00Z")


if __name__ == "__main__":
    unittest.main()
