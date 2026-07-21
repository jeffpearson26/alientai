from __future__ import annotations

"""Evaluate lead-lag hypotheses on a final held-out period after estimated costs.

This is a research-only, single-pair diagnostic. It does not aggregate candidates
into a portfolio and cannot create orders or enable trading.
"""

import argparse
import json
import math
from pathlib import Path
from typing import Any, Mapping

from discover_lead_lag_candidates import read_returns


DEFAULT_THRESHOLDS = (0.0, 0.25, 0.5, 1.0, 1.5)


def read_bars(path: Path) -> dict[str, dict[str, dict[str, float]]]:
    output: dict[str, dict[str, dict[str, float]]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            symbol, date = str(row.get("symbol") or "").upper(), str(row.get("date") or "")
            try:
                opening, close = float(row["open"]), float(row["close"])
            except (KeyError, TypeError, ValueError):
                continue
            if symbol and len(date) == 10 and opening > 0 and close > 0:
                output.setdefault(symbol, {})[date] = {"open": opening, "close": close}
    return output


def candidate_records(
    candidate: Mapping[str, Any],
    returns: Mapping[str, Mapping[str, float]],
    bars: Mapping[str, Mapping[str, Mapping[str, float]]],
    sector_returns: Mapping[str, Mapping[str, float]],
    sector_map: Mapping[str, str],
) -> list[dict[str, float | str]]:
    source_symbol, target_symbol = str(candidate["source_symbol"]), str(candidate["target_symbol"])
    source_sector, target_sector = sector_map.get(source_symbol), sector_map.get(target_symbol)
    if not source_sector or not target_sector:
        return []
    source, target = returns.get(source_symbol, {}), returns.get(target_symbol, {})
    source_benchmark, target_benchmark = sector_returns.get(source_sector, {}), sector_returns.get(target_sector, {})
    sessions = sorted(set(source) & set(target) & set(source_benchmark) & set(target_benchmark))
    lag = int(candidate["lag_sessions"])
    records: list[dict[str, float | str]] = []
    for index in range(len(sessions) - lag):
        source_date, target_date = sessions[index], sessions[index + lag]
        bar = bars.get(target_symbol, {}).get(target_date)
        if not bar:
            continue
        source_residual = source[source_date] - source_benchmark[source_date]
        target_residual = target[target_date] - target_benchmark[target_date]
        intraday_return = ((bar["close"] / bar["open"]) - 1.0) * 100.0
        records.append({
            "source_date": source_date,
            "target_date": target_date,
            "source_residual_pct": source_residual,
            "target_residual_pct": target_residual,
            "target_open_to_close_pct": intraday_return,
        })
    return records


def net_metrics(records: list[Mapping[str, float | str]], direction: str, threshold: float, cost_pct: float) -> dict[str, float | int]:
    selected = [row for row in records if abs(float(row["source_residual_pct"])) >= threshold]
    values = []
    sign = 1.0 if direction == "same" else -1.0
    for row in selected:
        prediction = sign * (1.0 if float(row["source_residual_pct"]) >= 0 else -1.0)
        values.append(prediction * float(row["target_open_to_close_pct"]) - cost_pct)
    if not values:
        return {"signals": 0, "mean_net_return_pct": 0.0, "median_net_return_pct": 0.0, "win_rate_after_cost_pct": 0.0}
    ordered = sorted(values)
    middle = len(ordered) // 2
    median = ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2
    return {
        "signals": len(values),
        "mean_net_return_pct": round(sum(values) / len(values), 6),
        "median_net_return_pct": round(median, 6),
        "win_rate_after_cost_pct": round(100.0 * sum(value > 0 for value in values) / len(values), 4),
    }


def choose_pretest_threshold(records: list[Mapping[str, float | str]], direction: str, cost_pct: float, minimum_signals: int) -> tuple[float, dict[str, float | int]] | None:
    eligible = []
    for threshold in DEFAULT_THRESHOLDS:
        metrics = net_metrics(records, direction, threshold, cost_pct)
        if int(metrics["signals"]) >= minimum_signals:
            eligible.append((threshold, metrics))
    if not eligible:
        return None
    return max(eligible, key=lambda item: (float(item[1]["mean_net_return_pct"]), float(item[1]["median_net_return_pct"]), -item[0]))


def evaluate_candidates(
    candidates: list[Mapping[str, Any]],
    returns: Mapping[str, Mapping[str, float]],
    bars: Mapping[str, Mapping[str, Mapping[str, float]]],
    sector_returns: Mapping[str, Mapping[str, float]],
    sector_map: Mapping[str, str],
    *, cost_pct: float, minimum_pretest_signals: int, minimum_test_signals: int,
) -> list[dict[str, Any]]:
    output = []
    for candidate in candidates:
        records = candidate_records(candidate, returns, bars, sector_returns, sector_map)
        cut = (len(records) * 2) // 3
        picked = choose_pretest_threshold(records[:cut], str(candidate["direction"]), cost_pct, minimum_pretest_signals)
        if picked is None:
            continue
        threshold, pretest = picked
        test = net_metrics(records[cut:], str(candidate["direction"]), threshold, cost_pct)
        if int(test["signals"]) < minimum_test_signals:
            continue
        output.append({
            "source_symbol": candidate["source_symbol"], "target_symbol": candidate["target_symbol"],
            "lag_sessions": candidate["lag_sessions"], "direction": candidate["direction"],
            "selected_pretest_threshold_pct": threshold,
            "pretest": pretest, "held_out_test": test,
        })
    return sorted(output, key=lambda row: (-float(row["held_out_test"]["mean_net_return_pct"]), -int(row["held_out_test"]["signals"])))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--returns", type=Path, required=True)
    parser.add_argument("--sector-returns", type=Path, required=True)
    parser.add_argument("--sector-map", type=Path, required=True)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    parser.add_argument("--minimum-pretest-signals", type=int, default=100)
    parser.add_argument("--minimum-test-signals", type=int, default=50)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    candidates = json.loads(args.candidates.read_text(encoding="utf-8")).get("candidates", [])
    sector_map = {str(key).upper(): str(value).upper() for key, value in json.loads(args.sector_map.read_text(encoding="utf-8")).items()}
    rows = evaluate_candidates(candidates, read_returns(args.returns), read_bars(args.returns), read_returns(args.sector_returns), sector_map, cost_pct=args.round_trip_cost_pct, minimum_pretest_signals=args.minimum_pretest_signals, minimum_test_signals=args.minimum_test_signals)
    payload = {"status": "complete", "research_only": True, "execution_assumption": "Source return is known after its close; enter the target at a later session open and exit at that target close. No same-bar foresight is assumed.", "round_trip_cost_pct": args.round_trip_cost_pct, "candidate_count": len(rows), "candidates": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "candidate_count": len(rows), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
