from __future__ import annotations

"""Build one outcome-free, exact-universe future barrier snapshot."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from alientai_v2.research.barrier_probability_model import (
    FEATURE_LOOKBACK,
    FEATURE_NAMES,
    adjusted_daily_candles,
    technical_features,
)


MODEL_ID = "barrier_probability_48_h10_alpha_vantage_v1_20260807"
FIRST_ELIGIBLE_DECISION_DATE = "2026-08-07"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_symbols(path: Path) -> list[str]:
    return [
        line.strip().upper()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def filename(symbol: str) -> str:
    return f"{symbol.replace('/', '-').replace('.', '-')}_daily.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--decision-date", required=True)
    parser.add_argument("--symbols", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.decision_date < FIRST_ELIGIBLE_DECISION_DATE:
        raise ValueError("decision date predates the frozen prospective window")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise FileExistsError("output directory must be empty")

    model_report_path = args.model_dir / "training_report.json"
    model_audit_path = args.model_dir / "independent_model_audit.json"
    model_report = json.loads(
        model_report_path.read_text(encoding="utf-8")
    )
    model_audit = json.loads(model_audit_path.read_text(encoding="utf-8"))
    if (
        model_report.get("model_id") != MODEL_ID
        or model_report.get("status")
        != "FROZEN_PENDING_PROSPECTIVE_REVIEW"
        or model_audit.get("model_id") != MODEL_ID
        or model_audit.get("status") != "PASS"
    ):
        raise ValueError("frozen model identity or audit mismatch")
    archive_audit_path = args.archive / "content_audit.json"
    archive_audit = json.loads(
        archive_audit_path.read_text(encoding="utf-8")
    )
    if (
        archive_audit.get("status") != "PASS"
        or archive_audit.get("provider") != "Alpha Vantage"
        or archive_audit.get("required_latest_date") != args.decision_date
    ):
        raise ValueError("exact adjusted-daily source audit is not ready")

    symbols = read_symbols(args.symbols)
    if symbols != model_report.get("universe"):
        raise ValueError("snapshot universe differs from frozen model universe")
    rows = []
    sources = {}
    for symbol in symbols:
        path = args.archive / filename(symbol)
        candles = adjusted_daily_candles(path, symbol)
        if candles[-1]["market_date"] != args.decision_date:
            raise ValueError(
                f"{symbol}: latest date {candles[-1]['market_date']} "
                f"is not {args.decision_date}"
            )
        if len(candles) < FEATURE_LOOKBACK:
            raise ValueError(f"{symbol}: insufficient feature history")
        rows.append(
            {
                "schema_version": 1,
                "model_id": MODEL_ID,
                "provider": "Alpha Vantage",
                "market_date": args.decision_date,
                "symbol": symbol,
                "decision_adjusted_close": float(candles[-1]["close"]),
                **technical_features(candles[-FEATURE_LOOKBACK:]),
                "outcomes_attached": False,
                "research_only": True,
                "execution_decision": "AVOID",
            }
        )
        sources[symbol] = {
            "path": str(path.resolve()),
            "sha256": sha256(path),
            "rows": len(candles),
            "latest_date": candles[-1]["market_date"],
        }
    if len(rows) != len(symbols) or len({row["symbol"] for row in rows}) != len(
        symbols
    ):
        raise ValueError("snapshot universe is incomplete")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = args.output_dir / "feature_snapshot.jsonl"
    with snapshot_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    manifest = {
        "status": "complete",
        "schema_version": 1,
        "model_id": MODEL_ID,
        "decision_date": args.decision_date,
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "provider": "Alpha Vantage",
        "candidate_count": len(symbols),
        "symbols_path": str(args.symbols.resolve()),
        "symbols_sha256": sha256(args.symbols),
        "feature_names": list(FEATURE_NAMES),
        "feature_lookback_sessions": FEATURE_LOOKBACK,
        "source_archive": str(args.archive.resolve()),
        "source_audit_path": str(archive_audit_path.resolve()),
        "source_audit_sha256": sha256(archive_audit_path),
        "source_files": sources,
        "model_report_path": str(model_report_path.resolve()),
        "model_report_sha256": sha256(model_report_path),
        "model_audit_path": str(model_audit_path.resolve()),
        "model_audit_sha256": sha256(model_audit_path),
        "artifact": {
            "path": str(snapshot_path.resolve()),
            "sha256": sha256(snapshot_path),
            "rows": len(rows),
        },
        "outcomes_attached": False,
        "research_only": True,
        "execution_decision": "AVOID",
    }
    manifest_path = args.output_dir / "snapshot_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "complete",
                "decision_date": args.decision_date,
                "rows": len(rows),
                "manifest": str(manifest_path),
                "execution_decision": "AVOID",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
