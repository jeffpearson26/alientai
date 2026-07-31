from __future__ import annotations

"""Pure, deterministic contract selection and conservative shadow fills."""

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping, Sequence


class OptionChainError(ValueError):
    pass


@dataclass(frozen=True)
class CallSelectionPolicy:
    minimum_dte: int = 14
    maximum_dte: int = 45
    minimum_delta: float = 0.60
    maximum_delta: float = 0.75
    target_delta: float = 0.675
    minimum_open_interest: int = 100
    maximum_spread_pct: float = 10.0


def _number(row: Mapping[str, Any], name: str) -> float:
    try:
        return float(row.get(name))
    except (TypeError, ValueError):
        raise OptionChainError(f"invalid {name}") from None


def validate_realtime_payload(payload: Mapping[str, Any], expected_symbol: str) -> list[dict[str, Any]]:
    message = str(payload.get("message") or "")
    if "ARTIFICIAL" in message.upper() or "SAMPLE DATA" in message.upper():
        raise OptionChainError("provider returned artificial sample data")
    rows = payload.get("data")
    if not isinstance(rows, list) or not rows:
        raise OptionChainError("provider returned no option contracts")
    symbol = expected_symbol.upper()
    validated = []
    for raw in rows:
        row = dict(raw)
        if str(row.get("symbol") or "").upper() != symbol:
            raise OptionChainError("option chain contains an unexpected symbol")
        for field in ("contractID", "date", "expiration", "type", "strike", "bid", "ask"):
            if row.get(field) in (None, ""):
                raise OptionChainError(f"option chain is missing {field}")
        validated.append(row)
    return validated


def select_call(
    rows: Sequence[Mapping[str, Any]],
    market_date: str,
    policy: CallSelectionPolicy = CallSelectionPolicy(),
) -> dict[str, Any]:
    decision = date.fromisoformat(market_date)
    eligible = []
    for raw in rows:
        row = dict(raw)
        if str(row.get("type") or "").lower() != "call":
            continue
        try:
            expiration = date.fromisoformat(str(row["expiration"]))
            dte = (expiration - decision).days
            bid, ask = _number(row, "bid"), _number(row, "ask")
            delta = _number(row, "delta")
            open_interest = int(_number(row, "open_interest"))
        except (KeyError, OptionChainError, ValueError):
            continue
        if bid <= 0 or ask <= bid:
            continue
        spread_pct = (ask - bid) / ((ask + bid) / 2.0) * 100.0
        if not (
            policy.minimum_dte <= dte <= policy.maximum_dte
            and policy.minimum_delta <= delta <= policy.maximum_delta
            and open_interest >= policy.minimum_open_interest
            and spread_pct <= policy.maximum_spread_pct
        ):
            continue
        row.update({
            "dte": dte,
            "spread_pct": spread_pct,
            "delta": delta,
            "bid": bid,
            "ask": ask,
            "open_interest": open_interest,
        })
        eligible.append(row)
    if not eligible:
        raise OptionChainError("no call satisfies the frozen liquidity, DTE, delta, and spread policy")
    return min(
        eligible,
        key=lambda row: (
            row["spread_pct"],
            abs(row["delta"] - policy.target_delta),
            -row["open_interest"],
            str(row["expiration"]),
            _number(row, "strike"),
            str(row["contractID"]),
        ),
    )


def conservative_option_return_pct(entry_ask: float, exit_bid: float) -> float:
    if entry_ask <= 0 or exit_bid < 0:
        raise OptionChainError("invalid conservative option fill")
    return (exit_bid / entry_ask - 1.0) * 100.0
