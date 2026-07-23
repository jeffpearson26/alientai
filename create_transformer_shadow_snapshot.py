from __future__ import annotations

"""Create a non-executing forward journal snapshot for a reviewed Transformer artifact."""

import argparse
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import torch

from alientai_v2.engines.transformer_20day import apply_scaler, build_latest_sequence
from audit_transformer_candidate_coverage import load_candles, load_json, latest_date, make_model


def record(symbol: str, as_of_date: str, score: float, horizon_days: int) -> dict[str, Any]:
    return {
        "symbol": symbol, "as_of_date": as_of_date, "technical_context_score": score,
        "horizon_calendar_days": horizon_days, "outcome_not_due_before": (
            date.fromisoformat(as_of_date) + timedelta(days=horizon_days + 8)
        ).isoformat(),
        "research_only": True, "execution_enabled": False,
        "decision": "SHADOW_JOURNAL_ONLY",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a forward-only Transformer shadow snapshot.")
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--daily-dir", type=Path, required=True)
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--minimum-score", type=float, default=0.60)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 0 < args.minimum_score < 1:
        raise ValueError("minimum score must be in (0, 1)")
    config = load_json(args.candidate_dir / f"{args.prefix}_config.json")
    scaler = load_json(args.candidate_dir / f"{args.prefix}_scaler.json")
    model = make_model(config, args.candidate_dir / f"{args.prefix}_model.pt")
    minimum_history = int(config.get("min_history_days") or config["sequence_length"])
    sequences, symbols, excluded_stale, excluded_missing = [], [], 0, 0
    for symbol in [str(item).upper() for item in config.get("symbols_used", [])]:
        path = args.daily_dir / f"{symbol}_schwab_1d_max.csv"
        if not path.exists():
            excluded_missing += 1
            continue
        candles = load_candles(path)
        if len(candles) < minimum_history or latest_date(candles) != args.as_of_date:
            excluded_stale += 1
            continue
        sequence = build_latest_sequence(candles, int(config["sequence_length"]))
        if sequence is None:
            excluded_stale += 1
            continue
        sequences.append(sequence.squeeze(0)); symbols.append(symbol)
    if not sequences:
        raise ValueError("no fresh compatible sequences for requested as-of date")
    x = apply_scaler(torch.stack(sequences), scaler)
    with torch.no_grad():
        scores = torch.sigmoid(model(x)).cpu().tolist()
    horizon = int(config.get("horizon_days") or 20)
    selected = [record(symbol, args.as_of_date, float(score), horizon) for symbol, score in zip(symbols, scores) if score >= args.minimum_score]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in selected), encoding="utf-8")
    print(json.dumps({"status": "complete", "research_only": True, "execution_enabled": False,
                      "as_of_date": args.as_of_date, "fresh_sequences": len(symbols), "selected": len(selected),
                      "excluded_missing": excluded_missing, "excluded_stale": excluded_stale,
                      "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
