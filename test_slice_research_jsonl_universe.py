import unittest

from slice_research_jsonl_universe import slice_rows


class ResearchUniverseSliceTests(unittest.TestCase):
    def test_keeps_only_requested_symbols(self):
        rows = [{"symbol": "NVDA", "x": 1}, {"symbol": "AAPL", "x": 2}, {"symbol": "amd", "x": 3}]
        self.assertEqual(slice_rows(rows, {"AMD", "NVDA"}), [rows[0], rows[2]])

    def test_missing_symbol_or_empty_result_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "missing symbol"):
            slice_rows([{"x": 1}], {"NVDA"})
        with self.assertRaisesRegex(ValueError, "no source rows"):
            slice_rows([{"symbol": "AAPL"}], {"NVDA"})


if __name__ == "__main__":
    unittest.main()
