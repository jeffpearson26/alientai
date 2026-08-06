from __future__ import annotations

"""Produce a label-free daily ranking from a trained five-session picker."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np

from alientai_v2.research.cross_sectional_picker_5d import (
    build_daily_snapshot,
    date_local_score_percentiles,
    feature_matrix,
    passes_configured_filters,
    ranked_feature_names,
    selected_indices,
)
from build_nasdaq_qqq_spy_60session_panel import load_adjusted_daily
from train_cross_sectional_picker_5d import load_config


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_symbols(path: Path) -> list[str]:
    symbols = [
        line.strip().upper()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not symbols or len(symbols) != len(set(symbols)):
        raise ValueError(f"invalid symbol file: {path}")
    return symbols


def validate_archive(root: Path, required: list[str]) -> dict[str, Any]:
    path = root / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    completed = set(manifest.get("completed") or [])
    if (
        manifest.get("status") != "complete"
        or manifest.get("failed")
        or manifest.get("function") != "TIME_SERIES_DAILY_ADJUSTED"
        or manifest.get("outputsize") != "full"
    ):
        raise ValueError(f"daily archive is not complete adjusted data: {path}")
    missing = sorted(set(required) - completed)
    if missing:
        raise ValueError(f"archive missing symbols: {missing}")
    return {
        "path": str(path),
        "sha256": sha256(path),
        "required_symbols": required,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path)
    parser.add_argument("--as-of-date")
    parser.add_argument(
        "--research-preview",
        action="store_true",
        help="Allow AVOID-only rankings from a RESEARCH_HOLD model.",
    )
    args = parser.parse_args()
    config = load_config(args.config)
    report_path = args.model_root / "training_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if (
        report.get("model_id") != config["model_id"]
        or report.get("config_sha256") != sha256(args.config)
        or report.get("feature_names") != ranked_feature_names()
    ):
        raise ValueError("model/config/feature contract mismatch")
    if (
        report.get("status") != "RESEARCH_CANDIDATE"
        and not args.research_preview
    ):
        raise ValueError(
            "model is not a research candidate; use --research-preview "
            "for explicitly AVOID-only diagnostics"
        )
    model_path = Path(report["model"])
    if sha256(model_path) != report["model_sha256"]:
        raise ValueError("model fingerprint mismatch")

    data = config["data"]
    nasdaq_path = Path(data["nasdaq_symbols"])
    ai_path = Path(data["ai_symbols"])
    primary_root = Path(data["primary_daily_root"])
    supplement_root = Path(data["ai_supplement_daily_root"])
    candidates = sorted(set(read_symbols(nasdaq_path)) | set(read_symbols(ai_path)))
    context = ["QQQ", "SPY"]
    primary_available = {
        path.name.removesuffix("_daily.json")
        for path in primary_root.glob("*_daily.json")
    }
    primary_symbols = sorted(
        symbol
        for symbol in [*candidates, *context]
        if symbol in primary_available
    )
    supplement_symbols = sorted(set(candidates) - set(primary_symbols))
    primary_contract = validate_archive(primary_root, primary_symbols)
    supplement_contract = validate_archive(
        supplement_root, supplement_symbols
    )
    daily = {}
    source_files = {}
    for symbol in [*candidates, *context]:
        root = (
            primary_root
            if symbol in primary_available
            else supplement_root
        )
        path = root / f"{symbol}_daily.json"
        daily[symbol] = load_adjusted_daily(path)
        source_files[symbol] = {
            "path": str(path),
            "sha256": sha256(path),
        }
    rows, coverage = build_daily_snapshot(
        daily,
        candidates,
        as_of_date=args.as_of_date,
        minimum_cross_sectional_coverage=float(
            data["minimum_cross_sectional_coverage"]
        ),
    )
    eligible_indices = [
        index
        for index, row in enumerate(rows)
        if passes_configured_filters(row, config["filters"])
    ]
    eligible_rows = [rows[index] for index in eligible_indices]
    if not eligible_rows:
        raise ValueError("no liquid/risk-eligible rows in daily snapshot")
    booster = lgb.Booster(model_file=str(model_path))
    scores = np.asarray(
        booster.predict(
            feature_matrix(eligible_rows, ranked_feature_names())
        ),
        dtype=float,
    )
    percentiles = date_local_score_percentiles(eligible_rows, scores)
    selection = config["selection"]
    chosen_indices, diagnostics = selected_indices(
        eligible_rows,
        scores,
        top_quantile=float(selection["top_quantile"]),
        maximum_names=int(selection["maximum_names"]),
    )
    chosen_set = set(chosen_indices)
    ranked = []
    for index, (row, score, percentile) in enumerate(
        zip(eligible_rows, scores, percentiles)
    ):
        ranked.append(
            {
                "symbol": row["symbol"],
                "model_score": float(score),
                "score_cross_sectional_percentile": float(percentile),
                "transparent_composite_score": row[
                    "x5_transparent_composite_score"
                ],
                "atr_14_pct": row["x5_atr_14_pct"],
                "relative_volume_20d": row["x5_relative_volume_20d"],
                "average_dollar_volume_20d": row[
                    "x5_average_dollar_volume_20d"
                ],
                "selected_for_research_observation": index in chosen_set,
                "execution_decision": "AVOID",
            }
        )
    ranked.sort(
        key=lambda row: (
            -float(row["model_score"]),
            str(row["symbol"]),
        )
    )
    for rank, row in enumerate(ranked, start=1):
        row["rank"] = rank
    output = {
        "schema_version": 1,
        "status": (
            "RESEARCH_RANKING"
            if report["status"] == "RESEARCH_CANDIDATE"
            else "RESEARCH_PREVIEW_HOLD"
        ),
        "research_only": True,
        "execution_enabled": False,
        "execution_decision": "AVOID",
        "model_id": config["model_id"],
        "model_status": report["status"],
        "model_sha256": report["model_sha256"],
        "decision_date": coverage["decision_date"],
        "horizon_sessions": 5,
        "feature_available_at": (
            f"{coverage['decision_date']} completed regular close"
        ),
        "entry_contract": "next complete regular-session adjusted open",
        "exit_contract": "fifth subsequent regular-session adjusted close",
        "selection_policy": selection,
        "selection_diagnostics": diagnostics,
        "coverage": coverage,
        "eligible_count": len(eligible_rows),
        "selected_symbols": [
            row["symbol"]
            for row in ranked
            if row["selected_for_research_observation"]
        ],
        "ranked": ranked,
        "source_contract": {
            "primary": primary_contract,
            "supplement": supplement_contract,
            "files": source_files,
        },
        "limitations": report.get("limitations", []),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8"
    )
    if args.output_csv:
        args.output_csv.parent.mkdir(parents=True, exist_ok=True)
        with args.output_csv.open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "rank",
                    "symbol",
                    "model_score",
                    "score_cross_sectional_percentile",
                    "transparent_composite_score",
                    "atr_14_pct",
                    "relative_volume_20d",
                    "average_dollar_volume_20d",
                    "selected_for_research_observation",
                    "execution_decision",
                ],
            )
            writer.writeheader()
            writer.writerows(ranked)
    print(
        json.dumps(
            {
                "status": output["status"],
                "decision_date": output["decision_date"],
                "eligible_count": output["eligible_count"],
                "selected_symbols": output["selected_symbols"],
                "output_json": str(args.output_json),
                "output_csv": (
                    None if args.output_csv is None else str(args.output_csv)
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
