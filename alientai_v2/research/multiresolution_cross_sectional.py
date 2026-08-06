from __future__ import annotations

"""Leakage-safe helpers for the multi-resolution cross-sectional ranker."""

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

from alientai_v2.research.cross_sectional_technical_5d import (
    technical_features,
)


DAILY_FEATURES = (
    "daily_return_5d_pct",
    "daily_return_10d_pct",
    "daily_roc_10d_pct",
    "daily_rsi_14",
    "daily_stochastic_k_14",
    "daily_cci_20",
    "daily_relative_volume_20d",
    "daily_bollinger_pct_b_20",
    "daily_atr_14_pct",
    "daily_distance_ema_10_pct",
    "daily_macd_histogram_pct",
    "daily_relative_strength_qqq_5d_pct",
    "daily_relative_strength_spy_5d_pct",
)

FIVE_MINUTE_FEATURES = (
    "five_minute_regular_return_pct",
    "five_minute_regular_range_pct",
    "five_minute_regular_realized_volatility",
    "five_minute_regular_close_location",
    "five_minute_regular_last_hour_return_pct",
    "five_minute_regular_up_volume_fraction",
    "five_minute_regular_observed_bar_fraction",
    "afterhours_return_pct",
    "afterhours_range_pct",
    "afterhours_close_location",
    "afterhours_volume_to_regular",
    "afterhours_up_volume_fraction",
    "afterhours_observed_bar_fraction",
)

OPTION_FEATURES = (
    "call_volume",
    "call_open_interest",
    "call_volume_open_interest_ratio",
    "call_volume_prior10_median_ratio",
    "call_volume_prior20_zscore",
    "near_money_call_iv",
)

NEWS_FEATURES = (
    "news_article_count",
    "news_weighted_sentiment",
    "news_positive_article_count",
    "news_negative_article_count",
    "news_latest_age_hours",
)

CONTEXT_FEATURES = (
    "context_qqq_return_5d_pct",
    "context_qqq_return_20d_pct",
    "context_qqq_realized_volatility_20d",
    "context_spy_return_5d_pct",
    "context_spy_return_20d_pct",
    "context_spy_realized_volatility_20d",
)

FEATURE_SETS = {
    "daily_only": DAILY_FEATURES + CONTEXT_FEATURES,
    "daily_plus_5minute": DAILY_FEATURES
    + FIVE_MINUTE_FEATURES
    + CONTEXT_FEATURES,
    "daily_5minute_options": DAILY_FEATURES
    + FIVE_MINUTE_FEATURES
    + OPTION_FEATURES
    + ("option_available",)
    + CONTEXT_FEATURES,
    "daily_5minute_options_news": DAILY_FEATURES
    + FIVE_MINUTE_FEATURES
    + OPTION_FEATURES
    + NEWS_FEATURES
    + ("option_available", "news_available")
    + CONTEXT_FEATURES,
}


def requested_daily_features(
    candles: Sequence[Mapping[str, Any]],
    *,
    qqq_return_5d_pct: float,
    spy_return_5d_pct: float,
) -> dict[str, float | None]:
    """Return Jeff's requested daily features plus relative-strength context."""
    source = technical_features(candles)
    return {
        "daily_return_5d_pct": source["x5_return_5d_pct"],
        "daily_return_10d_pct": source["x5_return_10d_pct"],
        # Retained intentionally even though it equals the ten-session return.
        "daily_roc_10d_pct": source["x5_roc_10d_pct"],
        "daily_rsi_14": source["x5_rsi_14"],
        "daily_stochastic_k_14": source["x5_stochastic_k_14"],
        "daily_cci_20": source["x5_cci_20"],
        "daily_relative_volume_20d": source["x5_relative_volume_20d"],
        "daily_bollinger_pct_b_20": source["x5_bollinger_pct_b_20"],
        "daily_atr_14_pct": source["x5_atr_14_pct"],
        "daily_distance_ema_10_pct": source["x5_distance_ema_10_pct"],
        "daily_macd_histogram_pct": source["x5_macd_histogram_pct"],
        "daily_relative_strength_qqq_5d_pct": (
            float(source["x5_return_5d_pct"]) - qqq_return_5d_pct
        ),
        "daily_relative_strength_spy_5d_pct": (
            float(source["x5_return_5d_pct"]) - spy_return_5d_pct
        ),
        "average_dollar_volume_20d": source[
            "x5_average_dollar_volume_20d"
        ],
    }


