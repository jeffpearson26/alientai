"""Authorization policy for state-changing AlienTAI HTTP endpoints."""
from __future__ import annotations

import hmac


CONTROL_HEADER = "X-AlienTAI-Control-Token"
LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}


def is_control_request(method: str, path: str) -> bool:
    if str(method).upper() not in {"POST", "PUT", "PATCH", "DELETE"}:
        return False
    normalized = "/" + str(path or "").lstrip("/")
    return normalized.startswith("/v2/")


def control_request_allowed(client_host: str, supplied_token: str, configured_token: str) -> bool:
    if str(client_host or "").strip().lower() in LOCAL_HOSTS:
        return True
    expected = str(configured_token or "").strip()
    supplied = str(supplied_token or "").strip()
    return bool(expected and supplied and hmac.compare_digest(supplied, expected))
