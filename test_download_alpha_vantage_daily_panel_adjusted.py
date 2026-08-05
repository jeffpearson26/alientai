from __future__ import annotations

import download_alpha_vantage_daily_panel as module


class Response:
    def json(self) -> dict:
        return {"Time Series (Daily)": {"2026-08-04": {}}}


def test_fetch_propagates_adjusted_daily_function(monkeypatch) -> None:
    captured = {}

    def fake_get(parameters, api_key, timeout):
        captured.update({
            "parameters": parameters,
            "api_key": api_key,
            "timeout": timeout,
        })
        return Response()

    monkeypatch.setattr(module, "get_alpha_vantage_response", fake_get)
    result = module.fetch(
        "QQQ",
        "secret",
        outputsize="full",
        function="TIME_SERIES_DAILY_ADJUSTED",
    )
    assert "Time Series (Daily)" in result
    assert captured["parameters"] == {
        "function": "TIME_SERIES_DAILY_ADJUSTED",
        "symbol": "QQQ",
        "outputsize": "full",
    }
    assert captured["api_key"] == "secret"
    assert captured["timeout"] == 90
