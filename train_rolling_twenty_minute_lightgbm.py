from __future__ import annotations

"""Train and evaluate one research-only configurable-horizon LightGBM clone."""

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import lightgbm as lgb
import numpy as np

from alientai_v2.research.score_calibration import (
    brier_score,
    expected_calibration_error,
    fit_isotonic,
)

POLICY_SCORE_PERCENTILES = (90.0, 95.0, 97.5, 99.0, 99.5)
MAX_POSITIONS = 5
MIN_POLICY_SELECTIONS = 30
EMBARGO_SESSIONS = 5
SCHEMA_VERSION = 3
TIMESTAMP_UNIT = "ns_since_unix_epoch"
ENTRY_ASSUMPTION = "next_minute_open"
ALLOWED_HORIZON_MINUTES = (5, 10, 20, 30, 60, 90)


@dataclass
class Partition:
    x: np.ndarray
    gross: np.ndarray
    net: np.ndarray
    positive: np.ndarray
    timestamp: np.ndarray
    symbol: np.ndarray


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_compiled_panel_files(
    manifest: dict[str, Any],
    root: Path,
) -> dict[str, int]:
    """Fail closed on missing, changed, duplicated, or orphaned panel shards."""

    target_symbols = set(manifest["target_symbols"])
    seen: set[tuple[str, str]] = set()
    expected_paths: set[Path] = set()
    total_rows = 0
    root_resolved = root.resolve()
    for record in manifest.get("completed") or []:
        symbol = str(record["symbol"])
        month = str(record["month"])
        key = (symbol, month)
        if symbol not in target_symbols:
            raise ValueError(f"compiled panel contains unexpected symbol: {symbol}")
        if key in seen:
            raise ValueError(f"compiled panel contains duplicate shard: {symbol}|{month}")
        seen.add(key)
        path = (root / str(record["relative_path"])).resolve()
        if not path.is_relative_to(root_resolved):
            raise ValueError(f"compiled shard escapes panel root: {symbol}|{month}")
        if not path.is_file():
            raise ValueError(f"compiled shard is missing: {symbol}|{month}")
        if sha256(path) != record.get("output_sha256"):
            raise ValueError(f"compiled shard hash mismatch: {symbol}|{month}")
        rows = int(record.get("rows", -1))
        if rows < 0:
            raise ValueError(f"compiled shard row count is invalid: {symbol}|{month}")
        total_rows += rows
        expected_paths.add(path)
    observed_symbols = {symbol for symbol, _ in seen}
    if observed_symbols != target_symbols:
        missing = sorted(target_symbols - observed_symbols)
        raise ValueError(
            "compiled panel has no shards for target symbols: " + ", ".join(missing)
        )
    actual_paths = {path.resolve() for path in root.rglob("*.npz")}
    orphaned = actual_paths - expected_paths
    if orphaned:
        raise ValueError(f"compiled panel contains {len(orphaned)} orphan shards")
    return {
        "shards": len(seen),
        "rows": total_rows,
        "orphan_shards": 0,
    }


