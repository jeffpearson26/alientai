from __future__ import annotations

"""Leakage-safe preparation helpers for Jeff's external LambdaRank package."""

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from alientai_v2.research.cross_sectional_technical_5d import (
    technical_features,
)
from alientai_v2.research.multiresolution_cross_sectional import (
    add_cross_sectional_ranks,
    date_spearman,
    purged_date_folds,
)


MODEL_ID = "external_lambdarank_120_h20_corrected_v2_20260806"
HORIZON_SESSIONS = 20
EMBARGO_SESSIONS = 20
ROUND_TRIP_COST_PCT = 0.25
CONTEXT_SYMBOL = "SPY"
MINIMUM_CANDIDATES = 120
PACKAGE_SHA256 = (
    "dcfcd7e3403d93842ec732b2b8a46d99cf71fe8e15176ff7c1041299d94aff4d"
)
UNTRUSTED_JOBLIB_SHA256 = (
    "44ad9f72ed26f749c759977fba082e5d7ca656cc36b5d71e7b75b345534c1e91"
)

RAW_FEATURES = (
    "ret_5d",
    "ret_10d",
    "roc_10",
    "rsi_14",
    "stoch_k",
    "cci_20",
    "rel_volume",
    "bb_pct",
    "atr_pct",
    "dist_ema_10",
    "dist_ema_20",
    "macd_hist",
    "ret_5d_vs_spy",
)
FEATURE_COLUMNS = tuple(f"rank_{name}" for name in RAW_FEATURES)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_symbols(path: Path) -> list[str]:
    symbols = [
        line.strip().upper()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    if len(symbols) != MINIMUM_CANDIDATES:
        raise ValueError(
            f"expected exactly {MINIMUM_CANDIDATES} candidates; got "
            f"{len(symbols)}"
        )
    if len(set(symbols)) != len(symbols):
        raise ValueError("candidate universe contains duplicates")
    if CONTEXT_SYMBOL in symbols:
        raise ValueError("SPY must remain context-only")
    return symbols


def _symbol_file_candidates(root: Path, symbol: str) -> list[Path]:
    aliases = [
        symbol,
        symbol.replace("-", "."),
        symbol.replace("-", "_"),
    ]
    return [root / f"{alias}_schwab_1d_max.csv" for alias in aliases]


def _available_symbol_files(
    symbol: str, source_roots: Sequence[Path]
) -> list[tuple[int, Path]]:
    available: list[tuple[int, Path]] = []
    for root_index, root in enumerate(source_roots):
        matches = [
            candidate.resolve()
            for candidate in _symbol_file_candidates(root, symbol)
            if candidate.exists()
        ]
        unique = list(dict.fromkeys(matches))
        if len(unique) > 1:
            raise ValueError(
                f"{symbol} has multiple aliases in source root {root}"
            )
        if unique:
            available.append((root_index, unique[0]))
    return available


def resolve_symbol_file(
    symbol: str, source_roots: Sequence[Path]
) -> Path:
    # Roots are an explicit priority order. Use the first root containing the
    # symbol and consult later roots only as same-provider fallbacks. This
    # avoids treating an intentional mirror/fallback copy as a source splice.
    available = _available_symbol_files(symbol, source_roots)
    if available:
        return available[0][1]
    raise ValueError(f"{symbol} has no Schwab source file")


def schwab_date_offset_days(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        fields = set(csv.DictReader(handle).fieldnames or [])
    if {"datetime_ms", "datetime_utc"}.issubset(fields):
        return 0
    if {"schwab_symbol", "datetime"}.issubset(fields):
        return 1
    raise ValueError(f"{path} has an unknown Schwab daily date schema")


def load_schwab_daily(
    path: Path,
    *,
    symbol: str,
    as_of_session: str | None = None,
    minimum_rows: int = 100,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    rows: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    date_offset_days = schwab_date_offset_days(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"date", "open", "high", "low", "close", "volume"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(
                f"{path} missing columns {sorted(required - set(reader.fieldnames or []))}"
            )
        for source in reader:
            stored = pd.Timestamp(str(source["date"]))
            market_date = (
                stored + pd.Timedelta(days=date_offset_days)
            ).date().isoformat()
            if as_of_session is not None and market_date > as_of_session:
                continue
            row = {
                "symbol": symbol,
                "market_date": market_date,
                "open": float(source["open"]),
                "high": float(source["high"]),
                "low": float(source["low"]),
                "close": float(source["close"]),
                "volume": float(source["volume"]),
            }
            prices = [row[name] for name in ("open", "high", "low", "close")]
            if (
                any(not np.isfinite(value) or value <= 0.0 for value in prices)
                or not np.isfinite(row["volume"])
                or row["volume"] < 0.0
                or row["high"] < max(row["open"], row["close"], row["low"])
                or row["low"] > min(row["open"], row["close"], row["high"])
            ):
                # Exclude the entire symbol-date from the cross-section. The
                # panel builder subsequently keeps only dates with all 120
                # candidates, so a malformed source candle can never become a
                # feature or label. Preserve every rejection in the manifest.
                rejected.append(
                    {
                        "market_date": market_date,
                        "reason": "INVALID_OHLCV_ENVELOPE_OR_VALUE",
                    }
                )
                continue
            rows.append(row)
    date_counts: dict[str, int] = {}
    for row in rows:
        key = str(row["market_date"])
        date_counts[key] = date_counts.get(key, 0) + 1
    duplicate_dates = {
        market_date
        for market_date, count in date_counts.items()
        if count > 1
    }
    if duplicate_dates:
        rows = [
            row
            for row in rows
            if str(row["market_date"]) not in duplicate_dates
        ]
        rejected.extend(
            {
                "market_date": market_date,
                "reason": "DUPLICATE_SOURCE_SESSION_ALL_ROWS_EXCLUDED",
            }
            for market_date in sorted(duplicate_dates)
        )
    rows.sort(key=lambda row: str(row["market_date"]))
    dates = [str(row["market_date"]) for row in rows]
    if len(rows) < minimum_rows or len(dates) != len(set(dates)):
        raise ValueError(f"{symbol} has insufficient or duplicate daily rows")
    return rows, rejected


def _rows_match(
    left: Mapping[str, Any], right: Mapping[str, Any]
) -> bool:
    return all(
        np.isclose(
            float(left[name]),
            float(right[name]),
            rtol=0.0,
            atol=1e-9,
        )
        for name in ("open", "high", "low", "close", "volume")
    )


def load_daily_universe(
    symbols: Sequence[str],
    source_roots: Sequence[Path],
    *,
    as_of_session: str | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    daily: dict[str, list[dict[str, Any]]] = {}
    sources: dict[str, dict[str, Any]] = {}
    for symbol in [*symbols, CONTEXT_SYMBOL]:
        available = _available_symbol_files(symbol, source_roots)
        if not available:
            raise ValueError(f"{symbol} has no Schwab source file")
        loaded_components = []
        for root_index, path in available:
            rows, rejected = load_schwab_daily(
                path,
                symbol=symbol,
                as_of_session=as_of_session,
                minimum_rows=1,
            )
            loaded_components.append(
                {
                    "root_priority_index": root_index,
                    "path": path,
                    "rows": rows,
                    "rejected": rejected,
                    "date_offset_days": schwab_date_offset_days(path),
                }
            )
        if len(loaded_components[0]["rows"]) >= 100:
            used_components = [loaded_components[0]]
            rows = list(loaded_components[0]["rows"])
            source_mode = "SINGLE_PRIORITY_FILE"
        else:
            used_components = loaded_components
            merged: dict[str, dict[str, Any]] = {}
            for component in used_components:
                for row in component["rows"]:
                    market_date = str(row["market_date"])
                    existing = merged.get(market_date)
                    if existing is not None and not _rows_match(
                        existing, row
                    ):
                        raise ValueError(
                            f"{symbol} has conflicting same-provider "
                            f"candles for {market_date}"
                        )
                    merged[market_date] = row
            rows = [merged[key] for key in sorted(merged)]
            if len(rows) < 100:
                raise ValueError(
                    f"{symbol} has insufficient merged Schwab history"
                )
            source_mode = "SAME_PROVIDER_COMPONENT_MERGE"
        rejected = [
            {
                **row,
                "component_path": str(component["path"]),
            }
            for component in used_components
            for row in component["rejected"]
        ]
        daily[symbol] = rows
        sources[symbol] = {
            "source_mode": source_mode,
            "source_root_priority_index": min(
                int(component["root_priority_index"])
                for component in used_components
            ),
            "components": [
                {
                    "root_priority_index": int(
                        component["root_priority_index"]
                    ),
                    "path": str(component["path"]),
                    "sha256": sha256(component["path"]),
                    "date_offset_days": int(
                        component["date_offset_days"]
                    ),
                    "usable_rows": len(component["rows"]),
                    "rejected_row_count": len(component["rejected"]),
                }
                for component in used_components
            ],
            "rows": len(daily[symbol]),
            "first_market_date": str(daily[symbol][0]["market_date"]),
            "last_market_date": str(daily[symbol][-1]["market_date"]),
            "rejected_rows": rejected,
            "rejected_row_count": len(rejected),
        }
    return daily, sources


def _raw_features(
    candles: Sequence[Mapping[str, Any]], *, spy_return_5d: float
) -> dict[str, float]:
    source = technical_features(candles)
    values = {
        "ret_5d": source["x5_return_5d_pct"],
        "ret_10d": source["x5_return_10d_pct"],
        "roc_10": source["x5_roc_10d_pct"],
        "rsi_14": source["x5_rsi_14"],
        "stoch_k": source["x5_stochastic_k_14"],
        "cci_20": source["x5_cci_20"],
        "rel_volume": source["x5_relative_volume_20d"],
        "bb_pct": source["x5_bollinger_pct_b_20"],
        "atr_pct": source["x5_atr_14_pct"],
        "dist_ema_10": source["x5_distance_ema_10_pct"],
        "dist_ema_20": source["x5_distance_ema_20_pct"],
        "macd_hist": source["x5_macd_histogram_pct"],
        "ret_5d_vs_spy": (
            float(source["x5_return_5d_pct"]) - spy_return_5d
        ),
    }
    if any(value is None or not np.isfinite(float(value)) for value in values.values()):
        raise ValueError("feature row contains unavailable or non-finite values")
    return {name: float(value) for name, value in values.items()}


@dataclass(frozen=True)
class PanelBuild:
    feature_panel: pd.DataFrame
    labeled_panel: pd.DataFrame
    coverage: dict[str, Any]


def build_panels(
    daily: Mapping[str, Sequence[Mapping[str, Any]]],
    symbols: Sequence[str],
) -> PanelBuild:
    expected = set(symbols) | {CONTEXT_SYMBOL}
    if set(daily) != expected:
        raise ValueError(
            f"daily keys do not match frozen universe: "
            f"missing={sorted(expected - set(daily))}, "
            f"extra={sorted(set(daily) - expected)}"
        )
    positions = {
        symbol: {
            str(row["market_date"]): index
            for index, row in enumerate(candles)
        }
        for symbol, candles in daily.items()
    }
    calendar = [
        str(row["market_date"]) for row in daily[CONTEXT_SYMBOL]
    ]
    feature_rows: list[dict[str, Any]] = []
    incomplete_dates: dict[str, str] = {}
    for official_index, market_date in enumerate(calendar):
        if any(market_date not in positions[symbol] for symbol in expected):
            incomplete_dates[market_date] = "missing_decision_session"
            continue
        if any(positions[symbol][market_date] < 59 for symbol in expected):
            continue
        spy_index = positions[CONTEXT_SYMBOL][market_date]
        spy_window = daily[CONTEXT_SYMBOL][
            max(0, spy_index + 1 - 90) : spy_index + 1
        ]
        spy_technical = technical_features(spy_window)
        spy_return_5d = float(spy_technical["x5_return_5d_pct"])
        entry_date = (
            calendar[official_index + 1]
            if official_index + 1 < len(calendar)
            else None
        )
        exit_date = (
            calendar[official_index + HORIZON_SESSIONS]
            if official_index + HORIZON_SESSIONS < len(calendar)
            else None
        )
        date_rows: list[dict[str, Any]] = []
        label_available = entry_date is not None and exit_date is not None
        if label_available and any(
            entry_date not in positions[symbol]
            or exit_date not in positions[symbol]
            for symbol in symbols
        ):
            label_available = False
        for symbol in symbols:
            index = positions[symbol][market_date]
            candles = daily[symbol]
            raw = _raw_features(
                candles[max(0, index + 1 - 90) : index + 1],
                spy_return_5d=spy_return_5d,
            )
            source_technical = technical_features(
                candles[max(0, index + 1 - 90) : index + 1]
            )
            row: dict[str, Any] = {
                "symbol": symbol,
                "market_date": market_date,
                "decision_close": float(candles[index]["close"]),
                "average_dollar_volume_20d": float(
                    source_technical["x5_average_dollar_volume_20d"]
                ),
                **raw,
            }
            if label_available:
                entry = float(
                    candles[positions[symbol][str(entry_date)]]["open"]
                )
                exit_price = float(
                    candles[positions[symbol][str(exit_date)]]["close"]
                )
                gross = (exit_price / entry - 1.0) * 100.0
                row.update(
                    {
                        "label_entry_date": str(entry_date),
                        "label_exit_date": str(exit_date),
                        "label_gross_return_pct": gross,
                        "label_net_return_pct": (
                            gross - ROUND_TRIP_COST_PCT
                        ),
                    }
                )
            date_rows.append(row)
        if len(date_rows) != len(symbols):
            incomplete_dates[market_date] = "incomplete_candidate_coverage"
            continue
        feature_rows.extend(date_rows)

    feature_panel = pd.DataFrame(feature_rows)
    if feature_panel.empty:
        raise ValueError("feature panel is empty")
    feature_panel = add_cross_sectional_ranks(feature_panel, RAW_FEATURES)
    feature_panel = feature_panel.sort_values(
        ["market_date", "symbol"]
    ).reset_index(drop=True)
    coverage = feature_panel.groupby("market_date")["symbol"].nunique()
    if int(coverage.min()) != len(symbols):
        raise ValueError("feature panel lost full candidate coverage")
    labeled_panel = feature_panel.dropna(
        subset=["label_entry_date", "label_exit_date", "label_net_return_pct"]
    ).copy()
    target_ranked = add_cross_sectional_ranks(
        labeled_panel, ["label_net_return_pct"]
    )
    labeled_panel["target_return_rank"] = target_ranked[
        "rank_label_net_return_pct"
    ]
    # Five equal-width relevance buckets. The supplied package multiplied by
    # four, which put only each date's single maximum observation in class 4.
    labeled_panel["relevance"] = np.floor(
        labeled_panel["target_return_rank"].astype(float) * 5.0
    ).clip(0, 4).astype(int)
    if labeled_panel.groupby("market_date")["symbol"].nunique().min() != len(
        symbols
    ):
        raise ValueError("labeled panel lost full candidate coverage")
    return PanelBuild(
        feature_panel=feature_panel,
        labeled_panel=labeled_panel,
        coverage={
            "feature_rows": len(feature_panel),
            "feature_dates": int(feature_panel["market_date"].nunique()),
            "first_feature_date": str(feature_panel["market_date"].min()),
            "last_feature_date": str(feature_panel["market_date"].max()),
            "labeled_rows": len(labeled_panel),
            "labeled_dates": int(labeled_panel["market_date"].nunique()),
            "first_labeled_date": str(labeled_panel["market_date"].min()),
            "last_labeled_date": str(labeled_panel["market_date"].max()),
            "last_label_exit_date": str(
                labeled_panel["label_exit_date"].max()
            ),
            "candidate_count_each_date": int(coverage.min()),
            "dropped_or_incomplete_dates": incomplete_dates,
        },
    )


def relevance_counts(frame: pd.DataFrame) -> dict[int, int]:
    counts = frame["relevance"].value_counts().sort_index()
    return {int(label): int(counts.get(label, 0)) for label in range(5)}


def purged_folds(frame: pd.DataFrame, n_splits: int = 5):
    dates = frame[
        ["market_date", "label_entry_date", "label_exit_date"]
    ].drop_duplicates()
    return purged_date_folds(
        dates,
        horizon_sessions=EMBARGO_SESSIONS,
        n_splits=n_splits,
    )


def score_metrics(frame: pd.DataFrame) -> dict[str, Any]:
    mean_ic, ic_dates = date_spearman(
        frame, "model_score", "target_return_rank"
    )
    scored = frame.copy()
    scored["score_rank"] = scored.groupby("market_date")[
        "model_score"
    ].rank(method="average", pct=True)
    top = scored[scored["score_rank"] >= 0.80]
    bottom = scored[scored["score_rank"] <= 0.20]
    selected = (
        scored.sort_values(
            ["market_date", "model_score", "symbol"],
            ascending=[True, False, True],
        )
        .groupby("market_date", sort=True, group_keys=False)
        .head(10)
    )
    top_by_date = top.groupby("market_date")["label_net_return_pct"].mean()
    selected_by_date = selected.groupby("market_date")[
        "label_net_return_pct"
    ].mean()
    bottom_by_date = bottom.groupby("market_date")[
        "label_net_return_pct"
    ].mean()
    spread = top_by_date.align(bottom_by_date, join="inner")
    spread_values = spread[0] - spread[1]
    dates = sorted(selected_by_date.index.astype(str))
    rotations = []
    for offset in range(HORIZON_SESSIONS):
        selected_dates = dates[offset::HORIZON_SESSIONS]
        values = selected_by_date.reindex(selected_dates).dropna().to_numpy(
            dtype=float
        )
        rotations.append(
            {
                "offset": offset,
                "observations": int(len(values)),
                "compounded_return_pct": (
                    None
                    if len(values) == 0
                    else float((np.prod(1.0 + values / 100.0) - 1.0) * 100.0)
                ),
            }
        )
    return {
        "mean_rank_ic": mean_ic,
        "rank_ic_dates": ic_dates,
        "top20_rows": len(top),
        "top20_dates": int(top_by_date.size),
        "top20_mean_net_return_pct": (
            None if top.empty else float(top["label_net_return_pct"].mean())
        ),
        "top20_median_net_return_pct": (
            None if top.empty else float(top["label_net_return_pct"].median())
        ),
        "top20_win_rate_pct": (
            None
            if top.empty
            else float((top["label_net_return_pct"] > 0.0).mean() * 100.0)
        ),
        "selected10_rows": len(selected),
        "selected10_dates": int(selected_by_date.size),
        "selected10_mean_net_return_pct": (
            None
            if selected.empty
            else float(selected["label_net_return_pct"].mean())
        ),
        "selected10_median_net_return_pct": (
            None
            if selected.empty
            else float(selected["label_net_return_pct"].median())
        ),
        "selected10_win_rate_pct": (
            None
            if selected.empty
            else float(
                (selected["label_net_return_pct"] > 0.0).mean() * 100.0
            )
        ),
        "bottom20_mean_net_return_pct": (
            None
            if bottom.empty
            else float(bottom["label_net_return_pct"].mean())
        ),
        "top_minus_bottom_mean_pct": (
            None if spread_values.empty else float(spread_values.mean())
        ),
        "nonoverlap_rotations": rotations,
    }


def select_latest(
    frame: pd.DataFrame, *, maximum_selections: int = 10
) -> pd.DataFrame:
    required = {"market_date", "symbol", "model_score", *FEATURE_COLUMNS}
    if not required.issubset(frame.columns):
        raise ValueError(
            f"latest scoring frame missing {sorted(required - set(frame))}"
        )
    dates = frame["market_date"].astype(str).unique()
    if len(dates) != 1 or frame["symbol"].nunique() != MINIMUM_CANDIDATES:
        raise ValueError("latest score requires one complete 120-name date")
    output = frame.sort_values(
        ["model_score", "symbol"], ascending=[False, True]
    ).copy()
    top_count = max(1, int(np.ceil(len(output) * 0.20)))
    return output.head(min(top_count, maximum_selections)).reset_index(
        drop=True
    )
