from __future__ import annotations

"""Fail-closed validation for the research-only next-session clone registry."""

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


EXPECTED_SOURCE_MODELS = {
    "autonomous_transparent_20session",
    "contextual_options_top_quarter",
    "nasdaq100_complete_101_baseline_v1",
    "nasdaq100_complete_101_qqq_relative_v1",
    "nasdaq100_technical_clone_v1",
    "ai_semiconductor_60m_calls_frozen_20260731",
}


def validate_registry(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")
    if payload.get("research_only") is not True:
        raise ValueError("registry must remain research-only")
    if payload.get("execution_enabled") is not False:
        raise ValueError("execution must remain disabled")
    if float(payload.get("round_trip_cost_pct") or 0.0) != 0.25:
        raise ValueError("round-trip cost must remain 0.25%")

    clones = list(payload.get("clones") or [])
    if len(clones) != len(EXPECTED_SOURCE_MODELS):
        raise ValueError("registry must contain exactly six source-model clones")
    source_ids = {str(row.get("source_model_id") or "") for row in clones}
    if source_ids != EXPECTED_SOURCE_MODELS:
        raise ValueError("source-model set does not match the approved six models")
    clone_ids = [str(row.get("clone_model_id") or "") for row in clones]
    if len(set(clone_ids)) != len(clone_ids) or any(not value for value in clone_ids):
        raise ValueError("clone IDs must be unique and nonempty")

    for row in clones:
        if int(row.get("target_horizon_sessions") or 0) != 1:
            raise ValueError("every clone must target one complete session")
        if "official close" not in str(row.get("exit_contract") or "").lower():
            raise ValueError("every clone must exit at an official session close")
        if not row.get("feature_contract") or not row.get("entry_contract"):
            raise ValueError("every clone must preserve feature and entry contracts")

    return {
        "status": "PASS",
        "research_only": True,
        "execution_enabled": False,
        "clone_count": len(clones),
        "target_horizon_sessions": 1,
        "source_model_ids": sorted(source_ids),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("next_session_close_clone_registry.json"),
    )
    args = parser.parse_args()
    payload = json.loads(args.registry.read_text(encoding="utf-8"))
    print(json.dumps(validate_registry(payload), indent=2))


if __name__ == "__main__":
    main()
