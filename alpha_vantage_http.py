from __future__ import annotations

"""Credential-safe HTTP helpers shared by Alpha Vantage collectors."""

import re
from typing import Any, Mapping

import requests


ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"
_SENSITIVE_QUERY_VALUE = re.compile(
    r"(?i)((?:api[_-]?key|access[_-]?token|token)\s*=\s*)[^&\s]+"
)


class AlphaVantageRequestError(Exception):
    """An Alpha Vantage transport failure with sensitive request details removed."""


def redact_sensitive_text(value: Any, *secrets: str, limit: int = 1000) -> str:
    """Return bounded error text with explicit secrets and query credentials removed."""
    text = str(value or "Alpha Vantage request failed")
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    text = _SENSITIVE_QUERY_VALUE.sub(r"\1[REDACTED]", text)
    return text[:limit]


def get_alpha_vantage_response(
    params: Mapping[str, Any], api_key: str, *, timeout: float
) -> requests.Response:
    """Issue one request without allowing credential-bearing URLs into tracebacks.

    ``requests`` includes the prepared URL in several transport exceptions. Because
    Alpha Vantage authenticates in the query string, propagating those exceptions can
    print the API key in redirected stderr. Translate every Requests exception into a
    bounded, non-chained error that contains only the failure category and status.
    """
    request_params = dict(params)
    request_params["apikey"] = api_key
    response = None
    try:
        response = requests.get(
            ALPHA_VANTAGE_URL,
            params=request_params,
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        error_response = getattr(exc, "response", None)
        status = getattr(error_response, "status_code", None)
        if status is None and response is not None:
            status = getattr(response, "status_code", None)
        category = f"HTTP {status}" if status is not None else type(exc).__name__
        raise AlphaVantageRequestError(
            f"Alpha Vantage request failed ({category}); sensitive request details redacted."
        ) from None
    return response
