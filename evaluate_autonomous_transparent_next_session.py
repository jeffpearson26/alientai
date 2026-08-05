from __future__ import annotations

"""Evaluate the transparent champion formula on a next-session-close target."""

import argparse
import json
from pathlib import Path

import evaluate_autonomous_transparent_20session as source


research = source.research
research.HORIZON_SESSIONS = 1
research.EMBARGO_SESSIONS = 1
research.HAC_LAG_SESSIONS = 0
research.PORTFOLIO_SLOTS = research.MAX_DAILY_SELECTIONS
research.TARGET = "label_1d_net_return_pct"
research.GROSS = "label_1d_gross_return_pct"
research.LABEL_END = "label_1d_exit_market_date"
research.MODEL_TARGET = "model_excess_to_qqq_1d_pct"
research.MIN_DECISION_PRICE = 5.0
research.MIN_AVERAGE_DOLLAR_VOLUME_20D = 20_000_000.0
research.MIN_NONOVERLAP_OBSERVED_FOLDS = 1
research.MIN_NONOVERLAP_POSITIVE_FOLDS = 1


def evaluate(rows, daily):
    selected, result = source.evaluate(rows, daily)
    old_key = "20_rotating_nonoverlap_cohorts"
    result["1_rotating_nonoverlap_cohort"] = result.pop(old_key)
    return selected, result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--daily-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("output already exists")

    manifest_path = args.input.with_suffix(".manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("status") != "complete"
        or manifest.get("horizon_sessions") != 1
        or manifest.get("panel_sha256") != research.sha256(args.input)
    ):
        raise ValueError("invalid next-session champion panel")
    candidates = list(manifest.get("candidates") or [])
    if len(candidates) != 101:
        raise ValueError("exact 101-candidate universe required")

    dates = research.scan_panel_dates_without_parsing_labels(args.input)
    stride = int(manifest.get("decision_stride_market_sessions", 1))
    splits = research.split_dates(dates, stride)
    policy_rows = [
        row
        for row in research.read_rows_for_dates(
            args.input, splits["policy_validation"]
        )
        if source.eligible(row)
    ]
    daily = research.load_daily_paths(
        args.daily_root, [*candidates, "QQQ"]
    )
    _, policy = evaluate(policy_rows, daily)

    if policy["passes_gate"]:
        test_rows = [
            row
            for row in research.read_rows_for_dates(args.input, splits["test"])
            if source.eligible(row)
        ]
        _, test_metrics = evaluate(test_rows, daily)
        status = "FROZEN_PENDING_PROSPECTIVE"
        test = {
            "status": "OPENED_ONCE_AFTER_VALIDATION_PASS",
            "json_parsed": True,
            **test_metrics,
        }
    else:
        status = "RESEARCH_HOLD"
        test = {
            "status": "SEALED_UNLOADED",
            "json_parsed": False,
            "reason": "transparent policy failed frozen validation gate",
        }

    report = {
        "status": status,
        "research_only": True,
        "execution_enabled": False,
        "source_model_id": "autonomous_transparent_20session",
        "clone_model_id": "autonomous_transparent_next_session_close_v1",
        "model_family": (
            "transparent cross-sectional 126/60-session momentum plus "
            "inverse 60-session volatility"
        ),
        "formula": (
            "0.50*rank(excess_126d_vs_QQQ) + "
            "0.30*rank(excess_60d_vs_QQQ) + "
            "0.20*(1-rank(realized_volatility_60d))"
        ),
        "horizon_sessions": 1,
        "entry": "next regular-session adjusted open",
        "exit": "that next regular session's official adjusted close",
        "round_trip_cost_pct": 0.25,
        "input": str(args.input),
        "input_sha256": research.sha256(args.input),
        "panel_manifest_sha256": research.sha256(manifest_path),
        "candidate_count": len(candidates),
        "policy_validation_dates": len(splits["policy_validation"]),
        "test_dates_reserved": len(splits["test"]),
        "eligibility": {
            "minimum_price": research.MIN_DECISION_PRICE,
            "minimum_average_dollar_volume_20d": (
                research.MIN_AVERAGE_DOLLAR_VOLUME_20D
            ),
        },
        "policy_validation": policy,
        "test": test,
        "warnings": [
            "fixed June 2026 membership creates survivorship bias",
            "historical passage alone cannot authorize trading",
            "source model evidence is not inherited by this clone",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": status,
                "policy_pass": policy["passes_gate"],
                "policy_signals": policy.get("signals"),
                "policy_mean_net_return_pct": policy.get(
                    "mean_net_return_pct"
                ),
                "policy_win_rate_pct": policy.get("win_rate_pct"),
                "test_status": test["status"],
                "output": str(args.output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