def market_context_features(
    qqq_candles: Sequence[Mapping[str, Any]],
    spy_candles: Sequence[Mapping[str, Any]],
) -> dict[str, float]:
    qqq = technical_features(qqq_candles)
    spy = technical_features(spy_candles)
    return {
        "context_qqq_return_5d_pct": float(qqq["x5_return_5d_pct"]),
        "context_qqq_return_20d_pct": (
            float(qqq_candles[-1]["close"])
            / float(qqq_candles[-21]["close"])
            - 1.0
        )
        * 100.0,
        "context_qqq_realized_volatility_20d": float(
            qqq["x5_realized_volatility_20d_annualized_pct"]
        ),
        "context_spy_return_5d_pct": float(spy["x5_return_5d_pct"]),
        "context_spy_return_20d_pct": (
            float(spy_candles[-1]["close"])
            / float(spy_candles[-21]["close"])
            - 1.0
        )
        * 100.0,
        "context_spy_realized_volatility_20d": float(
            spy["x5_realized_volatility_20d_annualized_pct"]
        ),
    }


def _close_location(high: float, low: float, close: float) -> float:
    return 0.5 if high <= low else (close - low) / (high - low)


def _up_volume_fraction(frame: pd.DataFrame) -> float:
    changes = frame["close"].diff()
    total = float(frame["volume"].sum())
    if total <= 0.0:
        return 0.5
    return float(frame.loc[changes > 0.0, "volume"].sum() / total)


def _resample_to_five_minutes(frame: pd.DataFrame) -> pd.DataFrame:
    indexed = frame.set_index("timestamp").sort_index()
    output = indexed.resample(
        "5min", origin="start_day", label="left", closed="left"
    ).agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
    )
    return output.dropna(subset=["open", "high", "low", "close"]).reset_index()


def five_minute_session_features(
    frame: pd.DataFrame,
    *,
    source_interval_minutes: int,
) -> dict[str, float] | None:
    """Summarize one complete regular and after-hours session."""
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    if not required.issubset(frame.columns) or frame.empty:
        return None
    local = frame[list(required)].copy()
    local["timestamp"] = pd.to_datetime(local["timestamp"], errors="coerce")
    local = local.dropna(subset=["timestamp"])
    if local["timestamp"].duplicated().any():
        return None
    for name in ("open", "high", "low", "close", "volume"):
        local[name] = pd.to_numeric(local[name], errors="coerce")
    if local[list(required - {"timestamp"})].isna().any().any():
        return None
    if (
        (local[["open", "high", "low", "close"]] <= 0.0).any().any()
        or (local["volume"] < 0.0).any()
    ):
        return None
    if source_interval_minutes == 1:
        local = _resample_to_five_minutes(local)
    elif source_interval_minutes != 5:
        raise ValueError("only one- or five-minute source bars are supported")
    local = local.sort_values("timestamp")
    session_day = local.iloc[0]["timestamp"].normalize()
    expected_regular = pd.date_range(
        session_day + pd.Timedelta(hours=9, minutes=30),
        session_day + pd.Timedelta(hours=15, minutes=55),
        freq="5min",
    )
    expected_after = pd.date_range(
        session_day + pd.Timedelta(hours=16),
        session_day + pd.Timedelta(hours=19, minutes=55),
        freq="5min",
    )
    indexed = local.set_index("timestamp")
    if indexed.index.duplicated().any():
        return None
    regular = indexed.reindex(expected_regular)
    regular_observed = regular["close"].notna()
    # Regular-session endpoints prove that this is the complete session. An
    # occasional omitted interval is a zero-trade bar, reconstructed only from
    # the last already-known price (never from a future print).
    if (
        not bool(regular_observed.iloc[0])
        or not bool(regular_observed.iloc[-1])
        or int(regular_observed.sum()) < 75
    ):
        return None
    regular["close"] = regular["close"].ffill()
    for name in ("open", "high", "low"):
        regular[name] = regular[name].fillna(regular["close"])
    regular["volume"] = regular["volume"].fillna(0.0)
    regular = regular.reset_index(names="timestamp")

    after = indexed.reindex(expected_after)
    after_observed = after["close"].notna()
    # With a complete month file, omitted extended-hours intervals mean no
    # reported trade. Require at least one actual after-hours print so a wholly
    # unavailable session is not misclassified as zero activity.
    if int(after_observed.sum()) < 1:
        return None
    regular_close_seed = float(regular.iloc[-1]["close"])
    after["close"] = after["close"].ffill().fillna(regular_close_seed)
    for name in ("open", "high", "low"):
        after[name] = after[name].fillna(after["close"])
    after["volume"] = after["volume"].fillna(0.0)
    after = after.reset_index(names="timestamp")

    regular_open = float(regular.iloc[0]["open"])
    regular_close = float(regular.iloc[-1]["close"])
    regular_high = float(regular["high"].max())
    regular_low = float(regular["low"].min())
    five_returns = np.diff(np.log(regular["close"].to_numpy(dtype=float)))
    last_hour_open = float(regular.iloc[-12]["open"])
    after_close = float(after.iloc[-1]["close"])
    after_high = float(after["high"].max())
    after_low = float(after["low"].min())
    regular_volume = float(regular["volume"].sum())
    after_volume = float(after["volume"].sum())
    return {
        "five_minute_regular_return_pct": (
            regular_close / regular_open - 1.0
        )
        * 100.0,
        "five_minute_regular_range_pct": (
            regular_high / regular_low - 1.0
        )
        * 100.0,
        "five_minute_regular_realized_volatility": float(
            np.std(five_returns, ddof=0) * np.sqrt(78.0) * 100.0
        ),
        "five_minute_regular_close_location": _close_location(
            regular_high, regular_low, regular_close
        ),
        "five_minute_regular_last_hour_return_pct": (
            regular_close / last_hour_open - 1.0
        )
        * 100.0,
        "five_minute_regular_up_volume_fraction": _up_volume_fraction(regular),
        "five_minute_regular_observed_bar_fraction": float(
            regular_observed.mean()
        ),
        "afterhours_return_pct": (
            after_close / regular_close - 1.0
        )
        * 100.0,
        "afterhours_range_pct": (after_high / after_low - 1.0) * 100.0,
        "afterhours_close_location": _close_location(
            after_high, after_low, after_close
        ),
        "afterhours_volume_to_regular": (
            np.nan
            if regular_volume <= 0.0
            else after_volume / regular_volume
        ),
        "afterhours_up_volume_fraction": _up_volume_fraction(after),
        "afterhours_observed_bar_fraction": float(after_observed.mean()),
    }


