from __future__ import annotations

"""Train and evaluate the research-only any-time 20-minute LightGBM model."""

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import lightgbm as lgb
import numpy as np


FRACTIONS = (0.005, 0.01, 0.02, 0.05, 0.10)
MAX_POSITIONS = 5
MIN_VALIDATION_SELECTIONS = 1000
EMBARGO_SESSIONS = 5
SCHEMA_VERSION = 1


@dataclass
class Partition:
    x: np.ndarray
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


def split_market_dates(
    market_dates: Iterable[np.datetime64],
) -> dict[str, set[np.datetime64]]:
    dates = np.array(sorted(set(market_dates)), dtype="datetime64[D]")
    if len(dates) < 100:
        raise ValueError("at least 100 market dates are required")
    train_end = int(len(dates) * 0.60)
    validation_end = int(len(dates) * 0.80)
    if train_end <= EMBARGO_SESSIONS or validation_end - train_end <= 2 * EMBARGO_SESSIONS:
        raise ValueError("insufficient dates after embargo")
    return {
        "train": set(dates[:train_end]),
        "validation": set(
            dates[train_end + EMBARGO_SESSIONS : validation_end]
        ),
        "test": set(dates[validation_end + EMBARGO_SESSIONS :]),
        "embargo": set(
            np.concatenate(
                [
                    dates[train_end : train_end + EMBARGO_SESSIONS],
                    dates[validation_end : validation_end + EMBARGO_SESSIONS],
                ]
            )
        ),
    }


def rotating_nonoverlap_mask(
    timestamps_ns: np.ndarray,
    minute_of_session: np.ndarray,
) -> np.ndarray:
    dates = timestamps_ns.astype("datetime64[ns]").astype("datetime64[D]")
    date_numbers = dates.astype(np.int64)
    offsets = np.mod(date_numbers, 20)
    return np.mod(minute_of_session.astype(np.int64), 20) == offsets


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
) -> dict[str, Partition]:
    feature_names = list(manifest["feature_names"])
    minute_index = feature_names.index("minute_of_session")
    buffers: dict[str, dict[str, list[np.ndarray]]] = {
        name: {field: [] for field in ("x", "net", "positive", "timestamp", "symbol")}
        for name in ("train", "validation", "test")
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
            net = shard["net"].astype(np.float32)
            positive = shard["positive"].astype(np.float32)
            timestamp = shard["timestamp"].astype(np.int64)
        sample_mask = rotating_nonoverlap_mask(timestamp, x[:, minute_index])
        dates = timestamp.astype("datetime64[ns]").astype("datetime64[D]")
        for name in buffers:
            allowed = np.isin(dates, list(date_splits[name]))
            keep = sample_mask & allowed
            count = int(keep.sum())
            if not count:
                continue
            buffers[name]["x"].append(x[keep])
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


def select_cross_section(
    score: np.ndarray,
    timestamp: np.ndarray,
    fraction: float,
    max_positions: int = MAX_POSITIONS,
) -> np.ndarray:
    selected = np.zeros(len(score), dtype=bool)
    order = np.argsort(timestamp, kind="stable")
    sorted_stamps = timestamp[order]
    boundaries = np.r_[0, np.flatnonzero(np.diff(sorted_stamps)) + 1, len(order)]
    for start, end in zip(boundaries[:-1], boundaries[1:]):
        group = order[start:end]
        count = min(max_positions, max(1, int(math.ceil(len(group) * fraction))))
        ranked = group[np.argsort(score[group], kind="stable")[-count:]]
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
        "mean_net_pct": float(np.mean(values)),
        "median_net_pct": float(np.median(values)),
        "win_rate_pct": float(np.mean(values > 0.0) * 100.0),
        "fifth_percentile_net_pct": float(np.percentile(values, 5)),
        "worst_net_pct": float(np.min(values)),
        "capital_scaled_max_drawdown_pct": max_drawdown_capital_scaled(
            partition.net,
            partition.timestamp,
            mask,
        ),
    }


