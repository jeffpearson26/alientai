from __future__ import annotations

"""Build a source-pure, complete-101 payload for paper simulation only."""

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np

from alientai_v2.engines.nasdaq101_baseline_paper import (
    EXPECTED_MODEL_SHA256,
    EXPECTED_REPORT_SHA256,
    EXPECTED_SYMBOLS_SHA256,
    EXPECTED_UNIVERSE_SIZE,
    LOCKED_SCORE_CUTOFF,
    MAX_CANDIDATES,
    POLICY_ID,
)
from alientai_v2.research.score_calibration import percentile_rank
from evaluate_context_portfolio import file_sha256
from journal_nasdaq_challengers import (
    latest_common_date,
    load_candles,
    prospective_row,
    schwab_session_date,
    symbols,
    validate_market_date_freshness,
)


def validate_source_pure_histories(
    daily_dir: Path,
    symbol_list: list[str],
    market_date: str,
) -> None:
    duplicate_symbols: list[str] = []
    missing_market_date: list[str] = []
    for symbol in symbol_list:
        path = daily_dir / f"{symbol}_schwab_1d_max.csv"
        if not path.exists():
            raise ValueError(f"missing frozen-source history: {path}")
        with path.open(encoding="utf-8", newline="") as handle:
            counts = Counter(
                str(row.get("date") or "")
                for row in csv.DictReader(handle)
                if row.get("date")
            )
        if any(count > 1 for count in counts.values()):
            duplicate_symbols.append(symbol)
        if counts.get(market_date) != 1:
            missing_market_date.append(symbol)
    if duplicate_symbols:
        raise ValueError(
            "duplicate source sessions are unusable for "
            f"{len(duplicate_symbols)}/{len(symbol_list)} symbols; "
            f"examples: {', '.join(duplicate_symbols[:5])}"
        )
    if missing_market_date:
        raise ValueError(
            f"market date {market_date} is not exactly present for "
            f"{len(missing_market_date)}/{len(symbol_list)} symbols; "
            f"examples: {', '.join(missing_market_date[:5])}"
        )


def build_payload(
    daily_dir: Path,
    symbols_file: Path,
    model_path: Path,
    report_path: Path,
    market_date: str,
    maximum_candidates: int,
    maximum_market_age_calendar_days: int,
) -> dict[str, Any]:
    symbol_list = symbols(symbols_file)
    if len(symbol_list) != EXPECTED_UNIVERSE_SIZE or len(set(symbol_list)) != EXPECTED_UNIVERSE_SIZE:
        raise ValueError("paper payload requires exactly 101 unique frozen symbols")
    if file_sha256(symbols_file) != EXPECTED_SYMBOLS_SHA256:
        raise ValueError("frozen Nasdaq-101 symbol file hash mismatch")
    if file_sha256(model_path) != EXPECTED_MODEL_SHA256:
        raise ValueError("frozen Nasdaq-101 baseline model hash mismatch")
    if file_sha256(report_path) != EXPECTED_REPORT_SHA256:
        raise ValueError("frozen Nasdaq-101 training-report hash mismatch")

    market_session_date = schwab_session_date(market_date)
    market_date_age = validate_market_date_freshness(
        market_session_date,
        datetime.now(timezone.utc).date(),
        maximum_market_age_calendar_days,
    )
    validate_source_pure_histories(daily_dir, symbol_list, market_date)
    rows = [
        prospective_row(
            load_candles(daily_dir / f"{symbol}_schwab_1d_max.csv"),
            symbol,
            market_date,
        )
        for symbol in symbol_list
    ]
    if len(rows) != EXPECTED_UNIVERSE_SIZE or {row["symbol"] for row in rows} != set(symbol_list):
        raise ValueError("paper payload technical panel is not complete-101")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    feature_names = list(report.get("feature_names") or [])
    if not feature_names:
        raise ValueError("training report has no feature names")
    model = lgb.Booster(model_file=str(model_path))
    if model.feature_name() != feature_names:
        raise ValueError("model/report feature-order mismatch")
    matrix = np.asarray(
        [[float(row.get(name) or 0.0) for name in feature_names] for row in rows],
        dtype=np.float32,
    )
    scores = [
        float(value)
        for value in model.predict(matrix, num_iteration=model.best_iteration)
    ]
    ranked = sorted(
        zip(rows, scores),
        key=lambda item: (-item[1], str(item[0]["symbol"])),
    )
    candidates = [{
        "symbol": str(row["symbol"]).upper(),
        "market_date": market_date,
        "market_session_date": market_session_date,
        "model_score": score,
        "locked_score_cutoff": LOCKED_SCORE_CUTOFF,
        "confidence_rank_1_to_100": percentile_rank(score, scores),
        "confidence_rank_definition": "same-day complete-101 model-score percentile; not probability",
        "paper_decision": "BUY_CANDIDATE",
        "policy_id": POLICY_ID,
    } for row, score in ranked if score >= LOCKED_SCORE_CUTOFF][:maximum_candidates]

    return {
        "status": "paper_payload_ready",
        "research_only": True,
        "paper_only": True,
        "live_trading_enabled": False,
        "policy_id": POLICY_ID,
        "source": "schwab_daily_history",
        "source_pure": True,
        "market_date": market_date,
        "market_session_date": market_session_date,
        "market_date_age_calendar_days": market_date_age,
        "training_universe_size": EXPECTED_UNIVERSE_SIZE,
        "training_universe_symbols": symbol_list,
        "universe_rows": len(rows),
        "symbols_sha256": EXPECTED_SYMBOLS_SHA256,
        "model_sha256": EXPECTED_MODEL_SHA256,
        "training_report_sha256": EXPECTED_REPORT_SHA256,
        "locked_score_cutoff": LOCKED_SCORE_CUTOFF,
        "maximum_candidates": maximum_candidates,
        "candidates": candidates,
        "paper_evidence_separate_from_prospective_research": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--daily-dir", type=Path, required=True)
    parser.add_argument("--symbols-file", type=Path, default=Path("nasdaq100_2026-06_symbols.txt"))
    parser.add_argument(
        "--model",
        type=Path,
        default=Path("data_v2/rcef_research/nasdaq100_complete_clone/model_10pct/natural_technical_context_classifier.txt"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("data_v2/rcef_research/nasdaq100_complete_clone/model_10pct/natural_technical_context_report.json"),
    )
    parser.add_argument("--market-date")
    parser.add_argument("--maximum-candidates", type=int, default=MAX_CANDIDATES)
    parser.add_argument("--maximum-market-age-calendar-days", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.maximum_candidates not in range(1, MAX_CANDIDATES + 1):
        raise ValueError(f"maximum candidates must be between 1 and {MAX_CANDIDATES}")
    market_date = args.market_date or latest_common_date(
        args.daily_dir,
        symbols(args.symbols_file),
        "QQQ",
    )
    payload = build_payload(
        args.daily_dir,
        args.symbols_file,
        args.model,
        args.report,
        market_date,
        args.maximum_candidates,
        args.maximum_market_age_calendar_days,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": payload["status"],
        "policy_id": payload["policy_id"],
        "market_session_date": payload["market_session_date"],
        "universe_rows": payload["universe_rows"],
        "candidates": len(payload["candidates"]),
        "paper_only": payload["paper_only"],
        "live_trading_enabled": payload["live_trading_enabled"],
    }, indent=2))


if __name__ == "__main__":
    main()
