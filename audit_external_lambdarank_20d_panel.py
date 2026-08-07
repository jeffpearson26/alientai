from __future__ import annotations

"""Independently audit the corrected external LambdaRank panel."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from alientai_v2.research.external_lambdarank_20d import (
    CONTEXT_SYMBOL,
    FEATURE_COLUMNS,
    HORIZON_SESSIONS,
    MINIMUM_CANDIDATES,
    ROUND_TRIP_COST_PCT,
    load_daily_universe,
    purged_folds,
    read_symbols,
    sha256,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-root", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    manifest_path = args.panel_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    feature_path = Path(manifest["artifacts"]["feature_panel"]["path"])
    labeled_path = Path(manifest["artifacts"]["labeled_panel"]["path"])

    require(manifest["status"] == "complete", "manifest is not complete")
    require(
        manifest["universe"]["candidate_count"] == MINIMUM_CANDIDATES,
        "candidate universe count mismatch",
    )
    require(
        manifest["universe"]["context_only"] == [CONTEXT_SYMBOL],
        "SPY context contract mismatch",
    )
    require(
        manifest["source_contract"]["provider"] == "Schwab",
        "source provider mismatch",
    )
    require(
        manifest["external_package"]["bundled_joblib"]["status"]
        == "QUARANTINED_NEVER_LOADED",
        "untrusted joblib is not quarantined",
    )
    require(
        sha256(feature_path)
        == manifest["artifacts"]["feature_panel"]["sha256"],
        "feature panel hash mismatch",
    )
    require(
        sha256(labeled_path)
        == manifest["artifacts"]["labeled_panel"]["sha256"],
        "labeled panel hash mismatch",
    )

    feature = pd.read_csv(feature_path, low_memory=False)
    labeled = pd.read_csv(labeled_path, low_memory=False)
    for name, frame in (("feature", feature), ("labeled", labeled)):
        require(
            not frame.duplicated(["market_date", "symbol"]).any(),
            f"{name} panel has duplicate symbol-dates",
        )
        require(
            frame.groupby("market_date")["symbol"].nunique().eq(
                MINIMUM_CANDIDATES
            ).all(),
            f"{name} panel has incomplete dates",
        )
        require(
            not frame[list(FEATURE_COLUMNS)].isna().any().any(),
            f"{name} panel has missing model features",
        )
        require(
            np.isfinite(
                frame[list(FEATURE_COLUMNS)].to_numpy(dtype=float)
            ).all(),
            f"{name} panel has non-finite model features",
        )
        require(
            (
                frame[list(FEATURE_COLUMNS)].to_numpy(dtype=float) >= 0.0
            ).all()
            and (
                frame[list(FEATURE_COLUMNS)].to_numpy(dtype=float) <= 1.0
            ).all(),
            f"{name} ranks are outside [0, 1]",
        )

    relevance_sets = labeled.groupby("market_date")["relevance"].apply(
        lambda values: set(values.astype(int))
    )
    require(
        all(values == {0, 1, 2, 3, 4} for values in relevance_sets),
        "one or more dates lacks all five relevance buckets",
    )

    sources = manifest["source_contract"]["files"]
    for symbol, details in sources.items():
        for component in details["components"]:
            require(
                sha256(Path(component["path"])) == component["sha256"],
                f"source hash mismatch for {symbol}",
            )

    symbols = read_symbols(Path(manifest["universe"]["symbols_path"]))
    source_roots = [
        Path(value) for value in manifest["source_contract"]["roots"]
    ]
    daily, reproduced_sources = load_daily_universe(
        symbols,
        source_roots,
        as_of_session=manifest["source_contract"]["as_of_session"],
    )
    require(
        reproduced_sources == sources,
        "source selection and rejection manifest is not reproducible",
    )
    spy_rows = daily[CONTEXT_SYMBOL]
    spy_calendar = [str(row["market_date"]) for row in spy_rows]
    spy_positions = {
        market_date: index
        for index, market_date in enumerate(spy_calendar)
    }
    label_dates = labeled[
        ["market_date", "label_entry_date", "label_exit_date"]
    ].drop_duplicates()
    for row in label_dates.itertuples(index=False):
        decision_index = spy_positions[str(row.market_date)]
        require(
            str(row.label_entry_date)
            == spy_calendar[decision_index + 1],
            f"entry date mismatch for {row.market_date}",
        )
        require(
            str(row.label_exit_date)
            == spy_calendar[decision_index + HORIZON_SESSIONS],
            f"exit date mismatch for {row.market_date}",
        )

    maximum_label_error = 0.0
    for symbol, group in labeled.groupby("symbol", sort=True):
        rows = daily[symbol]
        by_date = {str(row["market_date"]): row for row in rows}
        for row in group.itertuples(index=False):
            entry = float(by_date[str(row.label_entry_date)]["open"])
            exit_price = float(by_date[str(row.label_exit_date)]["close"])
            expected = (
                (exit_price / entry - 1.0) * 100.0
                - ROUND_TRIP_COST_PCT
            )
            error = abs(expected - float(row.label_net_return_pct))
            maximum_label_error = max(maximum_label_error, error)
    require(maximum_label_error < 1e-9, "label return mismatch")

    folds = purged_folds(labeled, n_splits=5)
    date_rows = labeled[
        ["market_date", "label_entry_date", "label_exit_date"]
    ].drop_duplicates()
    fold_summary = []
    for fold in folds:
        validation = date_rows[
            date_rows["market_date"].isin(fold.validation_dates)
        ]
        train = date_rows[date_rows["market_date"].isin(fold.train_dates)]
        interval_start = str(validation["market_date"].min())
        interval_end = str(validation["label_exit_date"].max())
        overlap = (
            (train["label_entry_date"] <= interval_end)
            & (train["label_exit_date"] >= interval_start)
        )
        require(not overlap.any(), f"label overlap in fold {fold.fold}")
        require(
            set(fold.train_dates).isdisjoint(fold.embargo_dates),
            f"embargo leak in fold {fold.fold}",
        )
        fold_summary.append(
            {
                "fold": fold.fold,
                "train_dates": len(fold.train_dates),
                "validation_dates": len(fold.validation_dates),
                "purged_dates": len(fold.purged_dates),
                "embargo_dates": len(fold.embargo_dates),
            }
        )

    rejected = {
        symbol: details["rejected_row_count"]
        for symbol, details in sources.items()
        if details["rejected_row_count"]
    }
    fallback = {
        symbol: {
            "source_mode": details["source_mode"],
            "source_root_priority_index": details[
                "source_root_priority_index"
            ],
            "components": details["components"],
        }
        for symbol, details in sources.items()
        if details["source_root_priority_index"] > 0
        or details["source_mode"] != "SINGLE_PRIORITY_FILE"
    }
    report = {
        "status": "PASS",
        "panel_root": str(args.panel_root.resolve()),
        "manifest_sha256": sha256(manifest_path),
        "feature_rows": len(feature),
        "feature_dates": int(feature["market_date"].nunique()),
        "labeled_rows": len(labeled),
        "labeled_dates": int(labeled["market_date"].nunique()),
        "candidate_count_each_date": MINIMUM_CANDIDATES,
        "first_labeled_date": str(labeled["market_date"].min()),
        "last_labeled_date": str(labeled["market_date"].max()),
        "maximum_label_error": maximum_label_error,
        "folds": fold_summary,
        "source_rejection_counts": rejected,
        "same_provider_fallbacks": fallback,
        "bundled_joblib": "QUARANTINED_NEVER_LOADED",
        "sealed_test": "FUTURE_ONLY_NOT_STARTED",
        "research_only": True,
        "execution_decision": "AVOID",
    }
    report_path = args.report or (
        args.panel_root / "independent_content_audit.json"
    )
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
