from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import lightgbm as lgb
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parent
if not (PROJECT_ROOT / "train_v2_transformer_20day_sp500_from_supabase.py").exists():
    PROJECT_ROOT = Path.cwd()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from train_v2_transformer_20day_sp500_from_supabase import (  # noqa: E402
    build_bar_features,
    chronological_three_way_indices,
    env_value,
    fetch_daily_candles,
    load_env_file,
    now_iso,
    pct_change,
    read_symbols_file,
    safe_float,
)


BUILD = "ALIENTAI_V2_LIGHTGBM_5DAY_SP500_SUPABASE_BASELINE_V1"
BAR_FEATURE_NAMES = [
    "day_return_pct",
    "open_to_close_pct",
    "high_low_range_pct",
    "return_5d_pct",
    "return_10d_pct",
    "return_20d_pct",
    "return_50d_pct",
    "close_vs_sma20_pct",
    "close_vs_sma50_pct",
    "close_vs_sma200_pct",
    "drawdown_20d_pct",
    "position_in_20d_range",
    "volatility_20d",
    "volume_sma20_vs_sma50",
    "volume_today_vs_sma20",
    "above_sma200",
]
SUMMARY_WINDOWS = (5, 10, 20, 60)
SUMMARY_STATS = ("mean", "std", "min", "max")


def feature_names() -> List[str]:
    names = [f"latest_{name}" for name in BAR_FEATURE_NAMES]
    for days in SUMMARY_WINDOWS:
        for stat in SUMMARY_STATS:
            names.extend(f"window_{days}_{stat}_{name}" for name in BAR_FEATURE_NAMES)
    return names


def summarize_sequence(sequence: np.ndarray) -> np.ndarray:
    if sequence.ndim != 2 or sequence.shape[1] != len(BAR_FEATURE_NAMES):
        raise ValueError("sequence must have shape [days, 16]")
    if sequence.shape[0] < max(SUMMARY_WINDOWS):
        raise ValueError("sequence must contain at least 60 days")

    parts = [sequence[-1].astype(np.float32, copy=False)]
    for days in SUMMARY_WINDOWS:
        window = sequence[-days:]
        parts.extend((
            np.mean(window, axis=0),
            np.std(window, axis=0),
            np.min(window, axis=0),
            np.max(window, axis=0),
        ))
    result = np.concatenate(parts).astype(np.float32, copy=False)
    return np.nan_to_num(result, nan=0.0, posinf=0.0, neginf=0.0)


def make_symbol_examples(
    *,
    symbol: str,
    candles: List[Dict[str, Any]],
    sequence_length: int,
    horizon_days: int,
    min_history_days: int,
    step_days: int,
    target_return_pct: float,
) -> Tuple[List[np.ndarray], List[int], List[float], List[Dict[str, Any]]]:
    if sequence_length < 60:
        raise ValueError("sequence_length must be at least 60")
    if len(candles) < min_history_days + horizon_days + 1:
        return [], [], [], []

    bars = build_bar_features(candles)
    closes = [safe_float(c.get("close"), 0.0) for c in candles]
    start_idx = max(min_history_days, sequence_length - 1)
    end_idx = len(candles) - horizon_days

    x_rows: List[np.ndarray] = []
    labels: List[int] = []
    returns: List[float] = []
    metadata: List[Dict[str, Any]] = []

    for idx in range(start_idx, end_idx, max(1, step_days)):
        current_close = closes[idx]
        future_close = closes[idx + horizon_days]
        if current_close <= 0 or future_close <= 0:
            continue
        sequence = bars[idx - sequence_length + 1:idx + 1]
        if sequence.shape[0] != sequence_length:
            continue
        future_return = pct_change(current_close, future_close)
        x_rows.append(summarize_sequence(sequence))
        labels.append(1 if future_return >= target_return_pct else 0)
        returns.append(future_return)
        metadata.append({
            "symbol": symbol,
            "date": candles[idx].get("date"),
            "datetime_ms": int(candles[idx].get("datetime_ms") or 0),
            "close": current_close,
            "future_return_pct": future_return,
        })
    return x_rows, labels, returns, metadata


