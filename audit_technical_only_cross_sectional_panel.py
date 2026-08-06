from __future__ import annotations

"""Independently audit a pure daily-technical cross-sectional panel."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from alientai_v2.research.multiresolution_cross_sectional import DAILY_FEATURES
from build_multiresolution_cross_sectional_panel import sha256


EXCLUDED_TOKENS = (
    "option",
    "call_",
    "implied_volatility",
    "news",
    "headline",
    "sentiment",
    "fundamental",
    "earnings",
    "five_minute",
    "one_minute",
    "intraday",
    "premarket",
    "afterhour",
)


def audit(panel_root: Path) -> dict:
    manifest_path = panel_root / "manifest.json"
    panel_path = panel_root / "panel.csv.gz"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if manifest.get("status") != "complete":
        errors.append("manifest status is not complete")
    if manifest.get("model_family") != "technical_only_cross_sectional_ranker":
        errors.append("unexpected model family")
    source = manifest.get("source_contract", {})
    for name in ("options", "intraday", "afterhours", "news", "fundamentals"):
        if source.get(name) is not None:
            errors.append(f"excluded source is configured: {name}")
    actual_hash = sha256(panel_path)
    expected_hash = manifest["artifacts"]["panel"]["sha256"]
    if actual_hash != expected_hash:
        errors.append("panel SHA-256 mismatch")
    frame = pd.read_csv(panel_path)
    if len(frame) != int(manifest["rows"]):
        errors.append("row count does not match manifest")
    if frame.duplicated(["market_date", "symbol"]).any():
        errors.append("duplicate market_date/symbol keys")
    if set(frame["symbol"]) & {"QQQ", "SPY"}:
        errors.append("context ETF entered candidate rows")
    excluded_columns = [
        column
        for column in frame.columns
        if any(token in column.lower() for token in EXCLUDED_TOKENS)
    ]
    if excluded_columns:
        errors.append(f"excluded feature columns present: {excluded_columns}")
    if not np.allclose(frame["round_trip_cost_pct"], 0.25):
        errors.append("round-trip cost is not exactly 0.25%")
    availability = pd.to_datetime(
        frame["decision_available_at_et"], utc=True, errors="coerce"
    )
    eastern = availability.dt.tz_convert("America/New_York")
    if availability.isna().any():
        errors.append("invalid decision timestamp")
    if (eastern.dt.strftime("%Y-%m-%d") != frame["market_date"]).any():
        errors.append("decision timestamp date mismatch")
    if ((eastern.dt.hour != 20) | (eastern.dt.minute != 0)).any():
        errors.append("decision timestamp is not exactly 20:00 ET")
    for horizon in (5, 20):
        entry = frame[f"label_{horizon}d_entry_date"].astype(str)
        exit_date = frame[f"label_{horizon}d_exit_date"].astype(str)
        decision = frame["market_date"].astype(str)
        if ((entry <= decision) | (exit_date < entry)).any():
            errors.append(f"invalid {horizon}-session label chronology")
        rank = pd.to_numeric(
            frame[f"label_{horizon}d_cross_sectional_rank"], errors="coerce"
        )
        if rank.isna().any() or ((rank < 0.0) | (rank > 1.0)).any():
            errors.append(f"invalid {horizon}-session target ranks")
    for name in DAILY_FEATURES:
        column = f"rank_{name}"
        if column not in frame:
            errors.append(f"missing ranked feature: {name}")
            continue
        rank = pd.to_numeric(frame[column], errors="coerce")
        invalid = rank.notna() & ((rank < 0.0) | (rank > 1.0))
        if invalid.any():
            errors.append(f"rank outside 0-1: {name}")
    counts = frame.groupby("market_date")["symbol"].nunique()
    expected_symbols = int(manifest["candidate_count"])
    if not (counts == expected_symbols).all():
        errors.append("a date does not contain the exact full candidate universe")
    report = {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "panel": str(panel_path),
        "panel_sha256": actual_hash,
        "rows": len(frame),
        "dates": int(frame["market_date"].nunique()),
        "symbols": int(frame["symbol"].nunique()),
        "minimum_symbols_per_date": int(counts.min()),
        "maximum_symbols_per_date": int(counts.max()),
        "universe": manifest["universe"],
        "excluded_feature_columns": excluded_columns,
        "research_only": True,
    }
    output = panel_root / "content_audit.json"
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-root", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.panel_root)
    print(json.dumps(report, indent=2))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
