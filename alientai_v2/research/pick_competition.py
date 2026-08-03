from __future__ import annotations

"""Pure, non-executing rules for the AlienTAI prospective pick competition."""

import hashlib
import json
from datetime import date, datetime, time
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo


EASTERN = ZoneInfo("America/New_York")
SUBMISSION_DEADLINE_ET = time(9, 25)
MAXIMUM_DAILY_PICKS = 5
HORIZONS = ("20m", "60m", "2d", "5d", "10d", "20d")
ROUND_TRIP_COST_PCT = 0.25
STOP_LOSS_PCT = -5.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_universe(path: Path) -> tuple[str, ...]:
    values = tuple(
        line.strip().upper()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    if len(values) != 101:
        raise ValueError(f"competition universe must contain exactly 101 tickers, found {len(values)}")
    if len(set(values)) != len(values) or any(not value for value in values):
        raise ValueError("competition universe contains a blank or duplicate ticker")
    return values


def normalize_picks(picks: Iterable[str], universe: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(str(value or "").strip().upper() for value in picks)
    if len(normalized) > MAXIMUM_DAILY_PICKS:
        raise ValueError("a participant may submit at most five picks per market day")
    if any(not value for value in normalized):
        raise ValueError("blank tickers are not allowed")
    if len(set(normalized)) != len(normalized):
        raise ValueError("duplicate tickers are not allowed")
    invalid = sorted(set(normalized).difference(universe))
    if invalid:
        raise ValueError(f"ticker outside frozen 101-stock universe: {', '.join(invalid)}")
    return normalized


def validate_submission_time(decision_date: str, submitted_at: datetime) -> datetime:
    decision = date.fromisoformat(decision_date)
    if submitted_at.tzinfo is None:
        raise ValueError("submission timestamp must include a timezone")
    eastern = submitted_at.astimezone(EASTERN)
    if eastern.date() != decision:
        raise ValueError("submission timestamp must fall on the decision date in Eastern time")
    if eastern.time().replace(tzinfo=None) > SUBMISSION_DEADLINE_ET:
        raise ValueError("submission arrived after the frozen 09:25 ET deadline")
    return eastern


def competition_manifest(universe_file: Path) -> dict[str, Any]:
    universe = load_universe(universe_file)
    return {
        "status": "frozen",
        "research_only": True,
        "execution_enabled": False,
        "universe_size": len(universe),
        "universe_sha256": sha256(universe_file),
        "selection_days_per_round": 5,
        "minimum_daily_picks": 0,
        "maximum_daily_picks": MAXIMUM_DAILY_PICKS,
        "submission_deadline": "09:25 America/New_York",
        "entry_reference": "09:30 ET regular-session open",
        "horizons": list(HORIZONS),
        "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
        "fixed_stop_loss_pct": STOP_LOSS_PCT,
        "unmanaged_track": True,
        "stop_managed_track": True,
        "daily_basket_weighting": "equal weight across every submitted ticker",
        "abstention_rule": "zero picks creates an abstention, not a win or loss",
    }


def build_submission(
    participant: str,
    decision_date: str,
    picks: Iterable[str],
    universe: Sequence[str],
    submitted_at: datetime,
    round_id: str,
) -> dict[str, Any]:
    name = str(participant or "").strip()
    if not name:
        raise ValueError("participant is required")
    if not str(round_id or "").strip():
        raise ValueError("round_id is required")
    eastern = validate_submission_time(decision_date, submitted_at)
    normalized = normalize_picks(picks, universe)
    return {
        "round_id": str(round_id).strip(),
        "participant": name,
        "decision_date": decision_date,
        "submitted_at_utc": submitted_at.astimezone(ZoneInfo("UTC")).isoformat(),
        "submitted_at_et": eastern.isoformat(),
        "picks": list(normalized),
        "pick_count": len(normalized),
        "abstained": not normalized,
        "entry_reference": "09:30 ET regular-session open",
        "horizons": list(HORIZONS),
        "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
        "fixed_stop_loss_pct": STOP_LOSS_PCT,
        "status": "frozen_pending",
        "research_only": True,
        "execution_decision": "AVOID",
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def append_submission(path: Path, submission: Mapping[str, Any]) -> None:
    key = (
        str(submission["round_id"]),
        str(submission["participant"]).casefold(),
        str(submission["decision_date"]),
    )
    for row in read_jsonl(path):
        existing = (
            str(row.get("round_id")),
            str(row.get("participant") or "").casefold(),
            str(row.get("decision_date")),
        )
        if existing == key:
            raise ValueError("participant already has a frozen submission for this decision date")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(dict(submission), sort_keys=True) + "\n")


def parse_aware_timestamp(value: Any, field: str) -> datetime:
    text = str(value or "").strip().replace("Z", "+00:00")
    if not text:
        raise ValueError(f"{field} is required")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed


def post_cost_return_pct(
    entry_price: Any,
    exit_price: Any,
    cost_pct: float = ROUND_TRIP_COST_PCT,
) -> float:
    entry = float(entry_price)
    exit_value = float(exit_price)
    cost = float(cost_pct)
    if entry <= 0 or exit_value <= 0:
        raise ValueError("entry and exit prices must be positive")
    if cost < 0:
        raise ValueError("round-trip cost cannot be negative")
    return ((exit_value / entry) - 1.0) * 100.0 - cost


def evaluate_pick_outcomes(
    *,
    symbol: str,
    entry_price: Any,
    entry_at_utc: Any,
    horizon_observations: Mapping[str, Mapping[str, Any]],
    stop_exit: Mapping[str, Any] | None = None,
    cost_pct: float = ROUND_TRIP_COST_PCT,
) -> dict[str, Any]:
    """Score one pick from explicit, timestamped, point-in-time price facts."""

    ticker = str(symbol or "").strip().upper()
    if not ticker:
        raise ValueError("symbol is required")
    entry_time = parse_aware_timestamp(entry_at_utc, "entry_at_utc")
    entry = float(entry_price)
    if entry <= 0:
        raise ValueError("entry price must be positive")

    stop_time: datetime | None = None
    stop_price: float | None = None
    if stop_exit is not None:
        stop_time = parse_aware_timestamp(stop_exit.get("as_of_utc"), "stop_exit.as_of_utc")
        stop_price = float(stop_exit.get("price"))
        if stop_time <= entry_time:
            raise ValueError("stop exit must occur after entry")
        if stop_price <= 0:
            raise ValueError("stop exit price must be positive")

    outcomes: dict[str, Any] = {}
    for horizon in HORIZONS:
        observation = horizon_observations.get(horizon)
        if observation is None:
            outcomes[horizon] = {"status": "pending"}
            continue
        observed_at = parse_aware_timestamp(observation.get("as_of_utc"), f"{horizon}.as_of_utc")
        observed_price = float(observation.get("price"))
        if observed_at <= entry_time:
            raise ValueError(f"{horizon} observation must occur after entry")
        if observed_price <= 0:
            raise ValueError(f"{horizon} price must be positive")
        stop_applied = stop_time is not None and stop_time <= observed_at
        managed_exit = stop_price if stop_applied else observed_price
        outcomes[horizon] = {
            "status": "complete",
            "observed_at_utc": observed_at.isoformat(),
            "unmanaged_exit_price": observed_price,
            "unmanaged_net_return_pct": post_cost_return_pct(entry, observed_price, cost_pct),
            "stop_managed_exit_price": managed_exit,
            "stop_managed_net_return_pct": post_cost_return_pct(entry, managed_exit, cost_pct),
            "stop_applied": stop_applied,
            "stop_exit_at_utc": stop_time.isoformat() if stop_applied else None,
        }

    return {
        "symbol": ticker,
        "entry_price": entry,
        "entry_at_utc": entry_time.isoformat(),
        "round_trip_cost_pct": float(cost_pct),
        "outcomes": outcomes,
        "research_only": True,
        "execution_decision": "AVOID",
    }


def summarize_returns(values: Iterable[Any]) -> dict[str, Any]:
    returns = [float(value) for value in values]
    if not returns:
        return {
            "sample_size": 0,
            "mean_return_pct": None,
            "median_return_pct": None,
            "win_rate_pct": None,
            "worst_return_pct": None,
            "best_return_pct": None,
        }
    return {
        "sample_size": len(returns),
        "mean_return_pct": sum(returns) / len(returns),
        "median_return_pct": median(returns),
        "win_rate_pct": sum(value > 0 for value in returns) / len(returns) * 100.0,
        "worst_return_pct": min(returns),
        "best_return_pct": max(returns),
    }
