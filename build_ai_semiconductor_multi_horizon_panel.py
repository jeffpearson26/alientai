from __future__ import annotations

"""Add point-in-time 1/5/20-session labels to the saved catalyst panel."""

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


HORIZONS = (1, 5, 20)
ROUND_TRIP_COST_PCT = 0.25


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_daily(path: Path) -> list[tuple[str, float, float]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    series = payload.get("Time Series (Daily)") or {}
    return sorted(
        (day, float(values["1. open"]), float(values["4. close"]))
        for day, values in series.items()
    )


def horizon_labels(
    daily: Sequence[tuple[str, float, float]],
    market_date: str,
    horizons: Iterable[int] = HORIZONS,
    cost_pct: float = ROUND_TRIP_COST_PCT,
) -> dict[str, Any]:
    """Use next-session open and each fixed later-session close."""
    index_by_date = {row[0]: index for index, row in enumerate(daily)}
    if market_date not in index_by_date:
        return {}
    index = index_by_date[market_date]
    if index + 1 >= len(daily):
        return {}
    entry_date, entry_open, _ = daily[index + 1]
    result: dict[str, Any] = {
        "label_entry_market_date": entry_date,
        "label_entry_next_open": entry_open,
    }
    for horizon in horizons:
        if horizon <= 0:
            raise ValueError("horizons must be positive")
        target_index = index + horizon
        prefix = f"label_{horizon}d"
        if target_index >= len(daily):
            result.update({
                f"{prefix}_available": False,
                f"{prefix}_exit_market_date": None,
                f"{prefix}_exit_close": None,
                f"{prefix}_gross_return_pct": None,
                f"{prefix}_net_return_pct": None,
            })
            continue
        exit_date, _, exit_close = daily[target_index]
        gross = (exit_close / entry_open - 1.0) * 100.0
        result.update({
            f"{prefix}_available": True,
            f"{prefix}_exit_market_date": exit_date,
            f"{prefix}_exit_close": exit_close,
            f"{prefix}_gross_return_pct": gross,
            f"{prefix}_net_return_pct": gross - cost_pct,
        })
    return result


def build_panel(
    rows: Iterable[Mapping[str, Any]],
    daily_by_symbol: Mapping[str, Sequence[tuple[str, float, float]]],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for source in rows:
        symbol = str(source.get("symbol") or "").upper()
        market_date = str(source.get("market_date") or "")[:10]
        key = (symbol, market_date)
        if not all(key) or key in seen:
            raise ValueError(f"invalid or duplicate panel key: {key}")
        seen.add(key)
        if symbol not in daily_by_symbol:
            raise ValueError(f"missing daily history for {symbol}")
        labels = horizon_labels(daily_by_symbol[symbol], market_date)
        if not labels:
            continue
        row = dict(source)
        row.update(labels)
        row.update({
            "multi_horizon_label_contract":
                "decision after close; next-session open entry; fixed session close exits",
            "multi_horizon_round_trip_cost_pct": ROUND_TRIP_COST_PCT,
            "research_only": True,
            "execution_enabled": False,
        })
        output.append(row)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--daily-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rows = read_jsonl(args.input)
    symbols = sorted({str(row["symbol"]).upper() for row in rows})
    daily = {
        symbol: load_daily(args.daily_root / f"{symbol}_daily.json")
        for symbol in symbols
    }
    output = build_panel(rows, daily)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in output),
        encoding="utf-8",
    )
    coverage = {
        str(horizon): sum(bool(row.get(f"label_{horizon}d_available")) for row in output)
        for horizon in HORIZONS
    }
    print(json.dumps({
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "rows": len(output),
        "symbols": len(symbols),
        "dates": len({row["market_date"] for row in output}),
        "coverage": coverage,
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
