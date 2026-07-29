from __future__ import annotations

"""Score frozen Nasdaq models from an isolated Alpha Vantage daily panel.

This is a current source-shift diagnostic only. It cannot determine model
performance, update a Schwab prospective record, or create any order.
"""

import argparse
import json
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np

from build_alpha_vantage_daily_technical_panel import candles
from evaluate_context_portfolio import file_sha256
from evaluate_score_percentile_baskets import DEFAULT_PERCENTILE_EDGES, percentile_edges
from journal_nasdaq_challengers import prospective_row, symbols
from journal_nasdaq_score_baskets import CONFIGURATIONS, basket_for_score
from alientai_v2.research.score_calibration import percentile_rank


def safe_name(symbol: str) -> str:
    return symbol.replace("/", "-").replace(".", "-")


def score_snapshot(
    daily_dir: Path,
    symbols_file: Path,
    research_root: Path,
    market_date: str,
    percentile_edges_list: list[int],
) -> list[dict[str, Any]]:
    universe = symbols(symbols_file)
    benchmark = candles(daily_dir / "QQQ_daily.json")
    observations: list[dict[str, Any]] = []
    for config in CONFIGURATIONS:
        model_path = research_root / config["model_path"]
        report_path = research_root / config["report_path"]
        report = json.loads(report_path.read_text(encoding="utf-8"))
        rows = [
            prospective_row(
                candles(daily_dir / f"{safe_name(symbol)}_daily.json"),
                symbol,
                market_date,
                benchmark if config["qqq_relative"] else None,
                "QQQ" if config["qqq_relative"] else None,
            )
            for symbol in universe
        ]
        features = report["feature_names"]
        model = lgb.Booster(model_file=str(model_path))
        scores = [float(value) for value in model.predict(np.asarray([
            [float(row.get(name) or 0.0) for name in features] for row in rows
        ], dtype=np.float32), num_iteration=model.best_iteration)]
        validation_rows = [json.loads(line) for line in Path(report["input"]).read_text(encoding="utf-8").splitlines() if line.strip()]
        validation_rows = [row for row in validation_rows if report["split"]["validation_start"] <= row["market_date"] <= report["split"]["validation_end"]]
        validation_scores = model.predict(np.asarray([
            [float(row.get(name) or 0.0) for name in features] for row in validation_rows
        ], dtype=np.float32), num_iteration=model.best_iteration)
        cutoffs = percentile_edges([float(value) for value in validation_scores], percentile_edges_list)
        for row, score in zip(rows, scores):
            observations.append({
                **row,
                "source": "alpha_vantage_time_series_daily",
                "model_training_source": "local_schwab_daily_history",
                "model_id": config["model_id"],
                "model_sha256": file_sha256(model_path),
                "model_score": score,
                "score_percentile_basket": basket_for_score(score, cutoffs, percentile_edges_list),
                "confidence_rank_1_to_100": percentile_rank(score, scores),
                "confidence_rank_definition": "same-day universe score percentile; not probability",
                "research_only": True,
                "execution_decision": "AVOID",
            })
    return observations


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a source-separated Alpha Vantage Nasdaq model snapshot.")
    parser.add_argument("--daily-dir", type=Path, required=True)
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--research-root", type=Path, required=True)
    parser.add_argument("--market-date", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--percentile-edges", type=int, nargs="+", default=DEFAULT_PERCENTILE_EDGES)
    args = parser.parse_args()
    rows = score_snapshot(args.daily_dir, args.symbols_file, args.research_root, args.market_date, args.percentile_edges)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "market_date": args.market_date,
        "observations": rows,
        "warning": "Alpha Vantage inputs scored by Schwab-trained models are a source-shift diagnostic, not performance evidence or a trading signal.",
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "complete", "research_only": True, "execution_enabled": False,
        "market_date": args.market_date, "observations": len(rows),
        "top_by_model": {
            model_id: max((row for row in rows if row["model_id"] == model_id), key=lambda row: row["model_score"])["symbol"]
            for model_id in sorted({row["model_id"] for row in rows})
        },
    }, indent=2))


if __name__ == "__main__":
    main()
