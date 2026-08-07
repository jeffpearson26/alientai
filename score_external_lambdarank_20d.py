from __future__ import annotations

"""Score one explicit future decision date with the corrected LambdaRank model."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import lightgbm as lgb
import pandas as pd

from alientai_v2.research.external_lambdarank_20d import (
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
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


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
    report_path = args.model_root / "training_report.json"
    metadata_path = args.model_root / "model_metadata.json"
    model_path = args.model_root / "model.txt"
    snapshot_manifest = json.loads(
        snapshot_manifest_path.read_text(encoding="utf-8")
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if report.get("status") != "READY_FOR_FUTURE_ONLY_TEST":
        raise ValueError("development gate did not authorize future testing")
    if (
        snapshot_manifest.get("model_id") != MODEL_ID
        or metadata.get("model_id") != MODEL_ID
    ):
        raise ValueError("model ID mismatch")
    if snapshot_manifest.get("decision_date") != args.decision_date:
        raise ValueError("snapshot decision date mismatch")
    if snapshot_manifest.get("outcomes_attached") is not False:
        raise ValueError("future snapshot must not contain outcomes")
    if metadata.get("feature_columns") != list(FEATURE_COLUMNS):
        raise ValueError("model feature contract mismatch")
    if sha256(metadata_path) != snapshot_manifest[
        "model_metadata_sha256"
    ]:
        raise ValueError("snapshot was not built for this model artifact")
    if sha256(feature_path) != snapshot_manifest["artifact"]["sha256"]:
        raise ValueError("feature snapshot hash mismatch")
    if sha256(model_path) != metadata["model_sha256"]:
        raise ValueError("model artifact hash mismatch")
    if args.decision_date <= str(
        metadata["prospective_eligible_after_session"]
    ):
        raise ValueError(
            "decision date is not genuinely prospective relative to the "
            "model freeze"
        )

    frame = pd.read_csv(feature_path)
    day = frame[
        frame["market_date"].astype(str) == args.decision_date
    ].copy()
    if day.empty:
        raise ValueError(f"decision date is unavailable: {args.decision_date}")
    if day[list(FEATURE_COLUMNS)].isna().any().any():
        raise ValueError("future features contain missing values")
    booster = lgb.Booster(model_file=str(model_path))
    day["model_score"] = booster.predict(day[list(FEATURE_COLUMNS)])
    selected = select_latest(day, maximum_selections=10)
    now = datetime.now(timezone.utc).isoformat()
    observation = {
        "model_id": MODEL_ID,
        "decision_date": args.decision_date,
        "observed_at_utc": now,
        "source_manifest": str(snapshot_manifest_path.resolve()),
        "source_manifest_sha256": sha256(snapshot_manifest_path),
        "feature_snapshot_sha256": sha256(feature_path),
        "model_sha256": sha256(model_path),
        "horizon_sessions": HORIZON_SESSIONS,
        "entry": "next complete regular-session open",
        "exit": "twentieth subsequent regular-session close",
        "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
        "selection_policy": "top 20 percent, maximum 10",
        "selections": [
            {
                "rank": index,
                "symbol": str(row.symbol),
                "score": float(row.model_score),
            }
            for index, row in enumerate(selected.itertuples(), start=1)
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
            raise ValueError("future journal already contains this decision date")
        args.journal.parent.mkdir(parents=True, exist_ok=True)
        with args.journal.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(observation, sort_keys=True, separators=(",", ":"))
                + "\n"
            )

    args.output_root.mkdir(parents=True, exist_ok=True)
    output_json = args.output_root / "observation.json"
    output_csv = args.output_root / "ranking.csv"
    output_json.write_text(
        json.dumps(observation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    day.sort_values(
        ["model_score", "symbol"], ascending=[False, True]
    )[["market_date", "symbol", "model_score"]].to_csv(
        output_csv, index=False
    )
    print(
        json.dumps(
            {
                "status": observation["status"],
                "decision_date": args.decision_date,
                "selections": observation["selections"],
                "output": str(output_json),
                "journaled": args.journal is not None,
                "execution_decision": "AVOID",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
