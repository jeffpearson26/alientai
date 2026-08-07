from __future__ import annotations

"""Independently audit the Alpha Vantage 20-session LambdaRank panel."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from alientai_v2.research.external_lambdarank_alpha_vantage_20d import (
    CONTEXT_SYMBOL,
    FEATURE_COLUMNS,
    HORIZON_SESSIONS,
    MINIMUM_CANDIDATES,
    MODEL_ID,
    ROUND_TRIP_COST_PCT,
    SOURCE_ENDPOINT,
    chronological_panel_split,
    load_alpha_vantage_daily_archive,
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
    require(manifest["status"] == "complete", "manifest is incomplete")
    require(manifest["model_id"] == MODEL_ID, "model ID mismatch")
    require(
        manifest["source_contract"]["provider"] == "Alpha Vantage"
        and manifest["source_contract"]["endpoint"] == SOURCE_ENDPOINT,
        "source contract mismatch",
    )
    require(
        manifest["universe"]["candidate_count"] == MINIMUM_CANDIDATES
        and manifest["universe"]["context_only"] == [CONTEXT_SYMBOL],
        "universe contract mismatch",
    )
    require(
        manifest["external_package"]["bundled_joblib"]["status"]
        == "QUARANTINED_NEVER_LOADED",
        "untrusted joblib was not quarantined",
    )

    feature_path = Path(manifest["artifacts"]["feature_panel"]["path"])
    labeled_path = Path(manifest["artifacts"]["labeled_panel"]["path"])
    development_path = Path(
        manifest["artifacts"]["development_panel"]["path"]
    )
    sealed_path = Path(manifest["artifacts"]["sealed_test_panel"]["path"])
    require(
        sha256(feature_path)
        == manifest["artifacts"]["feature_panel"]["sha256"],
        "feature hash mismatch",
    )
    require(
        sha256(labeled_path)
        == manifest["artifacts"]["labeled_panel"]["sha256"],
        "labeled hash mismatch",
    )
    require(
        sha256(development_path)
        == manifest["artifacts"]["development_panel"]["sha256"],
        "development hash mismatch",
    )
    require(
        sha256(sealed_path)
        == manifest["artifacts"]["sealed_test_panel"]["sha256"],
        "sealed-test hash mismatch",
    )
    feature = pd.read_csv(feature_path, low_memory=False)
    labeled = pd.read_csv(labeled_path, low_memory=False)
    development = pd.read_csv(development_path, low_memory=False)
    sealed = pd.read_csv(sealed_path, low_memory=False)
    for name, frame in (("feature", feature), ("labeled", labeled)):
        require(
            not frame.duplicated(["market_date", "symbol"]).any(),
            f"{name} has duplicate keys",
        )
        require(
            frame.groupby("market_date")["symbol"]
            .nunique()
            .eq(MINIMUM_CANDIDATES)
            .all(),
            f"{name} has incomplete dates",
        )
        ranks = frame[list(FEATURE_COLUMNS)].to_numpy(dtype=float)
        require(
            np.isfinite(ranks).all()
            and (ranks >= 0.0).all()
            and (ranks <= 1.0).all(),
            f"{name} has invalid ranked features",
        )
    relevance = labeled.groupby("market_date")["relevance"].apply(
        lambda values: set(values.astype(int))
    )
    require(
        all(values == {0, 1, 2, 3, 4} for values in relevance),
        "relevance buckets are incomplete",
    )
    reproduced_development, reproduced_sealed, split = (
        chronological_panel_split(labeled)
    )
    require(
        reproduced_development.equals(development),
        "development split is not reproducible",
    )
    require(
        reproduced_sealed.equals(sealed),
        "sealed split is not reproducible",
    )
    require(
        split == manifest["validation_contract"]["split"],
        "split metadata is not reproducible",
    )
    require(
        development["label_exit_date"].astype(str).max()
        < sealed["market_date"].astype(str).min(),
        "development label interval overlaps sealed test",
    )

    symbols = read_symbols(Path(manifest["universe"]["symbols_path"]))
    source = manifest["source_contract"]
    daily, reproduced = load_alpha_vantage_daily_archive(
        Path(source["archive"]),
        symbols,
        as_of_session=source["as_of_session"],
    )
    source_reproducible = {
        key: value
        for key, value in source.items()
        if key
        not in {
            "all_symbols_required",
            "silent_failures_allowed",
            "schwab_substitution_allowed",
        }
    }
    require(
        reproduced == source_reproducible,
        "source manifest is not reproducible",
    )

    calendar = [
        str(row["market_date"]) for row in daily[CONTEXT_SYMBOL]
    ]
    positions = {market_date: index for index, market_date in enumerate(calendar)}
    label_dates = labeled[
        ["market_date", "label_entry_date", "label_exit_date"]
    ].drop_duplicates()
    for row in label_dates.itertuples(index=False):
        index = positions[str(row.market_date)]
        require(
            str(row.label_entry_date) == calendar[index + 1],
            f"entry date mismatch for {row.market_date}",
        )
        require(
            str(row.label_exit_date) == calendar[index + HORIZON_SESSIONS],
            f"exit date mismatch for {row.market_date}",
        )

    maximum_label_error = 0.0
    for symbol, group in labeled.groupby("symbol", sort=True):
        by_date = {
            str(row["market_date"]): row for row in daily[symbol]
        }
        for row in group.itertuples(index=False):
            entry = float(by_date[str(row.label_entry_date)]["open"])
            exit_price = float(by_date[str(row.label_exit_date)]["close"])
            expected = (
                (exit_price / entry - 1.0) * 100.0
                - ROUND_TRIP_COST_PCT
            )
            maximum_label_error = max(
                maximum_label_error,
                abs(expected - float(row.label_net_return_pct)),
            )
    require(maximum_label_error < 1e-9, "label return mismatch")

    folds = purged_folds(labeled, n_splits=5)
    date_rows = labeled[
        ["market_date", "label_entry_date", "label_exit_date"]
    ].drop_duplicates()
    for fold in folds:
        validation = date_rows[
            date_rows["market_date"].isin(fold.validation_dates)
        ]
        train = date_rows[date_rows["market_date"].isin(fold.train_dates)]
        start = str(validation["market_date"].min())
        end = str(validation["label_exit_date"].max())
        overlap = (
            (train["label_entry_date"] <= end)
            & (train["label_exit_date"] >= start)
        )
        require(not overlap.any(), f"label overlap in fold {fold.fold}")
        require(
            set(fold.train_dates).isdisjoint(fold.embargo_dates),
            f"embargo leak in fold {fold.fold}",
        )

    report = {
        "status": "PASS",
        "model_id": MODEL_ID,
        "manifest_sha256": sha256(manifest_path),
        "feature_rows": len(feature),
        "feature_dates": int(feature["market_date"].nunique()),
        "labeled_rows": len(labeled),
        "labeled_dates": int(labeled["market_date"].nunique()),
        "development_rows": len(development),
        "development_dates": int(
            development["market_date"].nunique()
        ),
        "sealed_rows": len(sealed),
        "sealed_dates": int(sealed["market_date"].nunique()),
        "sealed_first_date": str(sealed["market_date"].min()),
        "sealed_last_date": str(sealed["market_date"].max()),
        "candidate_count_each_date": MINIMUM_CANDIDATES,
        "first_labeled_date": str(labeled["market_date"].min()),
        "last_labeled_date": str(labeled["market_date"].max()),
        "maximum_label_error": maximum_label_error,
        "source_provider": "Alpha Vantage",
        "source_archive_audit_sha256": source["content_audit_sha256"],
        "bundled_joblib": "QUARANTINED_NEVER_LOADED",
        "sealed_test": "UNLOADED",
        "research_only": True,
        "execution_decision": "AVOID",
    }
    output = args.report or (
        args.panel_root / "independent_content_audit.json"
    )
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