def split_market_dates(
    market_dates: Iterable[np.datetime64],
) -> dict[str, set[np.datetime64]]:
    dates = np.array(sorted(set(market_dates)), dtype="datetime64[D]")
    if len(dates) < 100:
        raise ValueError("at least 100 market dates are required")
    train_end = int(len(dates) * 0.50)
    fit_validation_end = int(len(dates) * 0.65)
    calibration_end = int(len(dates) * 0.75)
    policy_validation_end = int(len(dates) * 0.85)
    boundaries = (
        train_end,
        fit_validation_end,
        calibration_end,
        policy_validation_end,
    )
    if any(
        right - left <= EMBARGO_SESSIONS
        for left, right in zip((0, *boundaries[:-1]), boundaries)
    ):
        raise ValueError("insufficient dates after embargo")
    return {
        "train": set(dates[:train_end]),
        "fit_validation": set(
            dates[
                train_end + EMBARGO_SESSIONS
                : fit_validation_end
            ]
        ),
        "calibration": set(
            dates[
                fit_validation_end + EMBARGO_SESSIONS
                : calibration_end
            ]
        ),
        "policy_validation": set(
            dates[
                calibration_end + EMBARGO_SESSIONS
                : policy_validation_end
            ]
        ),
        "test": set(
            dates[policy_validation_end + EMBARGO_SESSIONS :]
        ),
        "embargo": set(
            np.concatenate(
                [
                    dates[train_end : train_end + EMBARGO_SESSIONS],
                    dates[
                        fit_validation_end
                        : fit_validation_end + EMBARGO_SESSIONS
                    ],
                    dates[
                        calibration_end
                        : calibration_end + EMBARGO_SESSIONS
                    ],
                    dates[
                        policy_validation_end
                        : policy_validation_end + EMBARGO_SESSIONS
                    ],
                ]
            )
        ),
    }


def rotating_nonoverlap_mask(
    timestamps_ns: np.ndarray,
    minute_of_session: np.ndarray,
    horizon_minutes: int = 20,
) -> np.ndarray:
    if horizon_minutes <= 0:
        raise ValueError("horizon_minutes must be positive")
    dates = timestamps_ns.astype("datetime64[ns]").astype("datetime64[D]")
    date_numbers = dates.astype(np.int64)
    offsets = np.mod(date_numbers, horizon_minutes)
    return (
        np.mod(minute_of_session.astype(np.int64), horizon_minutes)
        == offsets
    )


def discover_dates(manifest: dict[str, Any], root: Path) -> np.ndarray:
    dates: set[np.datetime64] = set()
    for record in manifest["completed"]:
        path = root / record["relative_path"]
        with np.load(path) as shard:
            values = shard["timestamp"].astype("datetime64[ns]").astype("datetime64[D]")
        dates.update(np.unique(values))
    return np.array(sorted(dates), dtype="datetime64[D]")


def load_partitions(
    manifest: dict[str, Any],
    root: Path,
    date_splits: dict[str, set[np.datetime64]],
    partition_names: Iterable[str],
) -> dict[str, Partition]:
    requested = tuple(partition_names)
    if not requested:
        raise ValueError("at least one partition must be requested")
    unknown = set(requested) - set(date_splits)
    if unknown:
        raise ValueError(f"unknown partitions requested: {sorted(unknown)}")
    feature_names = list(manifest["feature_names"])
    minute_index = feature_names.index("minute_of_session")
    buffers: dict[str, dict[str, list[np.ndarray]]] = {
        name: {
            field: []
            for field in (
                "x",
                "gross",
                "net",
                "positive",
                "timestamp",
                "symbol",
            )
        }
        for name in requested
    }
    symbol_ids = {
        symbol: index
        for index, symbol in enumerate(
            sorted({str(item["symbol"]) for item in manifest["completed"]})
        )
    }
    for record in manifest["completed"]:
        with np.load(root / record["relative_path"]) as shard:
            x = shard["x"].astype(np.float32)
            gross = shard["gross"].astype(np.float32)
            net = shard["net"].astype(np.float32)
            positive = shard["positive"].astype(np.float32)
            timestamp = shard["timestamp"].astype(np.int64)
        sample_mask = rotating_nonoverlap_mask(
            timestamp,
            x[:, minute_index],
            int(manifest["horizon_minutes"]),
        )
        dates = timestamp.astype("datetime64[ns]").astype("datetime64[D]")
        for name in buffers:
            allowed = np.isin(dates, list(date_splits[name]))
            keep = sample_mask & allowed
            count = int(keep.sum())
            if not count:
                continue
            buffers[name]["x"].append(x[keep])
            buffers[name]["gross"].append(gross[keep])
            buffers[name]["net"].append(net[keep])
            buffers[name]["positive"].append(positive[keep])
            buffers[name]["timestamp"].append(timestamp[keep])
            buffers[name]["symbol"].append(
                np.full(count, symbol_ids[str(record["symbol"])], dtype=np.int16)
            )
    output = {}
    for name, values in buffers.items():
        if not values["x"]:
            raise ValueError(f"partition is empty: {name}")
        output[name] = Partition(
            x=np.concatenate(values["x"]),
            gross=np.concatenate(values["gross"]),
            net=np.concatenate(values["net"]),
            positive=np.concatenate(values["positive"]),
            timestamp=np.concatenate(values["timestamp"]),
            symbol=np.concatenate(values["symbol"]),
        )
    return output