def choose_fraction(
    partition: Partition,
    score: np.ndarray,
) -> tuple[float | None, list[dict[str, Any]]]:
    rows = []
    chosen = None
    chosen_key = None
    for fraction in FRACTIONS:
        selected = select_cross_section(score, partition.timestamp, fraction)
        result = {"fraction": fraction, **metrics(partition, selected)}
        passes = (
            result["signals"] >= MIN_VALIDATION_SELECTIONS
            and result["mean_net_pct"] > 0
            and result["median_net_pct"] > 0
            and result["win_rate_pct"] >= 52.0
            and result["capital_scaled_max_drawdown_pct"] >= -20.0
        )
        result["passes_gate"] = passes
        rows.append(result)
        key = (
            result["mean_net_pct"],
            result["median_net_pct"],
            result["win_rate_pct"],
        )
        if passes and (chosen_key is None or key > chosen_key):
            chosen, chosen_key = fraction, key
    return chosen, rows


def train(panel_root: Path, output_root: Path) -> dict[str, Any]:
    manifest_path = panel_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "complete" or manifest.get("failed"):
        raise ValueError("compiled panel must be complete with zero failures")
    dates = discover_dates(manifest, panel_root)
    splits = split_market_dates(dates)
    partitions = load_partitions(manifest, panel_root, splits)

    train_set = lgb.Dataset(
        partitions["train"].x,
        label=partitions["train"].positive,
        feature_name=list(manifest["feature_names"]),
        free_raw_data=False,
    )
    validation_set = lgb.Dataset(
        partitions["validation"].x,
        label=partitions["validation"].positive,
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
        valid_sets=[validation_set],
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(25)],
    )
    regression_train = lgb.Dataset(
        partitions["train"].x,
        label=partitions["train"].net,
        feature_name=list(manifest["feature_names"]),
        free_raw_data=False,
    )
    regression_validation = lgb.Dataset(
        partitions["validation"].x,
        label=partitions["validation"].net,
        feature_name=list(manifest["feature_names"]),
        reference=regression_train,
        free_raw_data=False,
    )
    regressor = lgb.train(
        {**shared, "objective": "huber", "metric": "l1"},
        regression_train,
        num_boost_round=600,
        valid_sets=[regression_validation],
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(25)],
    )

    validation_classifier = classifier.predict(partitions["validation"].x)
    validation_return = regressor.predict(partitions["validation"].x)
    validation_score, standardization = standardize_on_validation(
        validation_classifier,
        validation_return,
    )
    chosen_fraction, validation_grid = choose_fraction(
        partitions["validation"],
        validation_score,
    )

    test_classifier = classifier.predict(partitions["test"].x)
    test_return = regressor.predict(partitions["test"].x)
    test_score = apply_standardization(
        test_classifier,
        test_return,
        standardization,
    )
    test_result: dict[str, Any]
    if chosen_fraction is None:
        test_result = {"opened": False, "reason": "no validation policy passed"}
    else:
        test_selected = select_cross_section(
            test_score,
            partitions["test"].timestamp,
            chosen_fraction,
        )
        test_result = {
            "opened": True,
            "fraction": chosen_fraction,
            **metrics(partitions["test"], test_selected),
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
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": (
            "RESEARCH_PROMISING_PENDING_PROSPECTIVE"
            if test_promising
            else "RESEARCH_HOLD"
        ),
        "research_only": True,
        "execution_enabled": False,
        "source_panel_manifest_sha256": sha256(manifest_path),
        "feature_names": list(manifest["feature_names"]),
        "sampling": "one non-overlapping 20-minute phase per date; phase rotates by date",
        "embargo_sessions": EMBARGO_SESSIONS,
        "date_counts": {name: len(values) for name, values in splits.items()},
        "row_counts": {name: len(value.net) for name, value in partitions.items()},
        "validation_all_rows": metrics(partitions["validation"]),
        "validation_grid": validation_grid,
        "chosen_fraction": chosen_fraction,
        "test": test_result,
        "standardization": standardization,
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
