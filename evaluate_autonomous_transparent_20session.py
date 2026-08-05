from __future__ import annotations

"""Evaluate the predeclared transparent 20-session champion control."""

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

import train_nasdaq101_126session_technical_model as research


research.HORIZON_SESSIONS = 20
research.EMBARGO_SESSIONS = 20
research.HAC_LAG_SESSIONS = 19
research.PORTFOLIO_SLOTS = research.MAX_DAILY_SELECTIONS * 20
research.TARGET = "label_20d_net_return_pct"
research.GROSS = "label_20d_gross_return_pct"
research.LABEL_END = "label_20d_exit_market_date"
research.MODEL_TARGET = "model_excess_to_qqq_20d_pct"
research.MIN_DECISION_PRICE = 5.0
research.MIN_AVERAGE_DOLLAR_VOLUME_20D = 20_000_000.0
research.MIN_NONOVERLAP_OBSERVED_FOLDS = 4
research.MIN_NONOVERLAP_POSITIVE_FOLDS = 3


def eligible(row: Mapping[str, Any]) -> bool:
    return (
        row.get(research.TARGET) is not None
        and row.get(research.LABEL_END)
        and float(row.get("decision_adjusted_close") or 0.0)
        >= research.MIN_DECISION_PRICE
        and float(row.get("lh_average_dollar_volume_20d") or 0.0)
        >= research.MIN_AVERAGE_DOLLAR_VOLUME_20D
    )


def score_rows(rows: Sequence[Mapping[str, Any]]) -> np.ndarray:
    return np.asarray(
        [
            0.50 * float(row.get("rank_relative_to_qqq_126d_pct") or 0.0)
            + 0.30 * float(row.get("rank_relative_to_qqq_60d_pct") or 0.0)
            + 0.20
            * (
                1.0
                - float(
                    row.get("rank_lh_realized_volatility_60d_pct") or 0.5
                )
            )
            for row in rows
        ],
        dtype=float,
    )


def evaluate(
    rows: list[dict[str, Any]],
    daily: Mapping[str, Sequence[Mapping[str, Any]]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    research.add_cross_sectional_feature_ranks(rows)
    research.add_qqq_relative_targets(rows, daily["QQQ"])
    selected, diagnostics = research.selected_rows(
        rows, score_rows(rows), -1.0
    )
    metrics = research.basic_metrics(selected, daily)
    nonoverlap = research.nonoverlap_summary(selected)
    qqq_control = research.basic_metrics(
        research.matched_qqq_control_rows(selected, daily["QQQ"]), daily
    )
    passes = (
        metrics.get("signals", 0) >= 250
        and metrics.get("decision_dates", 0) >= 100
        and metrics.get("mean_net_return_pct", -999.0) > 0.0
        and metrics.get("median_net_return_pct", -999.0) > 0.0
        and metrics.get("win_rate_pct", 0.0) >= 52.0
        and metrics.get("hac_mean_net_ci95_low_pct") is not None
        and metrics["hac_mean_net_ci95_low_pct"] > 0.0
        and metrics.get(
            "cash_scaled_mark_to_market_max_drawdown_pct", -999.0
        )
        >= -20.0
        and metrics.get("largest_symbol_share_pct", 100.0) <= 12.0
        and nonoverlap["observed_folds"]
        >= research.MIN_NONOVERLAP_OBSERVED_FOLDS
        and nonoverlap["positive_mean_folds"]
        >= research.MIN_NONOVERLAP_POSITIVE_FOLDS
        and nonoverlap["median_fold_mean_net_pct"] > 0.0
        and metrics.get("mean_net_return_pct", -999.0)
        > qqq_control.get("mean_net_return_pct", 999.0)
    )
    return selected, {
        "passes_gate": passes,
        **diagnostics,
        **metrics,
        "20_rotating_nonoverlap_cohorts": nonoverlap,
        "matched_qqq_control": qqq_control,
    }


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
        or manifest.get("horizon_sessions") != 20
        or manifest.get("panel_sha256") != research.sha256(args.input)
    ):
        raise ValueError("invalid champion panel")
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
        if eligible(row)
    ]
    daily = research.load_daily_paths(
        args.daily_root, [*candidates, "QQQ"]
    )
    _, policy = evaluate(policy_rows, daily)

    if policy["passes_gate"]:
        test_rows = [
            row
            for row in research.read_rows_for_dates(args.input, splits["test"])
            if eligible(row)
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
        "model_family": (
            "transparent cross-sectional 126/60-session momentum plus "
            "inverse 60-session volatility"
        ),
        "formula": (
            "0.50*rank(excess_126d_vs_QQQ) + "
            "0.30*rank(excess_60d_vs_QQQ) + "
            "0.20*(1-rank(realized_volatility_60d))"
        ),
        "horizon_sessions": 20,
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
