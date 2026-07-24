import gzip
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from download_alpha_vantage_daily_research_fallback import collect, payload_symbols


class AlphaVantageDailyFallbackTests(unittest.TestCase):
    def test_payload_requires_research_only_and_deduplicates_symbols(self):
        payload = {"research_only": True, "execution_enabled": False, "candidates": [{"symbol": "abc"}, {"symbol": "ABC"}]}
        self.assertEqual(payload_symbols(payload), ["ABC"])
        with self.assertRaises(ValueError):
            payload_symbols({"research_only": True, "execution_enabled": True, "candidates": []})

    def test_collect_archives_source_separated_raw_response(self):
        with TemporaryDirectory() as directory:
            result = collect(["ABC"], Path(directory), "secret", lambda symbol, key: b'{"Time Series (Daily)": {}}')
            path = Path(result["files"][0]["path"])
            self.assertTrue(path.exists())
            with gzip.open(path, "rb") as handle:
                self.assertEqual(json.loads(handle.read()), {"Time Series (Daily)": {}})
            self.assertFalse(result["execution_enabled"])


if __name__ == "__main__":
    unittest.main()
