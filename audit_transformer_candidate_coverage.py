from __future__ import annotations

"""Isolated, read-only coverage and score-distribution audit for a Transformer candidate."""

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import torch

from alientai_v2.engines.transformer_20day import TimeSeriesTransformer, apply_scaler, build_latest_sequence


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def load_candles(path: Path) -> list[dict[str, Any]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def make_model(config: dict[str, Any], model_path: Path) -> TimeSeriesTransformer:
    model = TimeSeriesTransformer(
        input_size=int(config["input_size"]), sequence_length=int(config["sequence_length"]),
        d_model=int(config["d_model"]), nhead=int(config["heads"]), num_layers=int(config["layers"]),
        dim_feedforward=int(config["d_model"]) * 2, dropout=float(config["dropout"]),
    )
    model.load_state_dict(torch.load(model_path, map_location="cpu"))
    model.eval()
    return model


def latest_date(candles: Sequence[dict[str, Any]]) -> str:
    return str(candles[-1].get("date") or candles[-1].get("datetime") or "") if candles else ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit candidate Transformer compatibility without changing runtime.")
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--daily-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = load_json(args.candidate_dir / f"{args.prefix}_config.json")
    scaler = load_json(args.candidate_dir / f"{args.prefix}_scaler.json")
    model = make_model(config, args.candidate_dir / f"{args.prefix}_model.pt")
    symbols = [str(value).upper() for value in config.get("symbols_used", [])]
    minimum = int(config.get("min_history_days") or config["sequence_length"])
    sequences, dates, missing, insufficient = [], [], [], []
    for symbol in symbols:
        path = args.daily_dir / f"{symbol}_schwab_1d_max.csv"
        if not path.exists():
            missing.append(symbol)
            continue
        candles = load_candles(path)
        if len(candles) < minimum:
            insufficient.append(symbol)
            continue
        sequence = build_latest_sequence(candles, int(config["sequence_length"]))
        if sequence is None:
            insufficient.append(symbol)
            continue
        sequences.append(sequence.squeeze(0))
        dates.append(latest_date(candles))
    if not sequences:
        raise ValueError("no candidate symbols have compatible local sequences")
    x = apply_scaler(torch.stack(sequences), scaler)
    with torch.no_grad():
        scores = torch.sigmoid(model(x)).cpu().numpy()
    report = {
        "status": "complete", "research_only": True, "execution_enabled": False,
        "warning": "Coverage and distribution audit only. No symbols, candidates, or orders are emitted.",
        "candidate_build": config.get("build"), "candidate_symbols": len(symbols), "scored_sequences": len(scores),
        "missing_local_files": len(missing), "insufficient_history": len(insufficient),
        "latest_date_min": min(dates), "latest_date_max": max(dates),
        "score_distribution": {"min": float(np.min(scores)), "p05": float(np.quantile(scores, 0.05)),
                               "median": float(np.median(scores)), "p95": float(np.quantile(scores, 0.95)), "max": float(np.max(scores))},
        "compatibility": "READY_FOR_SEPARATE_HOLDOUT_REVIEW",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
