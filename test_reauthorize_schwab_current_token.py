import unittest

from reauthorize_schwab_current_token import authorization_url, redirect_code


class SchwabCurrentTokenReauthorizationTests(unittest.TestCase):
    def test_authorization_url_contains_callback_and_state(self):
        url = authorization_url("client", "https://example.test/callback", "state-1")
        self.assertIn("client_id=client", url)
        self.assertIn("state=state-1", url)

    def test_redirect_code_requires_matching_state(self):
        self.assertEqual(redirect_code("https://example.test/callback?code=abc&state=state-1", "state-1"), "abc")
        with self.assertRaises(ValueError):
            redirect_code("https://example.test/callback?code=abc&state=wrong", "state-1")


if __name__ == "__main__":
    unittest.main()
