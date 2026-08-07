from __future__ import annotations

"""Build one immutable, point-in-time feature snapshot for future testing."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from alientai_v2.research.external_lambdarank_20d import (
    CONTEXT_SYMBOL,
    FEATURE_COLUMNS,
    MINIMUM_CANDIDATES,
    MODEL_ID,
    PACKAGE_SHA256,
    RAW_FEATURES,
    UNTRUSTED_JOBLIB_SHA256,
    build_panels,
    load_daily_universe,
    read_symbols,
    sha256,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_SYMBOLS = (
    ROOT / "research_universes" / "external_lambdarank_120_20260806.txt"
)
DEFAULT_PRIMARY = ROOT / "data_v2" / "sp500_daily_schwab_max_history"
DEFAULT_SECONDARY = ROOT / "data_v2" / "daily_schwab_max_history"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", type=Path, default=DEFAULT_SYMBOLS)
    parser.add_argument(
        "--source-root", type=Path, action="append", dest="source_roots"
    )
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--decision-date", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    if args.output_root.exists() and any(args.output_root.iterdir()):
        raise ValueError(f"output root must be new or empty: {args.output_root}")

    metadata_path = args.model_root / "model_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("model_id") != MODEL_ID:
        raise ValueError("model ID mismatch")
    if args.decision_date <= str(
        metadata["prospective_eligible_after_session"]
    ):
        raise ValueError(
            "snapshot date is not genuinely prospective relative to freeze"
        )

    source_roots = args.source_roots or [DEFAULT_PRIMARY, DEFAULT_SECONDARY]
    if not all(path.exists() for path in source_roots):
        raise ValueError("one or more source roots are missing")
    symbols = read_symbols(args.symbols)
    daily, source_manifest = load_daily_universe(
        symbols,
        source_roots,
        as_of_session=args.decision_date,
    )
    stale = {
        symbol: details["last_market_date"]
        for symbol, details in source_manifest.items()
        if details["last_market_date"] != args.decision_date
    }
    if stale:
        raise ValueError(
            f"snapshot is stale or incomplete for decision date "
            f"{args.decision_date}: {stale}"
        )

    panel = build_panels(daily, symbols).feature_panel
    snapshot = panel[
        panel["market_date"].astype(str) == args.decision_date
    ].copy()
    if (
        len(snapshot) != MINIMUM_CANDIDATES
        or snapshot["symbol"].nunique() != MINIMUM_CANDIDATES
    ):
        raise ValueError("decision-date feature cross-section is incomplete")
    if snapshot[list(FEATURE_COLUMNS)].isna().any().any():
        raise ValueError("decision-date model features are unavailable")

    args.output_root.mkdir(parents=True, exist_ok=True)
    snapshot_path = args.output_root / "feature_snapshot.csv"
    snapshot.to_csv(snapshot_path, index=False)
    manifest = {
        "status": "complete",
        "schema_version": 1,
        "model_id": MODEL_ID,
        "decision_date": args.decision_date,
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_count": MINIMUM_CANDIDATES,
        "context_only": [CONTEXT_SYMBOL],
        "symbols_path": str(args.symbols.resolve()),
        "symbols_sha256": sha256(args.symbols),
        "model_metadata_path": str(metadata_path.resolve()),
        "model_metadata_sha256": sha256(metadata_path),
        "prospective_eligible_after_session": metadata[
            "prospective_eligible_after_session"
        ],
        "source_contract": {
            "provider": "Schwab",
            "roots": [str(path.resolve()) for path in source_roots],
            "as_of_session": args.decision_date,
            "all_symbols_current_and_required": True,
            "files": source_manifest,
        },
        "feature_contract": {
            "raw_features": list(RAW_FEATURES),
            "model_features": list(FEATURE_COLUMNS),
            "cross_sectional_ranks": "same date, exact 120-name universe",
            "availability": "completed decision-session close only",
        },
        "artifact": {
            "path": str(snapshot_path.resolve()),
            "sha256": sha256(snapshot_path),
            "rows": len(snapshot),
        },
        "external_package": {
            "sha256": PACKAGE_SHA256,
            "bundled_joblib_sha256": UNTRUSTED_JOBLIB_SHA256,
            "bundled_joblib_status": "QUARANTINED_NEVER_LOADED",
        },
        "outcomes_attached": False,
        "research_only": True,
        "execution_decision": "AVOID",
    }
    manifest_path = args.output_root / "snapshot_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "complete",
                "decision_date": args.decision_date,
                "rows": len(snapshot),
                "manifest": str(manifest_path),
                "execution_decision": "AVOID",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
