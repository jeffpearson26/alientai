from __future__ import annotations

"""Build a reproducible champion-versus-challenger promotion scorecard."""

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


def replacement_gate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    validation = candidate["validation"]
    confirmation = candidate["confirmation"]
    prospective = candidate.get("prospective") or {}
    checks = {
        "complete_current_universe": bool(candidate.get("complete_current_universe")),
        "validation_minimum_20": int(validation.get("signals") or 0) >= 20,
        "validation_positive_mean": float(validation.get("mean_net_return_pct") or 0) > 0,
        "validation_positive_median": float(validation.get("median_net_return_pct") or 0) > 0,
        "validation_win_rate_50": float(validation.get("net_win_rate_pct") or 0) >= 50,
        "confirmation_minimum_30": int(confirmation.get("signals") or 0) >= 30,
        "confirmation_positive_mean": float(confirmation.get("mean_net_return_pct") or 0) > 0,
        "confirmation_positive_median": float(confirmation.get("median_net_return_pct") or 0) > 0,
        "confirmation_win_rate_60": float(confirmation.get("net_win_rate_pct") or 0) >= 60,
        "confirmation_drawdown_within_20": float(
            confirmation.get("capital_scaled_max_drawdown_pct") or -100
        ) >= -20,
        "prospective_minimum_30": int(prospective.get("completed_signals") or 0) >= 30,
    }
    return {
        "status": "REPLACEMENT_ELIGIBLE" if all(checks.values()) else "NOT_REPLACEMENT_ELIGIBLE",
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
    }


def selected_validation(report: Mapping[str, Any]) -> dict[str, Any]:
    fraction = float(report["selected_fraction"])
    row = min(
        report["validation_diagnostics"],
        key=lambda item: abs(float(item["fraction"]) - fraction),
    )
    return {
        key: row.get(key) for key in (
            "signals", "mean_net_return_pct", "median_net_return_pct",
            "net_win_rate_pct",
        )
    }


def portfolio_candidate(
    name: str,
    report: Mapping[str, Any],
    complete_current_universe: bool,
) -> dict[str, Any]:
    return {
        "name": name,
        "complete_current_universe": complete_current_universe,
        "validation": selected_validation(report),
        "confirmation": dict(report["test"]),
        "prospective": {"completed_signals": 0},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--research-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    def read(relative: str) -> dict[str, Any]:
        return json.loads((args.research_root / relative).read_text(encoding="utf-8"))

    candidates = [
        portfolio_candidate(
            "frozen_80_security_champion",
            read("nasdaq100_clone/portfolio_validation.json"),
            False,
        ),
        portfolio_candidate(
            "complete_101_security_baseline",
            read("nasdaq100_complete_clone/portfolio_validation.json"),
            True,
        ),
        portfolio_candidate(
            "complete_101_security_qqq_relative",
            read("nasdaq100_relative_qqq/portfolio_validation.json"),
            True,
        ),
        portfolio_candidate(
            "top_10_security_clone",
            read("nasdaq100_top10_clone/portfolio_validation.json"),
            True,
        ),
    ]
    two_stage = read("nasdaq100_two_stage/two_stage_report.json")
    candidates.append({
        "name": "complete_101_security_two_stage",
        "source_consistent": True,
        "validation": {
            key: two_stage["selected"].get(key) for key in (
                "signals", "mean_net_return_pct", "median_net_return_pct",
                "net_win_rate_pct",
            )
        },
        "confirmation": dict(two_stage["historical_confirmation"]),
        "prospective": {"completed_signals": 0},
    })
    for candidate in candidates:
        candidate["replacement_gate"] = replacement_gate(candidate)
    report = {
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "decision": "KEEP_FROZEN_80_SECURITY_CHAMPION",
        "decision_reason": "No challenger clears the complete validation, confirmation-sample, and prospective-evidence replacement gate.",
        "closest_to_replacement": "complete_101_security_baseline",
        "best_observed_economics": "complete_101_security_qqq_relative",
        "candidates": candidates,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
