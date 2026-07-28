import json
import tempfile
import unittest
from pathlib import Path

from filter_jsonl_symbol_universe import filter_rows


class FilterJsonlSymbolUniverseTests(unittest.TestCase):
    def test_filters_and_reports_missing_symbols(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.jsonl"
            output = Path(directory) / "output.jsonl"
            source.write_text(
                "\n".join(json.dumps({"symbol": symbol}) for symbol in ("AAA", "BBB")) + "\n",
                encoding="utf-8",
            )
            result = filter_rows(source, output, {"AAA", "CCC"})
            rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([{"symbol": "AAA"}], rows)
        self.assertEqual(["CCC"], result["missing_symbols"])


if __name__ == "__main__":
    unittest.main()
