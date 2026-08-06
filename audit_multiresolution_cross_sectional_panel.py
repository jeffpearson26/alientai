from __future__ import annotations

"""Independently audit a compiled multi-resolution ranker panel."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from alientai_v2.research.multiresolution_cross_sectional import (
    DAILY_FEATURES,
    FIVE_MINUTE_FEATURES,
    NEWS_FEATURES,
    OPTION_FEATURES,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-root", type=Path, required=True)
    args = parser.parse_args()
    manifest_path = args.panel_root / "manifest.json"
    panel_path = args.panel_root / "panel.csv.gz"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = []
    if manifest.get("status") != "complete":
        errors.append("manifest status is not complete")
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
    if not np.allclose(frame["round_trip_cost_pct"], 0.25):
        errors.append("round-trip cost is not exactly 0.25%")
    availability = pd.to_datetime(
        frame["decision_available_at_et"], utc=True, errors="coerce"
    )
    eastern = availability.dt.tz_convert("America/New_York")
    if availability.isna().any():
        errors.append("invalid decision availability timestamp")
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
    for name in [
        *DAILY_FEATURES,
        *FIVE_MINUTE_FEATURES,
        *OPTION_FEATURES,
        *NEWS_FEATURES,
    ]:
        rank = pd.to_numeric(frame[f"rank_{name}"], errors="coerce")
        invalid = rank.notna() & ((rank < 0.0) | (rank > 1.0))
        if invalid.any():
            errors.append(f"rank outside 0-1: {name}")
    counts = frame.groupby("market_date")["symbol"].nunique()
    expected_symbols = int(manifest["candidate_count"])
    minimum_fraction = 0.95 if manifest["universe"] == "nasdaq100" else 0.90
    if (counts < int(np.ceil(expected_symbols * minimum_fraction))).any():
        errors.append("post-filter cross-sectional coverage is too low")
    report = {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "panel": str(panel_path),
        "panel_sha256": actual_hash,
        "rows": len(frame),
        "dates": int(frame["market_date"].nunique()),
        "symbols": int(frame["symbol"].nunique()),
        "minimum_symbols_per_date": int(counts.min()),
        "median_symbols_per_date": float(counts.median()),
        "maximum_symbols_per_date": int(counts.max()),
        "universe": manifest["universe"],
        "research_only": True,
    }
    output = args.panel_root / "content_audit.json"
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