def non_overlapping_indices(metadata: Sequence[Dict[str, Any]], selected: np.ndarray, gap_days: int) -> np.ndarray:
    gap_ms = max(0, int(gap_days)) * 86_400_000
    last_by_symbol: Dict[str, int] = {}
    kept: List[int] = []
    order = sorted(np.flatnonzero(selected), key=lambda i: int(metadata[int(i)].get("datetime_ms") or 0))
    for raw_idx in order:
        idx = int(raw_idx)
        symbol = str(metadata[idx].get("symbol") or "").upper()
        timestamp = int(metadata[idx].get("datetime_ms") or 0)
        if not symbol or timestamp <= 0:
            continue
        if timestamp - last_by_symbol.get(symbol, -10**30) < gap_ms:
            continue
        kept.append(idx)
        last_by_symbol[symbol] = timestamp
    return np.asarray(kept, dtype=np.int64)


def threshold_metrics(
    labels: np.ndarray,
    probabilities: np.ndarray,
    returns: np.ndarray,
    metadata: Sequence[Dict[str, Any]],
    threshold: float,
    round_trip_cost_pct: float,
    non_overlap_days: int,
) -> Dict[str, Any]:
    selected = probabilities >= threshold
    count = int(np.sum(selected))
    result: Dict[str, Any] = {"threshold": float(threshold), "signal_count": count}
    if count == 0:
        return result

    chosen_returns = returns[selected]
    net = chosen_returns - round_trip_cost_pct
    wins = net[net > 0]
    losses = net[net < 0]
    gross_profit = float(np.sum(wins)) if wins.size else 0.0
    gross_loss = abs(float(np.sum(losses))) if losses.size else 0.0
    non_overlap = non_overlapping_indices(metadata, selected, non_overlap_days)
    non_overlap_net = returns[non_overlap] - round_trip_cost_pct

    result.update({
        "precision": round(float(np.mean(labels[selected])), 6),
        "avg_raw_return_pct": round(float(np.mean(chosen_returns)), 6),
        "avg_net_return_pct": round(float(np.mean(net)), 6),
        "excess_raw_return_vs_universe_pct": round(float(np.mean(chosen_returns) - np.mean(returns)), 6),
        "cost_adjusted_win_rate": round(float(np.mean(net > 0)), 6),
        "cost_adjusted_profit_factor": round(gross_profit / gross_loss, 6) if gross_loss > 0 else None,
        "non_overlapping_signal_count": int(non_overlap.size),
        "non_overlapping_avg_net_return_pct": round(float(np.mean(non_overlap_net)), 6) if non_overlap_net.size else None,
        "non_overlapping_cost_adjusted_win_rate": round(float(np.mean(non_overlap_net > 0)), 6) if non_overlap_net.size else None,
    })
    return result


