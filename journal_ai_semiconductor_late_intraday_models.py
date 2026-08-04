from __future__ import annotations

"""Journal frozen late-entry AI/semiconductor models before the 09:35 ET entry."""

import argparse
import json
import math
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

import lightgbm as lgb
import numpy as np

from alientai_v2.features.premarket_features import build_premarket_features
from build_ai_semiconductor_20min_panel import schwab_context
from journal_ai_semiconductor_intraday_models import (
    append_unique,
    by_symbol,
    ensure_frozen_manifest,
    read_jsonl,
    sha256,
)


EASTERN = ZoneInfo("America/New_York")
MODEL_CONFIGS = (
    ("60m_premarket", 0.20, "ai_semiconductor_late_60m_premarket_schwab_20260803"),
    ("60m_calls", 0.10, "ai_semiconductor_late_60m_calls_schwab_20260803"),
)


def validate_capture_window(
    decision_date: str,
    manifest: Mapping[str, Any],
    now_utc: datetime | None = None,
) -> datetime:
    now = now_utc or datetime.now(timezone.utc)
    now_et = now.astimezone(EASTERN)
    decision = date.fromisoformat(decision_date)
    if now_et.date() != decision or not time(9, 30) <= now_et.time() < time(9, 35):
        raise ValueError("late-entry scoring must occur from 09:30 through 09:34:59 ET")
    if (
        manifest.get("status") != "complete"
        or manifest.get("source") != "Schwab pricehistory"
        or manifest.get("mode") != "current"
        or int(manifest.get("bar_interval_minutes") or 0) != 5
        or manifest.get("timestamp_convention") != "interval_start"
        or manifest.get("decision_date") != decision_date
    ):
        raise ValueError("Schwab snapshot manifest contract mismatch")
    observed = datetime.fromisoformat(str(manifest.get("captured_at_utc") or ""))
    if observed.tzinfo is None or observed.utcoffset() is None:
        raise ValueError("Schwab snapshot capture timestamp is invalid")
    observed_et = observed.astimezone(EASTERN)
    if not time(9, 30) <= observed_et.time() < time(9, 35):
        raise ValueError("Schwab snapshot was not captured inside the entry window")
    return observed


def merge_inputs(
    technical_rows: Sequence[Mapping[str, Any]],
    call_rows: Sequence[Mapping[str, Any]],
    schwab_archive: Path,
    decision_date: str,
    prior_session_date: str,
    expected_symbols: Sequence[str],
) -> list[dict[str, Any]]:
    technical, calls = by_symbol(technical_rows), by_symbol(call_rows)
    expected = {symbol.strip().upper() for symbol in expected_symbols}
    if set(technical) != expected or set(calls) != expected:
        raise ValueError("technical and call inputs must match the frozen universe")
    output = []
    for symbol in sorted(expected):
        tech, call = technical[symbol], calls[symbol]
        prior_dates = {
            str(tech.get("market_date") or ""),
            str(call.get("market_date") or ""),
        }
        if len(prior_dates) != 1:
            raise ValueError(f"technical/call date mismatch for {symbol}")
        prior_date = next(iter(prior_dates))
        if prior_date != prior_session_date:
            raise ValueError(
                f"technical/call rows are stale for {symbol}: "
                f"expected {prior_session_date}, found {prior_date}"
            )
        candles = schwab_context(schwab_archive, symbol, decision_date)
        premarket = build_premarket_features(candles, decision_date)
        if (
            premarket.get("premarket_available") is not True
            or premarket.get("premarket_cutoff_et") != "09:25"
            or premarket.get("premarket_last_timestamp_et")
            != f"{decision_date} 09:25:00"
        ):
            raise ValueError(f"complete 09:25 Schwab premarket data unavailable for {symbol}")
        output.append({
            **tech,
            **{
                f"model_{name}": value
                for name, value in premarket.items()
                if name.startswith("premarket_")
            },
            **{
                f"model_{name}": value
                for name, value in call.items()
                if name.startswith("call_")
            },
            "symbol": symbol,
            "market_date": decision_date,
            "prior_feature_market_date": prior_date,
        })
    return output


