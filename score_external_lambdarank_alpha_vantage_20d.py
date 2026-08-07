from __future__ import annotations

"""Score one future date with the frozen Alpha Vantage LambdaRank clone."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import lightgbm as lgb
import pandas as pd

from alientai_v2.research.external_lambdarank_alpha_vantage_20d import (
    FEATURE_COLUMNS,
    HORIZON_SESSIONS,
    MODEL_ID,
    ROUND_TRIP_COST_PCT,
    select_latest,
    sha256,
)


def _read_journal(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--decision-date", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--journal", type=Path)
    args = parser.parse_args()
    if args.output_root.exists() and any(args.output_root.iterdir()):
        raise ValueError(f"output root must be new or empty: {args.output_root}")

    snapshot_manifest_path = (
        args.snapshot_root / "snapshot_manifest.json"
    )
    feature_path = args.snapshot_root / "feature_snapshot.csv"
    training_path = args.model_root / "training_report.json"
    metadata_path = args.model_root / "model_metadata.json"
    model_audit_path = args.model_root / "independent_model_audit.json"
    model_path = args.model_root / "model.txt"
    snapshot = json.loads(
        snapshot_manifest_path.read_text(encoding="utf-8")
    )
    training = json.loads(training_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    model_audit = json.loads(model_audit_path.read_text(encoding="utf-8"))
    if (
        training.get("status") != "READY_FOR_FUTURE_ONLY_TEST"
        or model_audit.get("status") != "PASS"
    ):
        raise ValueError("training or independent model audit is not ready")
    if (
        snapshot.get("model_id") != MODEL_ID
        or metadata.get("model_id") != MODEL_ID
        or model_audit.get("model_id") != MODEL_ID
    ):
        raise ValueError("model ID mismatch")
    if snapshot.get("decision_date") != args.decision_date:
        raise ValueError("snapshot decision date mismatch")
    if snapshot.get("outcomes_attached") is not False:
        raise ValueError("future snapshot contains outcomes")
    if snapshot["source_contract"].get("provider") != "Alpha Vantage":
        raise ValueError("snapshot provider mismatch")
    if metadata.get("feature_columns") != list(FEATURE_COLUMNS):
        raise ValueError("feature contract mismatch")
    if sha256(metadata_path) != snapshot["model_metadata_sha256"]:
        raise ValueError("snapshot model metadata hash mismatch")
    if sha256(model_audit_path) != snapshot["model_audit_sha256"]:
        raise ValueError("snapshot model audit hash mismatch")
    if sha256(feature_path) != snapshot["artifact"]["sha256"]:
        raise ValueError("snapshot feature hash mismatch")
    if sha256(model_path) != metadata["model_sha256"]:
        raise ValueError("model artifact hash mismatch")
    if args.decision_date <= str(
        metadata["prospective_eligible_after_session"]
    ):
        raise ValueError("decision date is not genuinely prospective")

    frame = pd.read_csv(feature_path)
    day = frame[
        frame["market_date"].astype(str) == args.decision_date
    ].copy()
    if len(day) != 120 or day["symbol"].nunique() != 120:
        raise ValueError("future score frame is incomplete")
    if day[list(FEATURE_COLUMNS)].isna().any().any():
        raise ValueError("future features contain missing values")
    booster = lgb.Booster(model_file=str(model_path))
    day["model_score"] = booster.predict(day[list(FEATURE_COLUMNS)])
    selected = select_latest(day, maximum_selections=10)
    observation = {
        "model_id": MODEL_ID,
        "decision_date": args.decision_date,
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_provider": "Alpha Vantage",
        "source_manifest": str(snapshot_manifest_path.resolve()),
        "source_manifest_sha256": sha256(snapshot_manifest_path),
        "feature_snapshot_sha256": sha256(feature_path),
        "model_sha256": sha256(model_path),
        "horizon_sessions": HORIZON_SESSIONS,
        "entry": "next complete regular-session adjusted open",
        "exit": "twentieth subsequent regular-session adjusted close",
        "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
        "selection_policy": "top 10 model scores",
        "selections": [
            {
                "rank": rank,
                "symbol": str(row.symbol),
                "score": float(row.model_score),
            }
            for rank, row in enumerate(
                selected.itertuples(), start=1
            )
        ],
        "status": "FUTURE_OUTCOME_PENDING",
        "research_only": True,
        "execution_decision": "AVOID",
    }
    if args.journal is not None:
        existing = _read_journal(args.journal)
        if any(
            row.get("model_id") == MODEL_ID
            and row.get("decision_date") == args.decision_date
            for row in existing
        ):
            raise ValueError("journal already contains this decision date")
        args.journal.parent.mkdir(parents=True, exist_ok=True)
        with args.journal.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(observation, sort_keys=True, separators=(",", ":"))
                + "\n"
            )

    args.output_root.mkdir(parents=True, exist_ok=True)
    observation_path = args.output_root / "observation.json"
    ranking_path = args.output_root / "ranking.csv"
    observation_path.write_text(
        json.dumps(observation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    day.sort_values(
        ["model_score", "symbol"], ascending=[False, True]
    )[["market_date", "symbol", "model_score"]].to_csv(
        ranking_path, index=False
    )
    print(
        json.dumps(
            {
                "status": observation["status"],
                "decision_date": args.decision_date,
                "selections": observation["selections"],
                "output": str(observation_path),
                "journaled": args.journal is not None,
                "execution_decision": "AVOID",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
