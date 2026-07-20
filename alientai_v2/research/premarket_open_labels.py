from __future__ import annotations

"""Construct tradable post-premarket labels from five-minute regular-session bars."""

from datetime import datetime, time
from typing import Any, Dict, Iterable, Mapping, Optional

from alientai_v2.features.premarket_features import number, parse_timestamp, pct_change


ENTRY_BAR_TIME = time(9, 30)
EXIT_CUTOFF = time(16, 0)


def selected_close(
    rows: Iterable[Mapping[str, Any]], day: str, *, first: bool,
) -> tuple[Optional[float], Optional[str]]:
    target = datetime.strptime(day, "%Y-%m-%d").date()
    candidates = []
    for row in rows:
        stamp = parse_timestamp(row.get("timestamp"))
        close = number(row.get("close"))
        if stamp is None or close is None or stamp.date() != target:
            continue
        if ENTRY_BAR_TIME <= stamp.time() <= EXIT_CUTOFF:
            candidates.append((stamp, close))
    if not candidates:
        return None, None
    stamp, close = sorted(candidates, key=lambda item: item[0])[0 if first else -1]
    return close, stamp.strftime("%Y-%m-%d %H:%M:%S")


def build_open_entry_label(
    entry_rows: Iterable[Mapping[str, Any]], exit_rows: Iterable[Mapping[str, Any]],
    market_date: str, future_market_date: str, exceptional_threshold_pct: float = 10.0,
) -> Dict[str, Any]:
    entry_price, entry_bar = selected_close(entry_rows, market_date, first=True)
    exit_price, exit_bar = selected_close(exit_rows, future_market_date, first=False)
    forward_return = pct_change(exit_price, entry_price)
    return {
        "premarket_label_available": forward_return is not None,
        "premarket_entry_rule": "first_regular_5min_bar_close",
        "premarket_entry_price": entry_price,
        "premarket_entry_bar_et": entry_bar,
        "premarket_exit_price": exit_price,
        "premarket_exit_bar_et": exit_bar,
        "premarket_forward_return_5d_pct": forward_return,
        "premarket_exceptional_threshold_pct": exceptional_threshold_pct,
        "premarket_label_exceptional_winner": (
            bool(forward_return >= exceptional_threshold_pct) if forward_return is not None else None
        ),
    }
