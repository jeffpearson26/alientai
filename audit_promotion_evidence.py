"""Fail-closed audit of a historical report against the frozen promotion protocol."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


REQUIRED_ARTIFACT_FIELDS = (
    "base_rows_sha256", "option_features_sha256", "technical_model_sha256",
)
REQUIRED_METRICS = (
    "signals", "mean_net_return_pct", "median_net_return_pct", "win_rate_after_cost",
    "fifth_percentile_net_return_pct", "worst_trade_net_return_pct",
    "approximate_cohort_max_drawdown_pct", "largest_symbol_signal_share",
)


def audit(report: Mapping[str, Any]) -> dict[str, Any]:
    artifacts = report.get("input_artifacts") if isinstance(report.get("input_artifacts"), Mapping) else {}
    results = report.get("results") if isinstance(report.get("results"), list) else []
    missing_artifacts = [field for field in REQUIRED_ARTIFACT_FIELDS if not artifacts.get(field)]
    candidates = []
    for index, result in enumerate(results):
        if not isinstance(result, Mapping):
            continue
        missing_metrics = [field for field in REQUIRED_METRICS if result.get(field) is None]
        gate = result.get("rare_signal_gate") if isinstance(result.get("rare_signal_gate"), Mapping) else {}
        candidates.append({
            "result_index": index,
            "selection": result.get("technical_top_fraction_selected_on_calibration"),
            "historical_gate": gate.get("status"),
            "missing_metrics": missing_metrics,
            "eligible_for_paper_review": not missing_artifacts and not missing_metrics and gate.get("status") == "RESEARCH_PASS",
        })
    return {
        "status": "complete", "research_only": True, "execution_enabled": False,
        "promotion_authorized": False,
        "missing_artifact_identities": missing_artifacts,
        "candidates": candidates,
        "warning": "Historical evidence and this audit never authorize paper or live trading; the prospective shadow gate and Jeff's separate review are still required.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    result = audit(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
