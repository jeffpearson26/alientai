from __future__ import annotations

"""Score and journal one future barrier-probability calibration snapshot."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from alientai_v2.research.barrier_probability_model import (
    FEATURE_NAMES,
    project_probability_bounds,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def apply_isotonic(
    scores: np.ndarray,
    blocks: Sequence[Mapping[str, float]],
) -> np.ndarray:
    uppers = np.asarray(
        [float(block["upper_score"]) for block in blocks],
        dtype=float,
    )
    probabilities = np.asarray(
        [float(block["probability"]) for block in blocks],
        dtype=float,
    )
    indices = np.searchsorted(uppers, scores.astype(float), side="left")
    return probabilities[np.minimum(indices, len(probabilities) - 1)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--journal", type=Path, required=True)
    args = parser.parse_args()
    snapshot_manifest_path = args.snapshot_dir / "snapshot_manifest.json"
    snapshot_manifest = json.loads(
        snapshot_manifest_path.read_text(encoding="utf-8")
    )
    snapshot_path = Path(snapshot_manifest["artifact"]["path"])
    report_path = args.model_dir / "training_report.json"
    audit_path = Path(snapshot_manifest["model_audit_path"])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    model_id = str(report.get("model_id") or "")
    if (
        not model_id
        or snapshot_manifest.get("model_id") != model_id
        or audit.get("model_id") != model_id
        or audit.get("status") != "PASS"
        or report.get("status")
        != "FROZEN_PENDING_PROSPECTIVE_REVIEW"
    ):
        raise ValueError("frozen model identity or readiness mismatch")
    if snapshot_manifest.get("outcomes_attached") is not False:
        raise ValueError("snapshot contains outcomes")
    if sha256(snapshot_path) != snapshot_manifest["artifact"]["sha256"]:
        raise ValueError("snapshot hash mismatch")
    if sha256(report_path) != snapshot_manifest["model_report_sha256"]:
        raise ValueError("snapshot model-report hash mismatch")
    if sha256(audit_path) != snapshot_manifest["model_audit_sha256"]:
        raise ValueError("snapshot model-audit hash mismatch")

    rows = read_jsonl(snapshot_path)
    expected_rows = int(snapshot_manifest.get("eligible_candidate_count", -1))
    if (
        not rows
        or len(rows) != expected_rows
        or len({row["symbol"] for row in rows}) != expected_rows
    ):
        raise ValueError("snapshot eligible universe is incomplete")
    matrix = np.asarray(
        [[float(row[name]) for name in FEATURE_NAMES] for row in rows],
        dtype=np.float32,
    )
    if not np.all(np.isfinite(matrix)):
        raise ValueError("snapshot feature matrix is invalid")
    lower_path = Path(report["lower_model_path"])
    upper_path = Path(report["upper_model_path"])
    calibration_path = Path(report["calibration_path"])
    if (
        sha256(lower_path) != report["lower_model_sha256"]
        or sha256(upper_path) != report["upper_model_sha256"]
        or sha256(calibration_path) != report["calibration_sha256"]
    ):
        raise ValueError("model artifact hash mismatch")
    calibration = json.loads(calibration_path.read_text(encoding="utf-8"))
    lower_model = lgb.Booster(model_file=str(lower_path))
    upper_model = lgb.Booster(model_file=str(upper_path))
    lower_raw = apply_isotonic(
        lower_model.predict(matrix),
        calibration["lower_bound_blocks"],
    )
    upper_raw = apply_isotonic(
        upper_model.predict(matrix),
        calibration["upper_bound_blocks"],
    )
    lower, upper, crossed = project_probability_bounds(lower_raw, upper_raw)
    predictions = [
        {
            "symbol": str(row["symbol"]),
            "decision_adjusted_close": float(row["decision_adjusted_close"]),
            "conservative_lower_probability": float(lower_probability),
            "optimistic_upper_probability": float(upper_probability),
            "diagnostic_midpoint_probability": float(
                (lower_probability + upper_probability) / 2.0
            ),
        }
        for row, lower_probability, upper_probability in zip(
            rows,
            lower,
            upper,
        )
    ]
    predictions.sort(
        key=lambda row: (
            -row["conservative_lower_probability"],
            row["symbol"],
        )
    )
    existing = read_jsonl(args.journal)
    decision_date = str(snapshot_manifest["decision_date"])
    if any(
        row.get("model_id") == model_id
        and row.get("decision_date") == decision_date
        for row in existing
    ):
        raise ValueError("journal already contains this decision date")
    observation = {
        "schema_version": 1,
        "model_id": model_id,
        "decision_date": decision_date,
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_provider": "Alpha Vantage",
        "snapshot_manifest_path": str(snapshot_manifest_path.resolve()),
        "snapshot_manifest_sha256": sha256(snapshot_manifest_path),
        "model_report_sha256": sha256(report_path),
        "model_audit_sha256": sha256(audit_path),
        "entry": "next regular-session adjusted open",
        "upper_barrier_pct": 1.5,
        "lower_barrier_pct": 0.5,
        "maximum_horizon_sessions": 10,
        "probability_interpretation": (
            "conservative and optimistic daily-path bounds; midpoint diagnostic"
        ),
        "pre_projection_crossing_count": int(np.sum(crossed)),
        "predictions": predictions,
        "status": "FUTURE_CALIBRATION_OUTCOME_PENDING",
        "research_only": True,
        "execution_decision": "AVOID",
    }
    args.journal.parent.mkdir(parents=True, exist_ok=True)
    with args.journal.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(observation, sort_keys=True, separators=(",", ":"))
            + "\n"
        )
    print(
        json.dumps(
            {
                "status": observation["status"],
                "decision_date": decision_date,
                "predictions": len(predictions),
                "highest_conservative_probabilities": predictions[:5],
                "journal": str(args.journal),
                "execution_decision": "AVOID",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