def standardize_on_validation(
    classifier_score: np.ndarray,
    return_score: np.ndarray,
) -> tuple[np.ndarray, dict[str, float]]:
    classifier_mean = float(np.mean(classifier_score))
    classifier_std = float(np.std(classifier_score))
    return_mean = float(np.mean(return_score))
    return_std = float(np.std(return_score))
    if classifier_std <= 0 or return_std <= 0:
        raise ValueError("model scores are degenerate")
    combined = 0.5 * (
        (classifier_score - classifier_mean) / classifier_std
        + (return_score - return_mean) / return_std
    )
    return combined, {
        "classifier_mean": classifier_mean,
        "classifier_std": classifier_std,
        "return_mean": return_mean,
        "return_std": return_std,
    }


def apply_standardization(
    classifier_score: np.ndarray,
    return_score: np.ndarray,
    values: dict[str, float],
) -> np.ndarray:
    return 0.5 * (
        (classifier_score - values["classifier_mean"]) / values["classifier_std"]
        + (return_score - values["return_mean"]) / values["return_std"]
    )


def apply_isotonic(
    scores: np.ndarray,
    blocks: list[dict[str, float]],
) -> np.ndarray:
    if not blocks:
        raise ValueError("calibration blocks are required")
    uppers = np.asarray(
        [float(block["upper_score"]) for block in blocks],
        dtype=float,
    )
    probabilities = np.asarray(
        [float(block["probability"]) for block in blocks],
        dtype=float,
    )
    indices = np.searchsorted(uppers, scores.astype(float), side="left")
    indices = np.minimum(indices, len(probabilities) - 1)
    return probabilities[indices]


def select_cross_section(
    score: np.ndarray,
    timestamp: np.ndarray,
    score_threshold: float,
    max_positions: int = MAX_POSITIONS,
) -> np.ndarray:
    """Select up to capacity only when a score clears the frozen threshold."""

    if max_positions < 1:
        raise ValueError("max_positions must be positive")
    selected = np.zeros(len(score), dtype=bool)
    order = np.argsort(timestamp, kind="stable")
    sorted_stamps = timestamp[order]
    boundaries = np.r_[0, np.flatnonzero(np.diff(sorted_stamps)) + 1, len(order)]
    for start, end in zip(boundaries[:-1], boundaries[1:]):
        group = order[start:end]
        eligible = group[score[group] >= score_threshold]
        if not len(eligible):
            continue
        count = min(max_positions, len(eligible))
        ranked = eligible[
            np.argsort(score[eligible], kind="stable")[-count:]
        ]
        selected[ranked] = True
    return selected


def max_drawdown_capital_scaled(
    net: np.ndarray,
    timestamp: np.ndarray,
    selected: np.ndarray,
    max_positions: int = MAX_POSITIONS,
) -> float:
    equity = peak = 1.0
    worst = 0.0
    for stamp in np.unique(timestamp[selected]):
        values = net[selected & (timestamp == stamp)]
        slots = max(max_positions, len(values))
        cohort_return = float(np.sum(values) / slots) / 100.0
        equity *= 1.0 + cohort_return
        peak = max(peak, equity)
        worst = min(worst, equity / peak - 1.0)
    return worst * 100.0


