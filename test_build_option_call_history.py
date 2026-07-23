from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from build_option_call_history import dates, totals


class BuildOptionCallHistoryTests(unittest.TestCase):
    def test_dates_uses_archive_day_layout_and_filters_missing_symbol(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for day, symbol in (("2026-07-01", "AAA"), ("2026-07-02", "BBB"), ("2026-07-03", "AAA")):
                path = root / "2026" / day / f"{symbol}.json.gz"
                path.parent.mkdir(parents=True, exist_ok=True)
                with gzip.open(path, "wt", encoding="utf-8") as handle:
                    json.dump({"data": []}, handle)

            self.assertEqual(dates(root, "AAA"), ["2026-07-01", "2026-07-03"])

    def test_totals_counts_only_call_volume_and_open_interest(self) -> None:
        volume, open_interest = totals([
            {"type": "call", "volume": "12", "open_interest": "30"},
            {"type": "CALL", "volume": 8, "open_interest": 20},
            {"type": "put", "volume": 999, "open_interest": 999},
        ])
        self.assertEqual(volume, 20.0)
        self.assertEqual(open_interest, 50.0)


if __name__ == "__main__":
    unittest.main()
