from __future__ import annotations

"""Append-only, non-executing prospective journal for frozen Nasdaq models."""

import argparse
import csv
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from alientai_v2.features.technical_snapshot import build_technical_snapshot
from alientai_v2.research.score_calibration import (
    calibrated_probability,
    percentile_rank,
)
from evaluate_context_portfolio import file_sha256


def load_candles(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return sorted(csv.DictReader(handle), key=lambda row: row["date"])


def symbols(path: Path) -> list[str]:
    return [
        line.strip().upper() for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def latest_common_date(
    daily_dir: Path, symbol_list: Sequence[str], benchmark_symbol: str,
) -> str:
    common: set[str] | None = None
    for symbol in [*symbol_list, benchmark_symbol]:
        path = daily_dir / f"{symbol}_schwab_1d_max.csv"
        if not path.exists():
            raise ValueError(f"missing daily history: {path}")
        dates = {row["date"] for row in load_candles(path)}
        common = dates if common is None else common & dates
    if not common:
        raise ValueError("no common market date across universe and benchmark")
    return max(common)


def validate_market_date_freshness(
    market_date: str, today: date, maximum_age_calendar_days: int,
) -> int:
    if maximum_age_calendar_days < 0:
        raise ValueError("maximum age must be nonnegative")
    age = (today - date.fromisoformat(market_date)).days
    if age < 0 or age > maximum_age_calendar_days:
        raise ValueError(
            f"market date {market_date} is {age} calendar days old; "
            f"maximum allowed is {maximum_age_calendar_days}"
        )
    return age


def schwab_session_date(stored_market_date: str) -> str:
    """Translate the legacy Pacific-local archive key to its UTC session date."""
    return (date.fromisoformat(stored_market_date) + timedelta(days=1)).isoformat()


def prospective_row(
    candles: Sequence[Mapping[str, Any]],
    symbol: str,
    market_date: str,
    benchmark: Sequence[Mapping[str, Any]] | None = None,
    benchmark_symbol: str | None = None,
) -> dict[str, Any]:
    by_date = {str(row["date"]): index for index, row in enumerate(candles)}
    index = by_date.get(market_date)
    if index is None or index < 59:
        raise ValueError(f"insufficient point-in-time history for {symbol}")
    row = {
        "symbol": symbol,
        "market_date": market_date,
        "entry_close": float(candles[index]["close"]),
        **build_technical_snapshot(list(candles[index - 59:index + 1])),
    }
    if benchmark is not None and benchmark_symbol:
        benchmark_by_date = {
            str(item["date"]): position for position, item in enumerate(benchmark)
        }
        benchmark_index = benchmark_by_date.get(market_date)
        if benchmark_index is None or benchmark_index < 60 or index < 60:
            raise ValueError("insufficient benchmark history")
        benchmark_close = float(benchmark[benchmark_index]["close"])
        row["benchmark_symbol"] = benchmark_symbol
        for lookback in (5, 20, 60):
            stock_return = (
                row["entry_close"] / float(candles[index - lookback]["close"]) - 1.0
            ) * 100.0
            benchmark_return = (
                benchmark_close / float(benchmark[benchmark_index - lookback]["close"])
                - 1.0
            ) * 100.0
            row[f"technical_benchmark_return_{lookback}d_pct"] = benchmark_return
            row[f"technical_relative_return_{lookback}d_pct"] = (
                stock_return - benchmark_return
            )
    return row


def select_candidates(
    rows: Sequence[Mapping[str, Any]],
    scores: Sequence[float],
    cutoff: float,
    maximum_candidates: int,
) -> list[dict[str, Any]]:
    if len(rows) != len(scores):
        raise ValueError("rows and scores must have equal length")
    if maximum_candidates < 1:
        raise ValueError("maximum_candidates must be positive")
    ranked = sorted(
        (
            {**row, "model_score": float(score)}
            for row, score in zip(rows, scores)
            if float(score) >= cutoff
        ),
        key=lambda row: (-row["model_score"], row["symbol"]),
    )
    all_scores = list(float(score) for score in scores)
    return [{
        **row,
        "confidence_rank_1_to_100": percentile_rank(row["model_score"], all_scores),
        "confidence_rank_definition": "same-day eligible-universe model-score percentile; not probability",
    } for row in ranked[:maximum_candidates]]


def append_unique(path: Path, rows: Sequence[Mapping[str, Any]]) -> int:
    existing = set()
    if path.exists():
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    row = json.loads(line)
                    existing.add((
                        row.get("model_id"), row.get("market_date"), row.get("symbol")
                    ))
    additions = [
        row for row in rows
        if (row.get("model_id"), row.get("market_date"), row.get("symbol")) not in existing
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for row in additions:
            handle.write(json.dumps(dict(row), sort_keys=True) + "\n")
    return len(additions)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--daily-dir", type=Path, required=True)
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--research-root", type=Path, required=True)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--market-date")
    parser.add_argument("--maximum-candidates", type=int, default=5)
    parser.add_argument("--maximum-market-age-calendar-days", type=int, default=3)
    args = parser.parse_args()

    symbol_list = symbols(args.symbols_file)
    benchmark_symbol = "QQQ"
    market_date = args.market_date or latest_common_date(
        args.daily_dir, symbol_list, benchmark_symbol
    )
    market_session_date = schwab_session_date(market_date)
    market_date_age = validate_market_date_freshness(
        market_session_date,
        datetime.now(timezone.utc).date(),
        args.maximum_market_age_calendar_days,
    )
    benchmark = load_candles(
        args.daily_dir / f"{benchmark_symbol}_schwab_1d_max.csv"
    )
    configurations = [
        {
            "model_id": "nasdaq100_complete_101_baseline_v1",
            "model": args.research_root / "nasdaq100_complete_clone/model_10pct/natural_technical_context_classifier.txt",
            "report": args.research_root / "nasdaq100_complete_clone/model_10pct/natural_technical_context_report.json",
            "score_cutoff": 0.20886314398519493,
            "qqq_relative": False,
        },
        {
            "model_id": "nasdaq100_complete_101_qqq_relative_v1",
            "model": args.research_root / "nasdaq100_relative_qqq/model_10pct/natural_technical_context_classifier.txt",
            "report": args.research_root / "nasdaq100_relative_qqq/model_10pct/natural_technical_context_report.json",
            "score_cutoff": 0.2246736047938044,
            "qqq_relative": True,
        },
    ]
    frozen_manifest = {
        "status": "frozen",
        "research_only": True,
        "execution_enabled": False,
        "target_horizon_sessions": 5,
        "maximum_candidates_per_model_per_day": args.maximum_candidates,
        "maximum_market_age_calendar_days": args.maximum_market_age_calendar_days,
        "models": [{
            "model_id": config["model_id"],
            "model_sha256": file_sha256(config["model"]),
            "training_report_sha256": file_sha256(config["report"]),
            "score_cutoff": config["score_cutoff"],
            "qqq_relative": config["qqq_relative"],
        } for config in configurations],
    }
    if args.manifest.exists():
        existing = json.loads(args.manifest.read_text(encoding="utf-8"))
        if existing != frozen_manifest:
            raise ValueError("existing frozen manifest does not match requested configuration")
    else:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            json.dumps(frozen_manifest, indent=2) + "\n", encoding="utf-8"
        )

    all_observations = []
    for config in configurations:
        report = json.loads(config["report"].read_text(encoding="utf-8"))
        rows = []
        for symbol in symbol_list:
            candles = load_candles(
                args.daily_dir / f"{symbol}_schwab_1d_max.csv"
            )
            rows.append(prospective_row(
                candles,
                symbol,
                market_date,
                benchmark if config["qqq_relative"] else None,
                benchmark_symbol if config["qqq_relative"] else None,
            ))
        features = report["feature_names"]
        matrix = np.asarray([
            [float(row.get(name) or 0.0) for name in features] for row in rows
        ], dtype=np.float32)
        model = lgb.Booster(model_file=str(config["model"]))
        scores = model.predict(matrix, num_iteration=model.best_iteration)
        selected = select_candidates(
            rows, scores, config["score_cutoff"], args.maximum_candidates
        )
        for row in selected:
            observation = {
                **row,
                "market_session_date": market_session_date,
                "model_id": config["model_id"],
                "model_sha256": file_sha256(config["model"]),
                "locked_score_cutoff": config["score_cutoff"],
                "target_horizon_sessions": 5,
                "status": "pending",
                "journaled_at_utc": datetime.now(timezone.utc).isoformat(),
                "research_only": True,
                "execution_decision": "AVOID",
            }
            all_observations.append(observation)
    additions = append_unique(args.journal, all_observations)
    print(json.dumps({
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "market_date": market_date,
        "market_session_date": market_session_date,
        "market_date_age_calendar_days": market_date_age,
        "eligible_universe": len(symbol_list),
        "observations_selected": len(all_observations),
        "observations_appended": additions,
        "by_model": {
            model_id: sum(row["model_id"] == model_id for row in all_observations)
            for model_id in sorted({row["model_id"] for row in all_observations})
        },
        "journal": str(args.journal),
        "manifest": str(args.manifest),
    }, indent=2))


if __name__ == "__main__":
    main()