def metrics(
    partition: Partition,
    selected: np.ndarray | None = None,
) -> dict[str, Any]:
    mask = np.ones(len(partition.net), dtype=bool) if selected is None else selected
    values = partition.net[mask]
    if not len(values):
        return {"signals": 0}
    return {
        "signals": int(len(values)),
        "timestamps": int(len(np.unique(partition.timestamp[mask]))),
        "symbols": int(len(np.unique(partition.symbol[mask]))),
        "mean_gross_pct": float(np.mean(partition.gross[mask])),
        "median_gross_pct": float(np.median(partition.gross[mask])),
        "mean_net_pct": float(np.mean(values)),
        "median_net_pct": float(np.median(values)),
        "win_rate_pct": float(np.mean(values > 0.0) * 100.0),
        "fifth_percentile_net_pct": float(np.percentile(values, 5)),
        "worst_net_pct": float(np.min(values)),
        "largest_symbol_share_pct": float(
            np.max(np.unique(partition.symbol[mask], return_counts=True)[1])
            / len(values)
            * 100.0
        ),
        "capital_scaled_max_drawdown_pct": max_drawdown_capital_scaled(
            partition.net,
            partition.timestamp,
            mask,
        ),
    }


def calibration_metrics(
    probabilities: np.ndarray,
    partition: Partition,
) -> dict[str, float]:
    labels = partition.positive.astype(int).tolist()
    values = probabilities.astype(float).tolist()
    return {
        "brier_score": float(brier_score(values, labels)),
        "expected_calibration_error_10bin": float(
            expected_calibration_error(values, labels, bins=10)
        ),
        "mean_predicted_probability": float(np.mean(probabilities)),
        "observed_positive_rate": float(np.mean(partition.positive)),
    }


def matched_control_selection(
    values: np.ndarray,
    timestamp: np.ndarray,
    reference_selected: np.ndarray,
    *,
    descending: bool,
) -> np.ndarray:
    """Select a capacity-matched deterministic control on model-active timestamps."""

    output = np.zeros(len(values), dtype=bool)
    for stamp in np.unique(timestamp[reference_selected]):
        group = np.flatnonzero(timestamp == stamp)
        count = int(np.sum(reference_selected[group]))
        finite = group[np.isfinite(values[group])]
        if not count or not len(finite):
            continue
        order = np.argsort(values[finite], kind="stable")
        ranked = finite[order[-count:] if descending else order[:count]]
        output[ranked] = True
    return output


def policy_diagnostics(
    partition: Partition,
    selected: np.ndarray,
    probabilities: np.ndarray,
    feature_names: list[str],
) -> dict[str, Any]:
    minute = partition.x[:, feature_names.index("minute_of_session")]
    qqq_session = partition.x[
        :, feature_names.index("qqq_session_return_pct")
    ]
    time_masks = {
        "opening_90m": minute < 90,
        "middle_session": (minute >= 90) & (minute < 300),
        "closing_90m": minute >= 300,
    }
    regime_masks = {
        "qqq_down_more_than_0_25pct": qqq_session < -0.25,
        "qqq_between_minus_0_25_and_plus_0_25pct": (
            (qqq_session >= -0.25) & (qqq_session <= 0.25)
        ),
        "qqq_up_more_than_0_25pct": qqq_session > 0.25,
    }
    controls = {}
    for name, descending in (
        ("momentum_5m", True),
        ("mean_reversion_5m", False),
        ("qqq_relative_5m", True),
    ):
        feature = (
            "relative_to_qqq_5m_pct"
            if name == "qqq_relative_5m"
            else "return_5m_pct"
        )
        control = matched_control_selection(
            partition.x[:, feature_names.index(feature)],
            partition.timestamp,
            selected,
            descending=descending,
        )
        controls[name] = metrics(partition, control)
    selected_probabilities = probabilities[selected]
    return {
        "abstained_timestamps": int(
            len(np.unique(partition.timestamp))
            - len(np.unique(partition.timestamp[selected]))
        ),
        "time_of_day": {
            name: metrics(partition, selected & mask)
            for name, mask in time_masks.items()
        },
        "qqq_regime": {
            name: metrics(partition, selected & mask)
            for name, mask in regime_masks.items()
        },
        "capacity_matched_controls": controls,
        "selected_probability": (
            {
                "mean": float(np.mean(selected_probabilities)),
                "median": float(np.median(selected_probabilities)),
                "mean_uncertainty": float(
                    np.mean(1.0 - np.abs(2.0 * selected_probabilities - 1.0))
                ),
            }
            if len(selected_probabilities)
            else {"signals": 0}
        ),
    }


