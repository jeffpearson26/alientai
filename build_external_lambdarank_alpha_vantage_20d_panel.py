from __future__ import annotations

"""Build the isolated Alpha Vantage 20-session LambdaRank panel."""

import argparse
import json
from pathlib import Path

from alientai_v2.research.external_lambdarank_alpha_vantage_20d import (
    CONTEXT_SYMBOL,
    EMBARGO_SESSIONS,
    FEATURE_COLUMNS,
    HORIZON_SESSIONS,
    MODEL_ID,
    PACKAGE_SHA256,
    RAW_FEATURES,
    ROUND_TRIP_COST_PCT,
    SOURCE_ENDPOINT,
    SOURCE_OUTPUTSIZE,
    SEALED_TEST_FRACTION,
    UNTRUSTED_JOBLIB_SHA256,
    build_panels,
    chronological_panel_split,
    load_alpha_vantage_daily_archive,
    read_symbols,
    relevance_counts,
    sha256,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_SYMBOLS = (
    ROOT / "research_universes" / "external_lambdarank_120_20260806.txt"
)
DEFAULT_ARCHIVE = Path(
    "D:/AlientAI/Data/AlphaVantage_2026/"
    "external_lambdarank_120_plus_spy_adjusted_daily_full_20260806"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", type=Path, default=DEFAULT_SYMBOLS)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--as-of-session", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    if args.output_root.exists() and any(args.output_root.iterdir()):
        raise ValueError(f"output root must be new or empty: {args.output_root}")

    symbols = read_symbols(args.symbols)
    daily, source_manifest = load_alpha_vantage_daily_archive(
        args.archive, symbols, as_of_session=args.as_of_session
    )
    result = build_panels(daily, symbols)
    development, sealed, split = chronological_panel_split(
        result.labeled_panel,
        sealed_fraction=SEALED_TEST_FRACTION,
        boundary_embargo_sessions=EMBARGO_SESSIONS,
    )
    args.output_root.mkdir(parents=True, exist_ok=True)
    feature_path = args.output_root / "feature_panel.csv.gz"
    labeled_path = args.output_root / "labeled_panel.csv.gz"
    development_path = args.output_root / "development_panel.csv.gz"
    sealed_path = args.output_root / "sealed_test_panel.csv.gz"
    result.feature_panel.to_csv(feature_path, index=False, compression="gzip")
    result.labeled_panel.to_csv(labeled_path, index=False, compression="gzip")
    development.to_csv(
        development_path, index=False, compression="gzip"
    )
    sealed.to_csv(sealed_path, index=False, compression="gzip")

    manifest = {
        "status": "complete",
        "schema_version": 1,
        "model_id": MODEL_ID,
        "model_family": "LightGBM LambdaRank cross-sectional ranker",
        "source_clone": "NEW_ALPHA_VANTAGE_MODEL_NO_SCHWAB_EVIDENCE",
        "external_package": {
            "source_zip": "D:/Downloads/lambdarank_ready.zip",
            "sha256": PACKAGE_SHA256,
            "bundled_joblib": {
                "sha256": UNTRUSTED_JOBLIB_SHA256,
                "status": "QUARANTINED_NEVER_LOADED",
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
            **source_manifest,
            "provider": "Alpha Vantage",
            "endpoint": SOURCE_ENDPOINT,
            "outputsize": SOURCE_OUTPUTSIZE,
            "all_symbols_required": True,
            "silent_failures_allowed": False,
            "schwab_substitution_allowed": False,
        },
        "feature_contract": {
            "raw_features": list(RAW_FEATURES),
            "model_features": list(FEATURE_COLUMNS),
            "cross_sectional_ranks": (
                "same decision date, exact full 120-name universe"
            ),
            "availability": "completed decision-session close only",
            "train_score_parity": "single shared feature implementation",
            "known_redundancy": (
                "rank_roc_10 equals rank_ret_10d and rank_ret_5d_vs_spy "
                "equals rank_ret_5d within a complete cross-section"
            ),
        },
        "label_contract": {
            "decision": "after completed regular-session close",
            "entry": "next complete regular-session split-adjusted open",
            "exit": "twentieth subsequent regular-session adjusted close",
            "horizon_sessions": HORIZON_SESSIONS,
            "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
            "target": "five balanced within-date relevance buckets",
        },
        "validation_contract": {
            "development_fraction": 0.80,
            "sealed_test_fraction": 0.20,
            "whole_dates": True,
            "boundary_embargo_sessions": EMBARGO_SESSIONS,
            "exact_label_interval_purge": True,
            "development_folds": 5,
            "fold_embargo_sessions": EMBARGO_SESSIONS,
            "hyperparameters": "fixed before sealed-test access",
            "sealed_test": "UNLOADED",
            "split": split,
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
            "development_panel": {
                "path": str(development_path.resolve()),
                "sha256": sha256(development_path),
                "rows": len(development),
                "dates": int(development["market_date"].nunique()),
            },
            "sealed_test_panel": {
                "path": str(sealed_path.resolve()),
                "sha256": sha256(sealed_path),
                "rows": len(sealed),
                "dates": int(sealed["market_date"].nunique()),
                "status": "SEALED_UNLOADED",
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
                "model_id": MODEL_ID,
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