def add_option_history_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Add call-activity baselines using only strictly earlier observations."""
    output = frame.sort_values(["symbol", "market_date"]).copy()
    grouped = output.groupby("symbol", sort=False)["call_volume"]
    prior_median = grouped.transform(
        lambda values: values.shift(1).rolling(10, min_periods=10).median()
    )
    prior_mean = grouped.transform(
        lambda values: values.shift(1).rolling(20, min_periods=10).mean()
    )
    prior_std = grouped.transform(
        lambda values: values.shift(1).rolling(20, min_periods=10).std(ddof=0)
    )
    output["call_volume_prior10_median_ratio"] = (
        output["call_volume"] / prior_median.replace(0.0, np.nan)
    )
    output["call_volume_prior20_zscore"] = (
        (output["call_volume"] - prior_mean)
        / prior_std.replace(0.0, np.nan)
    )
    output["call_volume_open_interest_ratio"] = (
        output["call_volume"]
        / output["call_open_interest"].replace(0.0, np.nan)
    )
    return output


def add_cross_sectional_ranks(
    frame: pd.DataFrame, columns: Iterable[str]
) -> pd.DataFrame:
    """Add deterministic 0-1 percentile ranks independently for each date."""
    output = frame.copy()
    for column in columns:
        def rank_group(values: pd.Series) -> pd.Series:
            numeric = pd.to_numeric(values, errors="coerce")
            count = int(numeric.notna().sum())
            if count <= 1:
                return pd.Series(np.nan, index=values.index)
            ranks = numeric.rank(method="average")
            return (ranks - 1.0) / (count - 1.0)

        output[f"rank_{column}"] = output.groupby(
            "market_date", sort=False
        )[column].transform(rank_group)
    return output


def rank_target(frame: pd.DataFrame, return_column: str) -> pd.Series:
    ranked = add_cross_sectional_ranks(frame, [return_column])
    return ranked[f"rank_{return_column}"]


@dataclass(frozen=True)
class PurgedFold:
    fold: int
    train_dates: tuple[str, ...]
    validation_dates: tuple[str, ...]
    purged_dates: tuple[str, ...]
    embargo_dates: tuple[str, ...]


def purged_date_folds(
    date_rows: pd.DataFrame,
    *,
    horizon_sessions: int,
    n_splits: int,
) -> list[PurgedFold]:
    """Create contiguous whole-date folds with label overlap purge + embargo."""
    required = {"market_date", "label_entry_date", "label_exit_date"}
    if not required.issubset(date_rows.columns):
        raise ValueError(f"date rows missing {sorted(required - set(date_rows))}")
    unique = (
        date_rows[list(required)]
        .drop_duplicates()
        .sort_values("market_date")
        .reset_index(drop=True)
    )
    if unique["market_date"].duplicated().any():
        raise ValueError("one label interval is required per market date")
    dates = unique["market_date"].astype(str).tolist()
    if len(dates) < max(30, n_splits * 8):
        raise ValueError("insufficient whole dates for purged folds")
    blocks = np.array_split(np.asarray(dates, dtype=object), n_splits)
    folds: list[PurgedFold] = []
    for fold_index, validation in enumerate(blocks, start=1):
        validation_dates = tuple(str(value) for value in validation)
        validation_rows = unique[
            unique["market_date"].isin(validation_dates)
        ]
        interval_start = str(validation_rows["market_date"].min())
        interval_end = str(validation_rows["label_exit_date"].max())
        validation_last_index = dates.index(validation_dates[-1])
        embargo = tuple(
            dates[
                validation_last_index
                + 1 : validation_last_index
                + 1
                + horizon_sessions
            ]
        )
        candidates = unique[
            ~unique["market_date"].isin(validation_dates)
            & ~unique["market_date"].isin(embargo)
        ]
        overlaps = (
            (candidates["label_entry_date"] <= interval_end)
            & (candidates["label_exit_date"] >= interval_start)
        )
        purged = tuple(candidates.loc[overlaps, "market_date"].astype(str))
        train = tuple(
            candidates.loc[~overlaps, "market_date"].astype(str)
        )
        if not train:
            raise ValueError(f"fold {fold_index} has no training dates")
        folds.append(
            PurgedFold(
                fold=fold_index,
                train_dates=train,
                validation_dates=validation_dates,
                purged_dates=purged,
                embargo_dates=embargo,
            )
        )
    return folds


def date_spearman(
    rows: pd.DataFrame, score_column: str, target_column: str
) -> tuple[float | None, int]:
    values = []
    for _, group in rows.groupby("market_date", sort=True):
        subset = group[[score_column, target_column]].dropna()
        if len(subset) < 3:
            continue
        value = subset[score_column].corr(
            subset[target_column], method="spearman"
        )
        if pd.notna(value):
            values.append(float(value))
    return (float(np.mean(values)), len(values)) if values else (None, 0)


def clustered_mean_ci(values_by_date: Mapping[str, Sequence[float]]) -> dict:
    means = np.asarray(
        [np.mean(values) for values in values_by_date.values() if values],
        dtype=float,
    )
    if len(means) < 2:
        return {"lower_95": None, "upper_95": None, "dates": len(means)}
    standard_error = float(np.std(means, ddof=1) / np.sqrt(len(means)))
    mean = float(np.mean(means))
    return {
        "lower_95": mean - 1.96 * standard_error,
        "upper_95": mean + 1.96 * standard_error,
        "dates": len(means),
    }


def selection_metrics(
    rows: pd.DataFrame,
    *,
    score_column: str,
    return_column: str,
    threshold: float,
    max_names: int = 15,
) -> dict[str, Any]:
    selected_groups = []
    bottom_groups = []
    for _, group in rows.groupby("market_date", sort=True):
        local = group.dropna(subset=[score_column, return_column]).copy()
        if len(local) < 5:
            continue
        local["score_percentile"] = local[score_column].rank(
            method="average", pct=True
        )
        selected_groups.append(
            local[local["score_percentile"] >= threshold]
            .sort_values([score_column, "symbol"], ascending=[False, True])
            .head(max_names)
        )
        bottom_groups.append(
            local[local["score_percentile"] <= 1.0 - threshold]
            .sort_values([score_column, "symbol"], ascending=[True, True])
            .head(max_names)
        )
    selected = (
        pd.concat(selected_groups, ignore_index=True)
        if selected_groups
        else pd.DataFrame()
    )
    bottom = (
        pd.concat(bottom_groups, ignore_index=True)
        if bottom_groups
        else pd.DataFrame()
    )
    if selected.empty:
        return {
            "signals": 0,
            "dates": 0,
            "mean_net_return_pct": None,
            "median_net_return_pct": None,
            "win_rate_pct": None,
            "top_minus_bottom_mean_pct": None,
            "clustered_mean_ci": {
                "lower_95": None,
                "upper_95": None,
                "dates": 0,
            },
        }
    returns = selected[return_column].astype(float)
    grouped = {
        str(date): group[return_column].astype(float).tolist()
        for date, group in selected.groupby("market_date", sort=True)
    }
    bottom_mean = (
        float(bottom[return_column].mean()) if not bottom.empty else np.nan
    )
    return {
        "signals": int(len(selected)),
        "dates": int(selected["market_date"].nunique()),
        "mean_net_return_pct": float(returns.mean()),
        "median_net_return_pct": float(returns.median()),
        "win_rate_pct": float((returns > 0.0).mean() * 100.0),
        "top_minus_bottom_mean_pct": (
            None if np.isnan(bottom_mean) else float(returns.mean() - bottom_mean)
        ),
        "clustered_mean_ci": clustered_mean_ci(grouped),
    }