def weekly_top_k_metrics(
    labels: np.ndarray,
    probabilities: np.ndarray,
    returns: np.ndarray,
    metadata: Sequence[Dict[str, Any]],
    *,
    top_k: int,
    minimum_probability: float,
    round_trip_cost_pct: float,
) -> Dict[str, Any]:
    """Evaluate fixed weekly decision dates with permission to abstain."""
    if top_k <= 0:
        raise ValueError("top_k must be positive")
    if not (0.0 <= minimum_probability <= 1.0):
        raise ValueError("minimum_probability must be between zero and one")
    if len(metadata) != len(probabilities) or len(returns) != len(probabilities):
        raise ValueError("weekly metric inputs must have equal lengths")

    week_by_index: Dict[int, Tuple[int, int]] = {}
    latest_timestamp_by_week: Dict[Tuple[int, int], int] = {}
    for index, row in enumerate(metadata):
        timestamp_ms = int(row.get("datetime_ms") or 0)
        if timestamp_ms <= 0:
            continue
        moment = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc)
        iso = moment.isocalendar()
        week = (int(iso.year), int(iso.week))
        week_by_index[index] = week
        latest_timestamp_by_week[week] = max(latest_timestamp_by_week.get(week, 0), timestamp_ms)

    selected_indices: List[int] = []
    weekly_net_returns: List[float] = []
    candidates_by_week: Dict[Tuple[int, int], Dict[str, int]] = defaultdict(dict)
    for index, row in enumerate(metadata):
        week = week_by_index.get(index)
        if week is None:
            continue
        if int(row.get("datetime_ms") or 0) != latest_timestamp_by_week[week]:
            continue
        if float(probabilities[index]) < minimum_probability:
            continue
        symbol = str(row.get("symbol") or "").upper().strip()
        if not symbol:
            continue
        previous = candidates_by_week[week].get(symbol)
        if previous is None or probabilities[index] > probabilities[previous]:
            candidates_by_week[week][symbol] = index
    for week in sorted(latest_timestamp_by_week):
        ranked = sorted(
            candidates_by_week.get(week, {}).values(),
            key=lambda index: float(probabilities[index]), reverse=True,
        )
        chosen = ranked[:top_k]
        selected_indices.extend(chosen)
        if chosen:
            weekly_net_returns.append(float(np.mean(returns[chosen] - round_trip_cost_pct)))

    total_weeks = len(latest_timestamp_by_week)
    weeks_with_picks = len(weekly_net_returns)
    selected = np.asarray(selected_indices, dtype=np.int64)
    if selected.size:
        net = returns[selected] - round_trip_cost_pct
        gains = float(np.sum(net[net > 0]))
        losses = abs(float(np.sum(net[net < 0])))
    else:
        net = np.asarray([], dtype=np.float32)
        gains = losses = 0.0

    cumulative = 0.0
    peak = 0.0
    maximum_drawdown = 0.0
    for weekly_return in weekly_net_returns:
        cumulative += weekly_return
        peak = max(peak, cumulative)
        maximum_drawdown = max(maximum_drawdown, peak - cumulative)

    result: Dict[str, Any] = {
        "top_k": int(top_k),
        "minimum_probability": float(minimum_probability),
        "total_weeks": total_weeks,
        "weeks_with_picks": weeks_with_picks,
        "abstention_rate": round(1.0 - (weeks_with_picks / total_weeks), 6) if total_weeks else None,
        "pick_count": int(selected.size),
    }
    if selected.size:
        result.update({
            "target_precision": round(float(np.mean(labels[selected])), 6),
            "average_net_return_pct": round(float(np.mean(net)), 6),
            "median_net_return_pct": round(float(np.median(net)), 6),
            "cost_adjusted_win_rate": round(float(np.mean(net > 0)), 6),
            "cost_adjusted_profit_factor": round(gains / losses, 6) if losses > 0 else None,
            "worst_pick_net_return_pct": round(float(np.min(net)), 6),
            "additive_weekly_max_drawdown_pct_points": round(maximum_drawdown, 6),
        })
    return result


