from __future__ import annotations

"""Build a fail-closed prospective shadow policy from natural-universe evidence."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping


def selection_fraction(value: str) -> float:
    try:
        return float(value.removeprefix("top_"))
    except (AttributeError, ValueError):
        return 1.0


def build_policy(
    natural_report: Mapping[str, Any], ablation_report: Mapping[str, Any],
) -> Dict[str, Any]:
    gate = natural_report.get("promotion_gate") or {}
    passing = [item for item in gate.get("checks", []) if bool(item.get("passed"))]
    combined = next(
        (item for item in ablation_report.get("experiments", []) if item.get("name") == "technical_plus_premarket"),
        None,
    )
    approved = gate.get("status") == "NATURAL_UNIVERSE_PASS" and bool(passing) and combined is not None
    base: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "execution_enabled": False,
        "paper_buying_enabled": False,
        "live_trading_enabled": False,
        "decision_cutoff_et": "09:25",
        "simulated_entry_rule": "first_regular_5min_bar_close",
        "horizon_trading_days": 5,
        "prospective_outcome_required": True,
        "natural_gate_status": gate.get("status", "NATURAL_UNIVERSE_HOLD"),
    }
    if not approved:
        return {
            **base, "status": "RESEARCH_HOLD", "shadow_recording_enabled": False,
            "reason": "Natural-universe promotion evidence is missing or did not pass.",
        }
    strictest = min(passing, key=lambda item: selection_fraction(str(item.get("selection") or "")))
    return {
        **base,
        "status": "PROSPECTIVE_SHADOW_APPROVED",
        "shadow_recording_enabled": True,
        "selection": strictest["selection"],
        "maximum_daily_universe_fraction": selection_fraction(str(strictest["selection"])),
        "model_name": "technical_plus_premarket",
        "model_path": combined.get("model_path"),
        "model_features": combined.get("model_features", []),
        "approval_basis": strictest,
        "note": "This policy may rank and journal candidates only. It cannot place orders.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--natural-report", type=Path, required=True)
    parser.add_argument("--ablation-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    policy = build_policy(
        json.loads(args.natural_report.read_text(encoding="utf-8")),
        json.loads(args.ablation_report.read_text(encoding="utf-8")),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(policy, indent=2))


if __name__ == "__main__":
    main()