def choose_threshold(
    partition: Partition,
    score: np.ndarray,
    calibration_score: np.ndarray,
) -> tuple[float | None, list[dict[str, Any]]]:
    rows = []
    chosen = None
    chosen_key = None
    for percentile in POLICY_SCORE_PERCENTILES:
        threshold = float(np.percentile(calibration_score, percentile))
        selected = select_cross_section(
            score,
            partition.timestamp,
            threshold,
        )
        result = {
            "score_percentile": percentile,
            "score_threshold": threshold,
            **metrics(partition, selected),
        }
        passes = (
            result["signals"] >= MIN_POLICY_SELECTIONS
            and result.get("mean_net_pct", float("-inf")) > 0
            and result.get("median_net_pct", float("-inf")) > 0
            and result.get("win_rate_pct", 0.0) >= 52.0
            and result.get("capital_scaled_max_drawdown_pct", -100.0) >= -20.0
            and result.get("largest_symbol_share_pct", 100.0) <= 20.0
        )
        result["passes_gate"] = passes
        rows.append(result)
        key = (
            result.get("mean_net_pct", float("-inf")),
            result.get("median_net_pct", float("-inf")),
            result.get("win_rate_pct", 0.0),
        )
        if passes and (chosen_key is None or key > chosen_key):
            chosen, chosen_key = threshold, key
    return chosen, rows


def load_test_partition_after_gate(
    manifest: dict[str, Any],
    panel_root: Path,
    splits: dict[str, set[np.datetime64]],
    chosen_threshold: float | None,
) -> Partition | None:
    """Keep test labels and features unopened until policy validation passes."""

    if chosen_threshold is None:
        return None
    return load_partitions(
        manifest,
        panel_root,
        splits,
        ("test",),
    )["test"]


