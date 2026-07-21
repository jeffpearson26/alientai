from __future__ import annotations

import traceback
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from alpha_vantage_http import (
    AlphaVantageRequestError,
    get_alpha_vantage_response,
    redact_sensitive_text,
)


SECRET = "never-print-this-alpha-vantage-key"


class _FailedResponse:
    status_code = 503

    def raise_for_status(self):
        raise requests.HTTPError(
            f"503 Server Error for url: https://example.invalid/query?apikey={SECRET}"
        )


class AlphaVantageHTTPTests(unittest.TestCase):
    def test_http_status_traceback_cannot_contain_key_or_credential_url(self):
        with patch("alpha_vantage_http.requests.get", return_value=_FailedResponse()):
            try:
                get_alpha_vantage_response(
                    {"function": "HISTORICAL_OPTIONS", "symbol": "A"},
                    SECRET,
                    timeout=1,
                )
            except AlphaVantageRequestError as exc:
                rendered = traceback.format_exc()
                self.assertIn("HTTP 503", str(exc))
            else:
                self.fail("Expected a credential-safe AlphaVantageRequestError")
        self.assertNotIn(SECRET, rendered)
        self.assertNotIn("apikey=", rendered.casefold())

    def test_connection_error_traceback_cannot_contain_key(self):
        unsafe = requests.ConnectionError(
            f"connection failed for https://example.invalid/query?apikey={SECRET}"
        )
        with patch("alpha_vantage_http.requests.get", side_effect=unsafe):
            try:
                get_alpha_vantage_response(
                    {"function": "EARNINGS", "symbol": "A"},
                    SECRET,
                    timeout=1,
                )
            except AlphaVantageRequestError:
                rendered = traceback.format_exc()
            else:
                self.fail("Expected a credential-safe AlphaVantageRequestError")
        self.assertNotIn(SECRET, rendered)
        self.assertNotIn("apikey=", rendered.casefold())

    def test_stored_error_redacts_explicit_and_unknown_query_credentials(self):
        value = (
            f"first={SECRET} "
            "https://example.invalid/query?apikey=another-secret&symbol=A"
        )
        rendered = redact_sensitive_text(value, SECRET)
        self.assertNotIn(SECRET, rendered)
        self.assertNotIn("another-secret", rendered)
        self.assertEqual(rendered.count("[REDACTED]"), 2)

    def test_collectors_do_not_bypass_shared_http_helper(self):
        root = Path(__file__).resolve().parent
        collectors = sorted(root.glob("download_alpha_vantage*.py"))
        self.assertGreaterEqual(len(collectors), 8)
        for path in collectors:
            source = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertNotIn("requests.get(", source)
                self.assertNotIn(".raise_for_status()", source)


if __name__ == "__main__":
    unittest.main()