def evaluate_partition(
    labels: np.ndarray,
    probabilities: np.ndarray,
    predicted_returns: np.ndarray,
    returns: np.ndarray,
    metadata: Sequence[Dict[str, Any]],
    thresholds: Sequence[float],
    round_trip_cost_pct: float,
    non_overlap_days: int,
) -> Dict[str, Any]:
    return {
        "rows": int(labels.size),
        "base_positive_rate": round(float(np.mean(labels)), 6),
        "universe_avg_raw_return_pct": round(float(np.mean(returns)), 6),
        "classifier_logloss": round(float(np.mean(-(labels * np.log(np.clip(probabilities, 1e-7, 1 - 1e-7)) + (1 - labels) * np.log(np.clip(1 - probabilities, 1e-7, 1 - 1e-7))))), 6),
        "regression_mae_pct": round(float(np.mean(np.abs(predicted_returns - returns))), 6),
        "thresholds": [
            threshold_metrics(labels, probabilities, returns, metadata, t, round_trip_cost_pct, non_overlap_days)
            for t in thresholds
        ],
        "weekly_selective": [
            weekly_top_k_metrics(
                labels, probabilities, returns, metadata,
                top_k=top_k, minimum_probability=minimum_probability,
                round_trip_cost_pct=round_trip_cost_pct,
            )
            for top_k in (1, 2)
            for minimum_probability in (0.50, 0.55, 0.60)
        ],
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def train_native_models(
    *,
    x_train: np.ndarray,
    y_train: np.ndarray,
    returns_train: np.ndarray,
    x_validation: np.ndarray,
    y_validation: np.ndarray,
    returns_validation: np.ndarray,
    names: Sequence[str],
    num_boost_round: int,
    early_stopping_rounds: int,
) -> Tuple[lgb.Booster, lgb.Booster]:
    """Train without LightGBM's optional scikit-learn compatibility layer."""
    classifier_train = lgb.Dataset(x_train, label=y_train, feature_name=list(names))
    classifier_validation = lgb.Dataset(
        x_validation,
        label=y_validation,
        reference=classifier_train,
        feature_name=list(names),
    )
    regressor_train = lgb.Dataset(x_train, label=returns_train, feature_name=list(names))
    regressor_validation = lgb.Dataset(
        x_validation,
        label=returns_validation,
        reference=regressor_train,
        feature_name=list(names),
    )
    callbacks = [
        lgb.early_stopping(max(1, int(early_stopping_rounds))),
        lgb.log_evaluation(50),
    ]
    common = {
        "learning_rate": 0.025,
        "num_leaves": 31,
        "min_data_in_leaf": 100,
        "bagging_fraction": 0.80,
        "bagging_freq": 5,
        "feature_fraction": 0.80,
        "lambda_l1": 2.0,
        "lambda_l2": 6.0,
        "verbosity": -1,
        "num_threads": 0,
        "force_col_wise": True,
    }
    classifier = lgb.train(
        {**common, "objective": "binary", "metric": "binary_logloss", "seed": 42},
        classifier_train,
        num_boost_round=max(1, int(num_boost_round)),
        valid_sets=[classifier_validation],
        valid_names=["validation"],
        callbacks=callbacks,
    )
    regressor = lgb.train(
        {**common, "objective": "huber", "metric": "l1", "seed": 43},
        regressor_train,
        num_boost_round=max(1, int(num_boost_round)),
        valid_sets=[regressor_validation],
        valid_names=["validation"],
        callbacks=callbacks,
    )
    return classifier, regressor


def fetch_symbol_candles(
    *, supabase_url: str, supabase_key: str, table: str, symbol: str, limit: int
) -> List[Dict[str, Any]]:
    """Keep the shared Transformer/Supabase helper interface explicit and tested."""
    return fetch_daily_candles(
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        table=table,
        symbol=symbol,
        limit=limit,
    )


def fetch_symbol_candles_with_retry(
    *, supabase_url: str, supabase_key: str, table: str, symbol: str, limit: int,
    attempts: int = 4, base_delay_seconds: float = 2.0,
) -> List[Dict[str, Any]]:
    """Retry complete symbol reads so a partial paginated response is never used."""
    last_error: Optional[Exception] = None
    for attempt in range(1, max(1, int(attempts)) + 1):
        try:
            return fetch_symbol_candles(
                supabase_url=supabase_url, supabase_key=supabase_key, table=table,
                symbol=symbol, limit=limit,
            )
        except Exception as exc:
            last_error = exc
            if attempt >= max(1, int(attempts)):
                break
            delay = max(0.0, float(base_delay_seconds)) * (2 ** (attempt - 1))
            print(
                f"  transient fetch failure for {symbol} "
                f"(attempt {attempt}/{attempts}): {type(exc).__name__}: {exc}",
                file=sys.stderr, flush=True,
            )
            if delay:
                time.sleep(delay)
    raise RuntimeError(
        f"Failed to fetch complete candle history for {symbol} after {attempts} attempts"
    ) from last_error


def main() -> None:
    parser = argparse.ArgumentParser(description="Train an isolated five-day LightGBM S&P 500 baseline.")
    parser.add_argument("--symbols-file", default="sp500_expanded_symbols.txt")
    parser.add_argument("--table", default="v2_daily_candles")
    parser.add_argument("--candle-limit", type=int, default=10000)
    parser.add_argument("--sequence-length", type=int, default=60)
    parser.add_argument("--horizon-days", type=int, default=5)
    parser.add_argument("--target-return-pct", type=float, default=0.0)
    parser.add_argument("--min-history-days", type=int, default=260)
    parser.add_argument("--step-days", type=int, default=1)
    parser.add_argument("--train-fraction", type=float, default=0.60)
    parser.add_argument("--validation-fraction", type=float, default=0.20)
    parser.add_argument("--split-embargo-calendar-days", type=int, default=12)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    parser.add_argument("--non-overlapping-calendar-days", type=int, default=9)
    parser.add_argument("--num-boost-round", type=int, default=1500)
    parser.add_argument("--early-stopping-rounds", type=int, default=100)
    parser.add_argument("--delay", type=float, default=0.05)
    parser.add_argument("--fetch-attempts", type=int, default=4)
    parser.add_argument("--fetch-retry-delay", type=float, default=2.0)
    parser.add_argument("--output-dir", default="data_v2/lightgbm_5day_sp500_supabase_training")
    args = parser.parse_args()

    if args.horizon_days != 5:
        raise ValueError("This isolated baseline is intentionally fixed to a five-trading-session horizon")
    load_env_file(PROJECT_ROOT / ".env")
    url = env_value("SUPABASE_URL")
    key = env_value("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_KEY", "SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Missing Supabase URL or key")

    symbols = read_symbols_file(PROJECT_ROOT / args.symbols_file)
    all_x: List[np.ndarray] = []
    all_y: List[int] = []
    all_returns: List[float] = []
    all_meta: List[Dict[str, Any]] = []
    summaries: List[Dict[str, Any]] = []

    print(f"Build: {BUILD}")
    print(f"Symbols: {len(symbols)}; horizon: 5 trading sessions; target: {args.target_return_pct:.2f}%")
    for number, symbol in enumerate(symbols, start=1):
        print(f"[{number}/{len(symbols)}] Fetching/building {symbol}...")
        candles = fetch_symbol_candles_with_retry(
            supabase_url=url,
            supabase_key=key,
            table=args.table,
            symbol=symbol,
            limit=args.candle_limit,
            attempts=args.fetch_attempts,
            base_delay_seconds=args.fetch_retry_delay,
        )
        x_rows, labels, future_returns, metadata = make_symbol_examples(
            symbol=symbol,
            candles=candles,
            sequence_length=args.sequence_length,
            horizon_days=args.horizon_days,
            min_history_days=args.min_history_days,
            step_days=args.step_days,
            target_return_pct=args.target_return_pct,
        )
        all_x.extend(x_rows)
        all_y.extend(labels)
        all_returns.extend(future_returns)
        all_meta.extend(metadata)
        summaries.append({"symbol": symbol, "candles": len(candles), "examples": len(x_rows)})
        if args.delay > 0:
            time.sleep(args.delay)

    if not all_x:
        raise RuntimeError("No training examples were created")
    x = np.stack(all_x).astype(np.float32)
    y = np.asarray(all_y, dtype=np.int32)
    returns = np.asarray(all_returns, dtype=np.float32)
    timestamps = np.asarray([int(m.get("datetime_ms") or 0) for m in all_meta], dtype=np.int64)
    train_idx, val_idx, test_idx, split = chronological_three_way_indices(
        timestamps,
        train_fraction=args.train_fraction,
        validation_fraction=args.validation_fraction,
        embargo_calendar_days=args.split_embargo_calendar_days,
    )

    names = feature_names()
    classifier, regressor = train_native_models(
        x_train=x[train_idx],
        y_train=y[train_idx],
        returns_train=returns[train_idx],
        x_validation=x[val_idx],
        y_validation=y[val_idx],
        returns_validation=returns[val_idx],
        names=names,
        num_boost_round=args.num_boost_round,
        early_stopping_rounds=args.early_stopping_rounds,
    )

    thresholds = (0.50, 0.55, 0.60, 0.65, 0.70)
    def partition(indices: np.ndarray) -> Dict[str, Any]:
        probs = classifier.predict(x[indices], num_iteration=classifier.best_iteration)
        predicted = regressor.predict(x[indices], num_iteration=regressor.best_iteration)
        meta = [all_meta[int(i)] for i in indices]
        return evaluate_partition(y[indices], probs, predicted, returns[indices], meta, thresholds, args.round_trip_cost_pct, args.non_overlapping_calendar_days)

    output = (PROJECT_ROOT / args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    classifier.save_model(str(output / "lightgbm_5day_classifier.txt"), num_iteration=classifier.best_iteration)
    regressor.save_model(str(output / "lightgbm_5day_return_regressor.txt"), num_iteration=regressor.best_iteration)
    importance = sorted(
        ({"feature": n, "classifier_gain": float(g)} for n, g in zip(names, classifier.feature_importance(importance_type="gain"))),
        key=lambda row: row["classifier_gain"], reverse=True,
    )
    report = {
        "status": "complete", "finished_at": now_iso(), "build": BUILD,
        "paper_only": True, "shadow_only": True, "execution_enabled": False,
        "symbols_seen": len(symbols), "total_examples": int(x.shape[0]), "feature_count": int(x.shape[1]),
        "horizon_trading_sessions": 5, "target_return_pct": args.target_return_pct,
        "round_trip_cost_pct": args.round_trip_cost_pct, "split": split,
        "classifier_best_iteration": int(classifier.best_iteration), "regressor_best_iteration": int(regressor.best_iteration),
        "train_metrics": partition(train_idx), "validation_metrics": partition(val_idx), "test_metrics": partition(test_idx),
        "top_40_classifier_features": importance[:40], "symbol_summary": summaries,
        "classifier_path": str(output / "lightgbm_5day_classifier.txt"),
        "regressor_path": str(output / "lightgbm_5day_return_regressor.txt"),
    }
    write_json(output / "lightgbm_5day_training_report.json", report)
    print("DONE")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
