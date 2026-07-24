import unittest

from validate_current_universe_manifest import validate_manifest


class CurrentUniverseManifestTests(unittest.TestCase):
    def test_accepts_dated_provenanced_snapshot_and_reports_overlap(self):
        report = validate_manifest({
            "schema_version": "1",
            "universe_name": "Example Small-Cap Universe",
            "as_of_date": "2026-07-23",
            "retrieved_at_utc": "2026-07-23T18:00:00Z",
            "source_name": "Example Provider",
            "source_url": "https://example.com/constituents",
            "symbols": ["AAA", "BBB", "AAA"],
        }, excluded_symbols={"BBB"})
        self.assertEqual(report["status"], "valid")
        self.assertEqual(report["valid_symbol_count"], 2)
        self.assertEqual(report["duplicate_symbol_count"], 1)
        self.assertEqual(report["excluded_symbol_overlap"], ["BBB"])

    def test_fails_closed_without_provenance_or_valid_symbols(self):
        report = validate_manifest({"universe_name": "Undated"})
        self.assertEqual(report["status"], "invalid")
        self.assertIn("symbols must include at least one valid ticker", report["errors"])
        self.assertTrue(any("missing required fields" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
