"""Audit timing and arithmetic for leakage-safe matched premarket labels."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping


FIRST_REGULAR_BAR_TIMESTAMP = "09:30:00"
# The stored source labels use close timestamps, so the final regular-session
# close is represented as 16:00 rather than the 15:55 bar opening.
LAST_REGULAR_BAR_TIMESTAMP = "16:00:00"


def key(row: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return tuple(str(row.get(name) or "") for name in ("study_event_id", "symbol", "market_date", "study_role"))


def audit(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(rows)
    duplicates = sum(count - 1 for count in Counter(key(row) for row in rows).values() if count > 1)
    available = [row for row in rows if row.get("premarket_label_available")]
    failures = {"duplicate_keys": duplicates, "invalid_dates": 0, "invalid_entry_timestamp": 0,
                "invalid_exit_timestamp": 0, "invalid_prices": 0, "return_mismatch": 0}
    for row in available:
        market_date, future_date = str(row.get("market_date") or ""), str(row.get("future_market_date") or "")
        entry, exit_ = str(row.get("premarket_entry_bar_et") or ""), str(row.get("premarket_exit_bar_et") or "")
        if not market_date or not future_date or future_date <= market_date:
            failures["invalid_dates"] += 1
        if entry != f"{market_date} {FIRST_REGULAR_BAR_TIMESTAMP}":
            failures["invalid_entry_timestamp"] += 1
        if exit_ != f"{future_date} {LAST_REGULAR_BAR_TIMESTAMP}":
            failures["invalid_exit_timestamp"] += 1
        try:
            entry_price, exit_price = float(row["premarket_entry_price"]), float(row["premarket_exit_price"])
            actual = float(row["premarket_forward_return_5d_pct"])
            expected = (exit_price / entry_price - 1.0) * 100.0
            if entry_price <= 0 or exit_price <= 0:
                failures["invalid_prices"] += 1
            elif abs(actual - expected) > 1e-6:
                failures["return_mismatch"] += 1
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            failures["invalid_prices"] += 1
    return {"status": "complete", "research_only": True, "execution_enabled": False,
            "rows": len(rows), "available_labels": len(available), "failures": failures,
            "passes": not any(failures.values())}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.labels.open(encoding="utf-8") as handle:
        result = audit(json.loads(line) for line in handle if line.strip())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
