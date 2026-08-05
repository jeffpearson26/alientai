from __future__ import annotations

"""Append one pre-entry autonomous transparent-model research observation."""

import argparse
import json
from datetime import UTC, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

import train_nasdaq101_126session_technical_model as research
from build_nasdaq101_126session_technical_panel import (
    BENCHMARKS,
    read_candidates,
)
from build_nasdaq_qqq_spy_60session_panel import load_adjusted_daily
from evaluate_autonomous_transparent_20session import score_rows
from score_nasdaq101_126session_technical_model import latest_rows


EXPECTED_FORMULA = (
    "0.50*rank(excess_126d_vs_QQQ) + "
    "0.30*rank(excess_60d_vs_QQQ) + "
    "0.20*(1-rank(realized_volatility_60d))"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--daily-root", type=Path, required=True)
    parser.add_argument("--candidates-file", type=Path, required=True)
    parser.add_argument("--journal", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    if (
        report.get("status") != "FROZEN_PENDING_PROSPECTIVE"
        or report.get("formula") != EXPECTED_FORMULA
        or report.get("horizon_sessions") != 20
        or report.get("test", {}).get("status")
        != "OPENED_ONCE_AFTER_VALIDATION_PASS"
    ):
        raise ValueError("frozen transparent report is not eligible")
    candidates = read_candidates(args.candidates_file)
    daily = {
        symbol: load_adjusted_daily(args.daily_root / f"{symbol}_daily.json")
        for symbol in [*candidates, *BENCHMARKS]
    }
    decision_date, rows = latest_rows(daily, candidates)
    eligibility = report["eligibility"]
    rows = [
        row
        for row in rows
        if float(row["decision_adjusted_close"])
        >= float(eligibility["minimum_price"])
        and float(row.get("lh_average_dollar_volume_20d") or 0.0)
        >= float(eligibility["minimum_average_dollar_volume_20d"])
    ]
    research.add_cross_sectional_feature_ranks(rows)
    scores = score_rows(rows)
    selected, diagnostics = research.selected_rows(rows, scores, -1.0)

    now = datetime.now(UTC)
    eastern = now.astimezone(ZoneInfo("America/New_York"))
    if eastern.date().isoformat() <= decision_date:
        raise ValueError("decision source is not from a prior completed date")
    if eastern.time() >= time(9, 30):
        raise ValueError("prospective entry window has already opened")
    existing = []
    if args.journal.exists():
        existing = [
            json.loads(line)
            for line in args.journal.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    if any(row.get("decision_date") == decision_date for row in existing):
        raise ValueError(f"decision date already journaled: {decision_date}")

    ranked = sorted(
        selected,
        key=lambda row: (-float(row["model_score"]), str(row["symbol"])),
    )
    record = {
        "schema_version": 1,
        "status": "SELECTIONS" if ranked else "ABSTENTION",
        "research_only": True,
        "execution_enabled": False,
        "decision_date": decision_date,
        "journaled_at_utc": now.isoformat(),
        "entry_contract": "next regular-session adjusted open",
        "exit_contract": "20th subsequent regular-session adjusted close",
        "round_trip_cost_pct": 0.25,
        "model_family": report["model_family"],
        "formula": EXPECTED_FORMULA,
        "frozen_report": str(args.report),
        "frozen_report_sha256": research.sha256(args.report),
        "candidate_universe_count": len(candidates),
        "eligible_universe_count": len(rows),
        "selection_diagnostics": diagnostics,
        "selections": [
            {
                "rank": rank,
                "symbol": str(row["symbol"]),
                "score": round(float(row["model_score"]), 8),
                "decision_adjusted_close": round(
                    float(row["decision_adjusted_close"]), 6
                ),
                "relative_to_qqq_60d_pct": row.get(
                    "relative_to_qqq_60d_pct"
                ),
                "relative_to_qqq_126d_pct": row.get(
                    "relative_to_qqq_126d_pct"
                ),
                "realized_volatility_60d_pct": row.get(
                    "lh_realized_volatility_60d_pct"
                ),
            }
            for rank, row in enumerate(ranked, start=1)
        ],
    }
    args.journal.parent.mkdir(parents=True, exist_ok=True)
    with args.journal.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
