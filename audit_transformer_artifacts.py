from __future__ import annotations

"""Read-only audit of the active Transformer artifact versus trained candidates."""

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def artifact_summary(directory: Path, prefix: str) -> dict[str, Any]:
    config_path = directory / f"{prefix}_config.json"
    model_path = directory / f"{prefix}_model.pt"
    scaler_path = directory / f"{prefix}_scaler.json"
    config = load_json(config_path)
    symbols = config.get("symbols_used") if isinstance(config.get("symbols_used"), list) else []
    return {
        "directory": str(directory), "build": config.get("build"), "created_at": config.get("created_at"),
        "horizon_days": config.get("horizon_days"), "symbols_used": len(symbols),
        "model_exists": model_path.exists(), "scaler_exists": scaler_path.exists(),
        "model_modified": model_path.stat().st_mtime if model_path.exists() else None,
        "scaler_modified": scaler_path.stat().st_mtime if scaler_path.exists() else None,
    }


def audit(active: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    same_build = active.get("build") == candidate.get("build")
    candidate_broader = int(candidate.get("symbols_used") or 0) > int(active.get("symbols_used") or 0)
    return {
        "status": "RESEARCH_HOLD" if not same_build or candidate_broader else "ARTIFACTS_COMPARABLE",
        "research_only": True, "execution_enabled": False,
        "active": active, "candidate": candidate,
        "reasons": [reason for reason, condition in {
            "active and candidate artifacts are different training builds": not same_build,
            "candidate has broader symbol coverage and requires independent promotion review": candidate_broader,
        }.items() if condition],
        "next_action": "Do not replace active artifact automatically; run an explicit compatibility and holdout review first.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Transformer artifact lineage without modifying runtime files.")
    parser.add_argument("--active-dir", type=Path, required=True)
    parser.add_argument("--active-prefix", required=True)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--candidate-prefix", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(artifact_summary(args.active_dir, args.active_prefix), artifact_summary(args.candidate_dir, args.candidate_prefix))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
