from __future__ import annotations

"""Point-in-time, conservative fills for exact historical multi-leg trades."""

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class OptionLeg:
    contract_id: str
    side: str  # "long" or "short"
    quantity: int = 1


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("option snapshot timestamps must be timezone-aware")
    return parsed


def _contracts(snapshot: Mapping[str, Any], name: str) -> dict[str, Mapping[str, Any]]:
    rows = snapshot.get("contracts")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{name} snapshot contains no contracts")
    output: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        contract_id = str(row.get("contractID") or "")
        if not contract_id or contract_id in output:
            raise ValueError(f"{name} snapshot has invalid contract identity")
        output[contract_id] = row
    return output


def _quote(row: Mapping[str, Any], field: str) -> float:
    try:
        value = float(row.get(field))
    except (TypeError, ValueError):
        raise ValueError(f"invalid option {field}") from None
    if not isfinite(value) or value < 0:
        raise ValueError(f"invalid option {field}")
    return value


def compile_exact_trade(
    *,
    legs: Sequence[OptionLeg],
    selection_snapshot: Mapping[str, Any],
    selected_at_utc: str,
    entry_snapshot: Mapping[str, Any],
    exit_snapshot: Mapping[str, Any],
    maximum_risk_dollars: float,
    fee_per_contract_per_side: float = 0.65,
) -> dict[str, Any]:
    """Require selection before entry and cross every quoted spread.

    Contract identities are frozen from a prior observable snapshot. Entry and
    exit use later exact snapshots, preventing same-snapshot selection/fill
    lookahead.
    """
    if not legs:
        raise ValueError("at least one option leg is required")
    if not isfinite(maximum_risk_dollars) or maximum_risk_dollars <= 0:
        raise ValueError("maximum risk must be positive")
    if fee_per_contract_per_side < 0:
        raise ValueError("option fee cannot be negative")
    selection_time = _time(str(selection_snapshot.get("available_at_utc") or ""))
    decision_time = _time(selected_at_utc)
    entry_time = _time(str(entry_snapshot.get("available_at_utc") or ""))
    exit_time = _time(str(exit_snapshot.get("available_at_utc") or ""))
    if not selection_time <= decision_time < entry_time < exit_time:
        raise ValueError(
            "option timing must be selection-available <= decision < entry < exit"
        )
    selection = _contracts(selection_snapshot, "selection")
    entry = _contracts(entry_snapshot, "entry")
    exit_ = _contracts(exit_snapshot, "exit")
    identities = [leg.contract_id for leg in legs]
    if len(set(identities)) != len(identities):
        raise ValueError("duplicate contract leg")
    if any(leg.side not in {"long", "short"} or leg.quantity < 1 for leg in legs):
        raise ValueError("invalid option leg side or quantity")
    missing = [
        contract_id for contract_id in identities
        if contract_id not in selection or contract_id not in entry
        or contract_id not in exit_
    ]
    if missing:
        raise ValueError(f"exact option contracts missing across snapshots: {missing}")

    entry_cash, exit_cash, fills = 0.0, 0.0, []
    contracts_traded = 0
    for leg in legs:
        entry_bid, entry_ask = _quote(entry[leg.contract_id], "bid"), _quote(entry[leg.contract_id], "ask")
        exit_bid, exit_ask = _quote(exit_[leg.contract_id], "bid"), _quote(exit_[leg.contract_id], "ask")
        if entry_ask < entry_bid or exit_ask < exit_bid:
            raise ValueError("crossed or malformed option quote")
        if leg.side == "long":
            entry_fill, exit_fill = entry_ask, exit_bid
            entry_cash -= entry_fill * leg.quantity
            exit_cash += exit_fill * leg.quantity
        else:
            entry_fill, exit_fill = entry_bid, exit_ask
            if entry_fill <= 0:
                raise ValueError("short option leg has no executable entry bid")
            entry_cash += entry_fill * leg.quantity
            exit_cash -= exit_fill * leg.quantity
        contracts_traded += leg.quantity
        fills.append({
            "contract_id": leg.contract_id, "side": leg.side,
            "quantity": leg.quantity, "entry_fill": entry_fill,
            "exit_fill": exit_fill,
        })
    gross_dollars = (entry_cash + exit_cash) * 100.0
    fees = contracts_traded * 2 * fee_per_contract_per_side
    net_dollars = gross_dollars - fees
    return {
        "status": "compiled",
        "research_only": True,
        "execution_enabled": False,
        "selection_available_at_utc": selection_time.isoformat(),
        "selected_at_utc": decision_time.isoformat(),
        "entry_available_at_utc": entry_time.isoformat(),
        "exit_available_at_utc": exit_time.isoformat(),
        "fills": fills,
        "gross_pnl_dollars": round(gross_dollars, 6),
        "fees_dollars": round(fees, 6),
        "net_pnl_dollars": round(net_dollars, 6),
        "maximum_risk_dollars": round(maximum_risk_dollars, 6),
        "net_return_on_risk_pct": round(net_dollars / maximum_risk_dollars * 100.0, 6),
    }
