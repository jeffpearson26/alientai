import csv
import gzip
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from audit_daily_price_source_alignment import audit


class DailyPriceSourceAlignmentTests(unittest.TestCase):
    def _write_sources(self, root: Path, alpha_close: str) -> None:
        (root / "schwab").mkdir()
        (root / "alpha").mkdir()
        with (root / "schwab" / "ABC_schwab_1d_max.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["date", "close"])
            writer.writeheader(); writer.writerows([{"date": "2026-07-21", "close": "100"}, {"date": "2026-07-22", "close": "102"}])
        with gzip.open(root / "alpha" / "ABC_daily.json.gz", "wt", encoding="utf-8") as handle:
            json.dump({"Time Series (Daily)": {"2026-07-22": {"4. close": alpha_close}}}, handle)

    def test_same_day_match_passes(self):
        with TemporaryDirectory() as directory:
            root = Path(directory); self._write_sources(root, "102")
            self.assertTrue(audit(["ABC"], root / "alpha", root / "schwab")["same_day_alignment_passes"])

    def test_prior_session_match_fails_same_day_alignment(self):
        with TemporaryDirectory() as directory:
            root = Path(directory); self._write_sources(root, "100")
            result = audit(["ABC"], root / "alpha", root / "schwab")
            self.assertFalse(result["same_day_alignment_passes"])
            self.assertEqual(1, result["symbols"][0]["prior_session_matches"])


if __name__ == "__main__":
    unittest.main()
