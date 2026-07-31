from __future__ import annotations

"""Append-only, non-executing prospective journal for the frozen Nasdaq-80 champion."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import lightgbm as lgb
import numpy as np

from evaluate_context_portfolio import file_sha256
from journal_nasdaq_challengers import (
    append_unique,
    load_candles,
    prospective_row,
    schwab_session_date,
    select_candidates,
    symbols,
    validate_market_date_freshness,
)


MODEL_ID = "nasdaq100_technical_clone_v1"
LOCKED_SCORE_CUTOFF = 0.15986412677273237
TARGET_HORIZON_SESSIONS = 5


def latest_universe_common_date(daily_dir: Path, symbol_list: Sequence[str]) -> str:
    common: set[str] | None = None
    for symbol in symbol_list:
        path = daily_dir / f"{symbol}_schwab_1d_max.csv"
        if not path.exists():
            raise ValueError(f"missing daily history: {path}")
        dates = {row["date"] for row in load_candles(path)}
        common = dates if common is None else common & dates
    if not common:
        raise ValueError("no common market date across the frozen universe")
    return max(common)


def frozen_manifest(
    model_path: Path,
    report_path: Path,
    symbols_path: Path,
    maximum_candidates: int,
    maximum_market_age_calendar_days: int,
) -> dict[str, Any]:
    return {
        "status": "frozen",
        "research_only": True,
        "execution_enabled": False,
        "model_id": MODEL_ID,
        "target_horizon_sessions": TARGET_HORIZON_SESSIONS,
        "decision_time": "after completed market-session close",
        "entry_reference": "same-session close; research outcome only",
        "exit_reference": "close five sessions later",
        "score_is_probability": False,
        "locked_score_cutoff": LOCKED_SCORE_CUTOFF,
        "maximum_candidates_per_day": maximum_candidates,
        "maximum_market_age_calendar_days": maximum_market_age_calendar_days,
        "model_sha256": file_sha256(model_path),
        "training_report_sha256": file_sha256(report_path),
        "symbols_file_sha256": file_sha256(symbols_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--daily-dir", type=Path, required=True)
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--market-date")
    parser.add_argument("--maximum-candidates", type=int, default=5)
    parser.add_argument("--maximum-market-age-calendar-days", type=int, default=1)
    args = parser.parse_args()

    symbol_list = symbols(args.symbols_file)
    market_date = args.market_date or latest_universe_common_date(
        args.daily_dir, symbol_list
    )
    market_session_date = schwab_session_date(market_date)
    market_date_age = validate_market_date_freshness(
        market_session_date,
        datetime.now(timezone.utc).date(),
        args.maximum_market_age_calendar_days,
    )
    requested_manifest = frozen_manifest(
        args.model,
        args.report,
        args.symbols_file,
        args.maximum_candidates,
        args.maximum_market_age_calendar_days,
    )
    if args.manifest.exists():
        existing = json.loads(args.manifest.read_text(encoding="utf-8"))
        if existing != requested_manifest:
            raise ValueError(
                "existing frozen manifest does not match requested configuration"
            )
    else:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            json.dumps(requested_manifest, indent=2) + "\n", encoding="utf-8"
        )

    rows = [
        prospective_row(
            load_candles(args.daily_dir / f"{symbol}_schwab_1d_max.csv"),
            symbol,
            market_date,
        )
        for symbol in symbol_list
    ]
    report = json.loads(args.report.read_text(encoding="utf-8"))
    feature_names = report["feature_names"]
    matrix = np.asarray(
        [
            [float(row.get(name) or 0.0) for name in feature_names]
            for row in rows
        ],
        dtype=np.float32,
    )
    model = lgb.Booster(model_file=str(args.model))
    scores = model.predict(matrix, num_iteration=model.best_iteration)
    selected = select_candidates(
        rows,
        scores,
        LOCKED_SCORE_CUTOFF,
        args.maximum_candidates,
    )
    observations = [
        {
            **row,
            "market_session_date": market_session_date,
            "model_id": MODEL_ID,
            "model_sha256": requested_manifest["model_sha256"],
            "locked_score_cutoff": LOCKED_SCORE_CUTOFF,
            "target_horizon_sessions": TARGET_HORIZON_SESSIONS,
            "status": "pending",
            "journaled_at_utc": datetime.now(timezone.utc).isoformat(),
            "research_only": True,
            "execution_decision": "AVOID",
        }
        for row in selected
    ]
    additions = append_unique(args.journal, observations)
    print(json.dumps({
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "model_id": MODEL_ID,
        "stored_market_date": market_date,
        "market_session_date": market_session_date,
        "market_date_age_calendar_days": market_date_age,
        "eligible_universe": len(symbol_list),
        "observations_selected": len(observations),
        "observations_appended": additions,
        "symbols": [row["symbol"] for row in observations],
        "journal": str(args.journal),
        "manifest": str(args.manifest),
    }, indent=2))


if __name__ == "__main__":
    main()
