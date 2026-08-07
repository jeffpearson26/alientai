from __future__ import annotations

"""Build the corrected, source-pure panel for the external LambdaRank lead."""

import argparse
import json
from pathlib import Path

from alientai_v2.research.external_lambdarank_20d import (
    CONTEXT_SYMBOL,
    EMBARGO_SESSIONS,
    FEATURE_COLUMNS,
    HORIZON_SESSIONS,
    MODEL_ID,
    PACKAGE_SHA256,
    RAW_FEATURES,
    ROUND_TRIP_COST_PCT,
    UNTRUSTED_JOBLIB_SHA256,
    build_panels,
    load_daily_universe,
    read_symbols,
    relevance_counts,
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
    parser.add_argument("--as-of-session")
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    source_roots = args.source_roots or [DEFAULT_PRIMARY, DEFAULT_SECONDARY]
    if args.output_root.exists() and any(args.output_root.iterdir()):
        raise ValueError(f"output root must be new or empty: {args.output_root}")
    if not all(path.exists() for path in source_roots):
        raise ValueError("one or more source roots are missing")

    symbols = read_symbols(args.symbols)
    daily, source_manifest = load_daily_universe(
        symbols, source_roots, as_of_session=args.as_of_session
    )
    result = build_panels(daily, symbols)
    args.output_root.mkdir(parents=True, exist_ok=True)
    feature_path = args.output_root / "feature_panel.csv.gz"
    labeled_path = args.output_root / "labeled_panel.csv.gz"
    result.feature_panel.to_csv(
        feature_path, index=False, compression="gzip"
    )
    result.labeled_panel.to_csv(
        labeled_path, index=False, compression="gzip"
    )
    manifest = {
        "status": "complete",
        "schema_version": 1,
        "model_id": MODEL_ID,
        "model_family": "LightGBM LambdaRank cross-sectional ranker",
        "external_package": {
            "source_zip": "D:/Downloads/lambdarank_ready.zip",
            "sha256": PACKAGE_SHA256,
            "claimed_sealed_result_status": (
                "EXPOSED_DEVELOPMENT_EVIDENCE_ONLY"
            ),
            "bundled_joblib": {
                "sha256": UNTRUSTED_JOBLIB_SHA256,
                "status": "QUARANTINED_NEVER_LOADED",
                "reason": (
                    "pickle/joblib is executable serialization and lacks an "
                    "audited provenance/schema manifest"
                ),
            },
        },
        "universe": {
            "candidate_count": len(symbols),
            "context_only": [CONTEXT_SYMBOL],
            "symbols_path": str(args.symbols.resolve()),
            "symbols_sha256": sha256(args.symbols),
            "fixed_contemporary_universe_bias": True,
        },
        "source_contract": {
            "provider": "Schwab",
            "roots": [str(path.resolve()) for path in source_roots],
            "date_mapping": (
                "per-file schema: datetime_ms/datetime_utc files use the "
                "stored U.S. session date; schwab_symbol/datetime files use "
                "the stored Pacific candle key plus one calendar day; each "
                "component records its offset"
            ),
            "as_of_session": args.as_of_session,
            "all_symbols_required": True,
            "silent_failures_allowed": False,
            "files": source_manifest,
        },
        "feature_contract": {
            "raw_features": list(RAW_FEATURES),
            "model_features": list(FEATURE_COLUMNS),
            "cross_sectional_ranks": "same decision date, full 120-name universe",
            "availability": "completed decision-session close only",
            "train_score_parity": "single shared feature implementation",
            "known_redundancy": (
                "rank_roc_10 equals rank_ret_10d and rank_ret_5d_vs_spy "
                "equals rank_ret_5d within a complete same-date cross-section"
            ),
        },
        "label_contract": {
            "decision": "after completed regular-session close",
            "entry": "next complete regular-session open",
            "exit": "twentieth subsequent regular-session close",
            "horizon_sessions": HORIZON_SESSIONS,
            "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
            "target": "five balanced within-date relevance buckets",
        },
        "validation_contract": {
            "whole_dates": True,
            "exact_label_interval_purge": True,
            "embargo_sessions": EMBARGO_SESSIONS,
            "folds": 5,
            "hyperparameters": "frozen from external proposal; no search",
            "historical_results": "development only",
            "sealed_test": "FUTURE_ONLY_NOT_STARTED",
        },
        "coverage": result.coverage,
        "relevance_counts": relevance_counts(result.labeled_panel),
        "artifacts": {
            "feature_panel": {
                "path": str(feature_path.resolve()),
                "sha256": sha256(feature_path),
                "rows": len(result.feature_panel),
            },
            "labeled_panel": {
                "path": str(labeled_path.resolve()),
                "sha256": sha256(labeled_path),
                "rows": len(result.labeled_panel),
            },
        },
        "research_only": True,
        "execution_decision": "AVOID",
    }
    manifest_path = args.output_root / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "complete",
                "feature_rows": len(result.feature_panel),
                "feature_dates": result.coverage["feature_dates"],
                "labeled_rows": len(result.labeled_panel),
                "labeled_dates": result.coverage["labeled_dates"],
                "last_feature_date": result.coverage["last_feature_date"],
                "last_labeled_date": result.coverage["last_labeled_date"],
                "manifest": str(manifest_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
