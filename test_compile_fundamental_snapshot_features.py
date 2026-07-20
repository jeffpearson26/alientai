from __future__ import annotations

import gzip
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from compile_fundamental_snapshot_features import available_symbols, compile_symbol


class CompileFundamentalSnapshotFeatureTests(unittest.TestCase):
    def test_compiles_available_sources_without_requiring_all_three(self):
        document = {
            "collected_at_utc": "2026-07-19T20:00:00Z",
            "payload": {"estimates": [{
                "date": "2026-09-30", "horizon": "fiscal quarter",
                "eps_estimate_average": "2", "eps_estimate_average_7_days_ago": "1",
            }]},
        }
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "earnings_estimates" / "IBM.json.gz"
            path.parent.mkdir(parents=True)
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                json.dump(document, handle)
            self.assertEqual(available_symbols(root), ["IBM"])
            result = compile_symbol(root, "IBM", "2026-07-20T20:00:00Z")
        self.assertTrue(result["earnings_estimate_available"])
        self.assertAlmostEqual(result["earnings_estimate_eps_change_7d_pct"], 100.0)
        self.assertNotIn("shares_outstanding_available", result)


if __name__ == "__main__":
    unittest.main()