def train(panel_root: Path, output_root: Path) -> dict[str, Any]:
    if output_root.exists():
        if not output_root.is_dir() or any(output_root.iterdir()):
            raise FileExistsError(
                "output_root must be an empty directory; horizon models may "
                "never overwrite artifacts"
            )
    manifest_path = panel_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "complete" or manifest.get("failed"):
        raise ValueError("compiled panel must be complete with zero failures")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("compiled panel schema version is not supported")
    if manifest.get("timestamp_unit") != TIMESTAMP_UNIT:
        raise ValueError("compiled panel timestamp unit is not nanoseconds")
    if manifest.get("entry_assumption") != ENTRY_ASSUMPTION:
        raise ValueError("compiled panel does not use executable next-minute entry")
    if manifest.get("horizon_minutes") not in ALLOWED_HORIZON_MINUTES:
        raise ValueError("compiled panel has an unsupported horizon")
    target_symbols = list(manifest.get("target_symbols") or [])
    if (
        not target_symbols
        or target_symbols != sorted(set(target_symbols))
        or manifest.get("target_symbols_count") != len(target_symbols)
        or manifest.get("target_symbols_sha256")
        != hashlib.sha256(
            ("\n".join(target_symbols) + "\n").encode("utf-8")
        ).hexdigest()
    ):
        raise ValueError("compiled panel target-universe contract is invalid")
    panel_integrity = validate_compiled_panel_files(manifest, panel_root)
    dates = discover_dates(manifest, panel_root)
    splits = split_market_dates(dates)
    partitions = load_partitions(
        manifest,
        panel_root,
        splits,
        ("train", "fit_validation", "calibration", "policy_validation"),
    )

    train_set = lgb.Dataset(
        partitions["train"].x,
        label=partitions["train"].positive,
        feature_name=list(manifest["feature_names"]),
        free_raw_data=False,
    )
    fit_validation_set = lgb.Dataset(
        partitions["fit_validation"].x,
        label=partitions["fit_validation"].positive,
        feature_name=list(manifest["feature_names"]),
        reference=train_set,
        free_raw_data=False,
    )
    shared = {
        "learning_rate": 0.04,
        "num_leaves": 31,
        "min_data_in_leaf": 1000,
        "feature_fraction": 0.85,
        "bagging_fraction": 0.80,
        "bagging_freq": 1,
        "lambda_l1": 0.2,
        "lambda_l2": 1.0,
        "verbosity": -1,
        "num_threads": 0,
        "seed": 8010,
    }
    classifier = lgb.train(
        {**shared, "objective": "binary", "metric": "binary_logloss"},
        train_set,
        num_boost_round=600,
        valid_sets=[fit_validation_set],
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(25)],
    )
    regression_train = lgb.Dataset(
        partitions["train"].x,
        label=partitions["train"].net,
        feature_name=list(manifest["feature_names"]),
        free_raw_data=False,
    )
    regression_fit_validation = lgb.Dataset(
        partitions["fit_validation"].x,
        label=partitions["fit_validation"].net,
        feature_name=list(manifest["feature_names"]),
        reference=regression_train,
        free_raw_data=False,
    )
    regressor = lgb.train(
        {**shared, "objective": "huber", "metric": "l1"},
        regression_train,
        num_boost_round=600,
        valid_sets=[regression_fit_validation],
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(25)],
    )

    calibration_raw_probability = classifier.predict(partitions["calibration"].x)
    isotonic_blocks = fit_isotonic(
        calibration_raw_probability.astype(float).tolist(),
        partitions["calibration"].positive.astype(int).tolist(),
    )
    calibration_probability = apply_isotonic(
        calibration_raw_probability,
        isotonic_blocks,
    )
    calibration_return = regressor.predict(partitions["calibration"].x)
    calibration_score, standardization = standardize_on_validation(
        calibration_probability,
        calibration_return,
    )

    policy_raw_probability = classifier.predict(
        partitions["policy_validation"].x
    )
    policy_probability = apply_isotonic(
        policy_raw_probability,
        isotonic_blocks,
    )
    policy_return = regressor.predict(partitions["policy_validation"].x)
    policy_score = apply_standardization(
        policy_probability,
        policy_return,
        standardization,
    )
    chosen_threshold, policy_grid = choose_threshold(
        partitions["policy_validation"],
        policy_score,
        calibration_score,
    )
    feature_name_list = list(manifest["feature_names"])
    policy_selected = (
        select_cross_section(
            policy_score,
            partitions["policy_validation"].timestamp,
            chosen_threshold,
        )
        if chosen_threshold is not None
        else np.zeros(len(policy_score), dtype=bool)
    )
    policy_stability = policy_diagnostics(
        partitions["policy_validation"],
        policy_selected,
        policy_probability,
        feature_name_list,
    )

    test_result: dict[str, Any]
    test_row_count: int | str = "SEALED_UNLOADED"
    if chosen_threshold is None:
        test_result = {
            "opened": False,
            "loaded": False,
            "reason": "no policy-validation threshold passed",
        }
    else:
        test_partition = load_test_partition_after_gate(
            manifest,
            panel_root,
            splits,
            chosen_threshold,
        )
        assert test_partition is not None
        test_row_count = len(test_partition.net)
        test_raw_probability = classifier.predict(test_partition.x)
        test_probability = apply_isotonic(
            test_raw_probability,
            isotonic_blocks,
        )
        test_return = regressor.predict(test_partition.x)
        test_score = apply_standardization(
            test_probability,
            test_return,
            standardization,
        )
        test_selected = select_cross_section(
            test_score,
            test_partition.timestamp,
            chosen_threshold,
        )
        test_result = {
            "opened": True,
            "loaded": True,
            "score_threshold": chosen_threshold,
            **metrics(test_partition, test_selected),
            "calibration": calibration_metrics(
                test_probability,
                test_partition,
            ),
            "diagnostics": policy_diagnostics(
                test_partition,
                test_selected,
                test_probability,
                feature_name_list,
            ),
        }

    output_root.mkdir(parents=True, exist_ok=True)
    classifier_path = output_root / "classifier.txt"
    regressor_path = output_root / "return_regressor.txt"
    classifier.save_model(str(classifier_path))
    regressor.save_model(str(regressor_path))
    test_promising = (
        test_result.get("opened")
        and test_result.get("mean_net_pct", 0) > 0
        and test_result.get("median_net_pct", 0) > 0
        and test_result.get("win_rate_pct", 0) >= 52.0
        and test_result.get("capital_scaled_max_drawdown_pct", -100) >= -20.0
        and test_result.get("largest_symbol_share_pct", 100) <= 20.0
    )
    partial_snapshot = bool(manifest.get("partial_snapshot"))
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": (
            "PARTIAL_PIPELINE_PILOT_ONLY"
            if partial_snapshot
            else (
                "RESEARCH_PROMISING_PENDING_PROSPECTIVE"
                if test_promising
                else "RESEARCH_HOLD"
            )
        ),
        "research_only": True,
        "execution_enabled": False,
        "partial_snapshot": partial_snapshot,
        "partial_snapshot_warning": (
            "Pipeline validation only; never compare, promote, freeze, or trade "
            "this model. Repeat from the complete audited archive."
            if partial_snapshot
            else None
        ),
        "source_panel_manifest_sha256": sha256(manifest_path),
        "source_panel_integrity": panel_integrity,
        "target_symbols": list(manifest["target_symbols"]),
        "target_symbols_count": int(manifest["target_symbols_count"]),
        "target_symbols_sha256": str(manifest["target_symbols_sha256"]),
        "universe_design": (
            "fixed contemporary research basket; historical results retain "
            "survivorship/selection bias"
        ),
        "promotion_limit": (
            "retrospective passage alone is insufficient; source-compatible "
            "prospective evidence is required"
        ),
        "horizon_minutes": int(manifest["horizon_minutes"]),
        "round_trip_cost_pct": float(manifest["round_trip_cost_pct"]),
        "entry_assumption": ENTRY_ASSUMPTION,
        "feature_names": list(manifest["feature_names"]),
        "sampling": (
            "one non-overlapping horizon-length phase per date; "
            "phase rotates by date"
        ),
        "embargo_sessions": EMBARGO_SESSIONS,
        "date_counts": {name: len(values) for name, values in splits.items()},
        "row_counts": {
            **{name: len(value.net) for name, value in partitions.items()},
            "test": test_row_count,
        },
        "fit_validation_all_rows": metrics(partitions["fit_validation"]),
        "calibration_all_rows": metrics(partitions["calibration"]),
        "calibration_quality": calibration_metrics(
            calibration_probability,
            partitions["calibration"],
        ),
        "policy_validation_all_rows": metrics(
            partitions["policy_validation"]
        ),
        "policy_validation_calibration": calibration_metrics(
            policy_probability,
            partitions["policy_validation"],
        ),
        "policy_grid": policy_grid,
        "chosen_score_threshold": chosen_threshold,
        "policy_validation_diagnostics": policy_stability,
        "test": test_result,
        "standardization": standardization,
        "isotonic_calibration_blocks": isotonic_blocks,
        "classifier_path": str(classifier_path),
        "classifier_sha256": sha256(classifier_path),
        "regressor_path": str(regressor_path),
        "regressor_sha256": sha256(regressor_path),
    }
    report_path = output_root / "training_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(train(args.panel_root, args.output_root), indent=2))


if __name__ == "__main__":
    main()
