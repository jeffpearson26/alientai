from __future__ import annotations

"""Train a research-only, natural-universe technical context model.

The model is intentionally limited to the point-in-time ``technical_*`` fields
emitted by ``build_daily_technical_panel.py``.  It never writes candidates or
touches execution settings.
"""

import argparse
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from alientai_v2.features.insider_purchase_features import safe_float


TARGET = "label_forward_return_5d_pct"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def technical_feature_names(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    """Return only nonconstant point-in-time technical features."""
    names = sorted({name for row in rows for name in row if name.startswith("technical_")})
    return [
        name for name in names
        if len({safe_float(row.get(name)) for row in rows if row.get(name) is not None}) > 1
    ]


def matrix(rows: Sequence[Mapping[str, Any]], names: Sequence[str]) -> np.ndarray:
    if not names:
        raise ValueError("at least one technical feature is required")
    return np.column_stack([
        np.asarray([safe_float(row.get(name)) for row in rows], dtype=np.float32)
        for name in names
    ])


def chronological_split(rows: Sequence[Mapping[str, Any]], train_fraction: float, validation_fraction: float,
                        embargo_days: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, str]]:
    if not 0 < train_fraction < 1 or not 0 < validation_fraction < 1 or train_fraction + validation_fraction >= 1:
        raise ValueError("train and validation fractions must be positive and total less than one")
    days = sorted({date.fromisoformat(str(row["market_date"])) for row in rows})
    if len(days) < 30:
        raise ValueError("at least 30 market dates are required")
    train_end = days[max(0, int(len(days) * train_fraction) - 1)]
    validation_end = days[max(0, int(len(days) * (train_fraction + validation_fraction)) - 1)]
    validation_start = train_end + timedelta(days=embargo_days)
    test_start = validation_end + timedelta(days=embargo_days)
    train, validation, test = [], [], []
    for index, row in enumerate(rows):
        day = date.fromisoformat(str(row["market_date"]))
        if day <= train_end:
            train.append(index)
        elif validation_start <= day <= validation_end:
            validation.append(index)
        elif day >= test_start:
            test.append(index)
    if not train or not validation or not test:
        raise ValueError("chronological split with embargo produced an empty partition")
    return (np.asarray(train), np.asarray(validation), np.asarray(test), {
        "train_end": train_end.isoformat(), "validation_start": validation_start.isoformat(),
        "validation_end": validation_end.isoformat(), "test_start": test_start.isoformat(),
    })


def metrics(labels: np.ndarray, scores: np.ndarray) -> dict[str, Any]:
    order = np.argsort(-scores)
    top = {}
    for fraction in (0.001, 0.0025, 0.005, 0.01):
        count = max(1, int(len(order) * fraction))
        selected = order[:count]
        top[str(fraction)] = {"count": int(count), "winner_rate": round(float(np.mean(labels[selected])), 6)}
    return {"rows": int(len(labels)), "base_rate": round(float(np.mean(labels)), 6), "top_fractions": top}


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a natural-universe technical context model (research only).")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--winner-return-pct", type=float, default=10.0)
    parser.add_argument("--target", default=TARGET)
    parser.add_argument("--train-fraction", type=float, default=0.60)
    parser.add_argument("--validation-fraction", type=float, default=0.20)
    parser.add_argument("--embargo-calendar-days", type=int, default=12)
    parser.add_argument("--num-boost-round", type=int, default=800)
    parser.add_argument("--early-stopping-rounds", type=int, default=60)
    args = parser.parse_args()

    rows = [row for row in read_jsonl(args.input) if row.get(args.target) is not None and row.get("market_date")]
    names = technical_feature_names(rows)
    x = matrix(rows, names)
    y = np.asarray([safe_float(row[args.target]) >= args.winner_return_pct for row in rows], dtype=np.int32)
    train_idx, validation_idx, test_idx, split = chronological_split(
        rows, args.train_fraction, args.validation_fraction, args.embargo_calendar_days,
    )
    train = lgb.Dataset(x[train_idx], label=y[train_idx], feature_name=names)
    validation = lgb.Dataset(x[validation_idx], label=y[validation_idx], reference=train, feature_name=names)
    model = lgb.train(
        {"objective": "binary", "metric": ["binary_logloss", "auc"], "learning_rate": 0.025,
         "num_leaves": 31, "min_data_in_leaf": 100, "feature_fraction": 0.85,
         "lambda_l1": 2.0, "lambda_l2": 8.0, "verbosity": -1, "seed": 42, "force_col_wise": True},
        train, num_boost_round=args.num_boost_round, valid_sets=[validation], valid_names=["validation"],
        callbacks=[lgb.early_stopping(args.early_stopping_rounds), lgb.log_evaluation(50)],
    )
    predict = lambda indexes: model.predict(x[indexes], num_iteration=model.best_iteration)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    model_path = args.output_dir / "natural_technical_context_classifier.txt"
    model.save_model(str(model_path), num_iteration=model.best_iteration)
    importance = sorted(
        ({"feature": name, "gain": float(gain)} for name, gain in zip(names, model.feature_importance(importance_type="gain"))),
        key=lambda item: item["gain"], reverse=True,
    )
    report = {
        "status": "complete", "research_only": True, "execution_enabled": False,
        "warning": "Scores are uncalibrated research ranks, not trading recommendations or promised probabilities.",
        "input": str(args.input), "rows": len(rows), "target": args.target,
        "winner_return_pct": args.winner_return_pct,
        "feature_names": names, "best_iteration": int(model.best_iteration), "split": split,
        "train": metrics(y[train_idx], predict(train_idx)), "validation": metrics(y[validation_idx], predict(validation_idx)),
        "test": metrics(y[test_idx], predict(test_idx)), "top_features": importance[:30], "model_path": str(model_path),
    }
    report_path = args.output_dir / "natural_technical_context_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
