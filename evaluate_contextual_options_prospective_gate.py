"""Aggregate completed source-consistent shadow outcomes behind a hard research gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from evaluate_matched_winner_full_universe import selection_metrics
from alientai_v2.research.rare_signal_gate import evaluate_rare_signal_gate


REQUIRED_SOURCE = "schwab_local_daily_csv"
MINIMUM_DISTINCT_MARKET_DATES = 10


def completed_records(reports: Iterable[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    rows, failures, seen = [], [], set()
    for report in reports:
        # Older progress snapshots may have no completed outcomes at all. They
        # cannot affect aggregate performance, so they must not invalidate a
        # later completed, source-approved review merely because that snapshot
        # predates source metadata.
        completed = [
            record for record in (report.get("records") or [])
            if isinstance(record, Mapping) and record.get("outcome_status") == "COMPLETE"
        ]
        if not completed:
            continue
        if report.get("research_only") is not True or report.get("execution_enabled") is not False:
            failures.append("report_not_explicitly_research_only")
            continue
        if report.get("source") != REQUIRED_SOURCE:
            failures.append("report_source_not_approved")
            continue
        for record in completed:
            key = (str(record.get("shadow_policy_id") or ""), str(record.get("symbol") or ""), str(record.get("market_date") or ""))
            if not all(key) or key in seen:
                failures.append("missing_or_duplicate_outcome_identity")
                continue
            try:
                raw = float(record["realized_return_pct"])
            except (KeyError, TypeError, ValueError):
                failures.append("completed_outcome_missing_return")
                continue
            seen.add(key)
            rows.append({**record, "label_forward_return_5d_pct": raw, "future_market_date": str(record.get("market_date") or "")})
    return rows, sorted(set(failures))


def evaluate(reports: Iterable[Mapping[str, Any]], round_trip_cost_pct: float = 0.25) -> dict[str, Any]:
    rows, failures = completed_records(reports)
    metrics = selection_metrics(rows, round_trip_cost_pct)
    distinct_dates = len({str(row.get("market_date") or "") for row in rows})
    gate = evaluate_rare_signal_gate(metrics)
    date_check = {"name": "minimum distinct decision dates", "observed": distinct_dates, "threshold": MINIMUM_DISTINCT_MARKET_DATES, "pass": distinct_dates >= MINIMUM_DISTINCT_MARKET_DATES}
    status = "RESEARCH_PASS" if gate["status"] == "RESEARCH_PASS" and date_check["pass"] and not failures else "RESEARCH_HOLD"
    return {"status": status, "research_only": True, "execution_enabled": False,
            "prospective_paper_review_eligible": False, "approved_source": REQUIRED_SOURCE,
            "completed_outcomes": len(rows), "distinct_market_dates": distinct_dates,
            "round_trip_cost_pct": round_trip_cost_pct, "metrics": metrics,
            "rare_signal_gate": gate, "date_diversity_check": date_check,
            "input_failures": failures,
            "warning": "Even a research pass requires a separate human review and does not enable paper trading."}


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate completed contextual-options shadow outcomes only.")
    parser.add_argument("--reviews-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    args = parser.parse_args()
    reports = []
    for path in sorted(args.reviews_dir.glob("contextual_options_shadow_review_*.json")):
        reports.append(json.loads(path.read_text(encoding="utf-8")))
    result = evaluate(reports, args.round_trip_cost_pct)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "completed_outcomes", "distinct_market_dates", "prospective_paper_review_eligible")}, indent=2))


if __name__ == "__main__":
    main()