def model_specs(model_root: Path, universe_size: int) -> list[dict[str, Any]]:
    output = []
    for short_name, fraction, directory_name in MODEL_CONFIGS:
        directory = model_root / directory_name
        model_path = directory / "natural_technical_context_classifier.txt"
        report_path = directory / "natural_technical_context_report.json"
        output.append({
            "model_id": f"ai_semiconductor_late_{short_name}_schwab_frozen_20260803",
            "horizon_minutes": 60,
            "daily_fraction": fraction,
            "daily_candidate_count": max(1, math.ceil(universe_size * fraction)),
            "model_sha256": sha256(model_path),
            "training_report_sha256": sha256(report_path),
        })
    return output


def score_models(
    rows: list[dict[str, Any]],
    model_root: Path,
    decision_date: str,
) -> list[dict[str, Any]]:
    observations = []
    journaled_at = datetime.now(timezone.utc).isoformat()
    for short_name, fraction, directory_name in MODEL_CONFIGS:
        directory = model_root / directory_name
        model_path = directory / "natural_technical_context_classifier.txt"
        report_path = directory / "natural_technical_context_report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        names = report["feature_names"]
        values = np.asarray(
            [[float(row.get(name) or 0.0) for name in names] for row in rows],
            dtype=np.float32,
        )
        model = lgb.Booster(model_file=str(model_path))
        scores = model.predict(values, num_iteration=model.best_iteration)
        count = max(1, math.ceil(len(rows) * fraction))
        ranked = sorted(
            ({**row, "model_score": float(score)} for row, score in zip(rows, scores)),
            key=lambda row: (-row["model_score"], row["symbol"]),
        )[:count]
        model_id = f"ai_semiconductor_late_{short_name}_schwab_frozen_20260803"
        for rank, row in enumerate(ranked, 1):
            observations.append({
                "model_id": model_id,
                "model_sha256": sha256(model_path),
                "market_date": decision_date,
                "prior_feature_market_date": row["prior_feature_market_date"],
                "symbol": row["symbol"],
                "rank": rank,
                "model_score": row["model_score"],
                "score_is_probability": False,
                "horizon_minutes": 60,
                "entry_reference": "09:35 ET bar open",
                "exit_reference": "10:30 ET bar close, observable 10:35 ET",
                "round_trip_cost_pct": 0.25,
                "status": "pending",
                "journaled_at_utc": journaled_at,
                "research_only": True,
                "execution_decision": "AVOID",
            })
    return observations


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--technical", type=Path, required=True)
    parser.add_argument("--call-history", type=Path, required=True)
    parser.add_argument("--schwab-archive", type=Path, required=True)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--decision-date", required=True)
    parser.add_argument("--prior-session-date", required=True)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--symbols-file", type=Path, required=True)
    args = parser.parse_args()

    symbols = [
        line.strip().upper()
        for line in args.symbols_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    snapshot_manifest = json.loads(
        (args.schwab_archive / "manifest.json").read_text(encoding="utf-8")
    )
    validate_capture_window(args.decision_date, snapshot_manifest)
    specs = model_specs(args.model_root, len(symbols))
    ensure_frozen_manifest(args.manifest, {
        "status": "frozen",
        "research_only": True,
        "execution_enabled": False,
        "universe_size": len(symbols),
        "universe_sha256": sha256(args.symbols_file),
        "decision_window": "09:30 through 09:34:59 ET",
        "entry_reference": "09:35 ET bar open",
        "outcome_reference": "10:30 ET bar close, observable 10:35 ET",
        "feature_sources": {
            "technical": "Alpha Vantage prior-session daily",
            "calls": "Alpha Vantage prior-session historical options",
            "premarket": "Schwab current-session five-minute extended-hours",
        },
        "models": specs,
    })
    rows = merge_inputs(
        read_jsonl(args.technical),
        read_jsonl(args.call_history),
        args.schwab_archive,
        args.decision_date,
        args.prior_session_date,
        symbols,
    )
    observations = score_models(rows, args.model_root, args.decision_date)
    additions = append_unique(args.journal, observations)
    print(json.dumps({
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "decision_date": args.decision_date,
        "models": len(specs),
        "observations": len(observations),
        "appended": additions,
    }, indent=2))


if __name__ == "__main__":
    main()
