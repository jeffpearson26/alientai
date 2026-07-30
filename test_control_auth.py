import unittest

from alientai_v2.control_auth import control_request_allowed, is_control_request


class ControlAuthTests(unittest.TestCase):
    def test_local_control_is_allowed_without_token(self):
        self.assertTrue(control_request_allowed("127.0.0.1", "", ""))
        self.assertTrue(control_request_allowed("::1", "", ""))

    def test_remote_control_fails_closed_without_configured_token(self):
        self.assertFalse(control_request_allowed("192.168.1.10", "", ""))

    def test_remote_control_requires_matching_token(self):
        self.assertFalse(control_request_allowed("192.168.1.10", "wrong", "secret"))
        self.assertTrue(control_request_allowed("192.168.1.10", "secret", "secret"))

    def test_only_mutating_v2_requests_are_control_requests(self):
        self.assertTrue(is_control_request("POST", "/v2/start"))
        self.assertTrue(is_control_request("DELETE", "/v2/example"))
        self.assertFalse(is_control_request("GET", "/v2/status"))
        self.assertFalse(is_control_request("POST", "/public"))


if __name__ == "__main__":
    unittest.main()
