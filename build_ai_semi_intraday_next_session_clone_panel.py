from __future__ import annotations

"""Build the source-pure AI/semi intraday-entry to next-close clone panel."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


TARGET = "label_next_complete_session_close_net_pct"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def key(row: dict[str, Any]) -> tuple[str, str]:
    return (
        str(row.get("symbol") or "").strip().upper(),
        str(row.get("market_date") or ""),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intraday-panel", type=Path, required=True)
    parser.add_argument("--alpha-daily-outcome-panel", type=Path, required=True)
    parser.add_argument("--universe", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    args = parser.parse_args()
    if args.output.exists() or args.manifest.exists():
        raise FileExistsError("output and manifest paths must both be new")
    if args.round_trip_cost_pct != 0.25:
        raise ValueError("clone contract requires exactly 0.25% cost")

    universe = [
        line.strip().upper()
        for line in args.universe.read_text(
            encoding="utf-8-sig"
        ).splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if len(universe) != 17 or len(set(universe)) != 17:
        raise ValueError("exact frozen 17-symbol universe is required")
    intraday = read_jsonl(args.intraday_panel)
    daily_rows = read_jsonl(args.alpha_daily_outcome_panel)
    daily = {key(row): row for row in daily_rows}
    if len(daily) != len(daily_rows):
        raise ValueError("duplicate Alpha daily outcome keys")

    output = []
    missing = 0
    for row in intraday:
        if key(row)[0] not in universe:
            raise ValueError("intraday panel contains an out-of-universe symbol")
        outcome = daily.get(key(row))
        if outcome is None:
            missing += 1
            continue
        try:
            entry = float(row["label_entry_0930_open"])
            exit_close = float(outcome["label_1d_exit_close"])
            entry_timestamp = str(row["label_entry_timestamp_et"])
            exit_date = str(outcome["label_1d_exit_market_date"])
        except (KeyError, TypeError, ValueError):
            missing += 1
            continue
        if (
            entry <= 0.0
            or exit_close <= 0.0
            or "09:30:00" not in entry_timestamp
            or not exit_date
            or row.get("label_source")
            != "Alpha Vantage TIME_SERIES_INTRADAY 5min"
            or outcome.get("label_source")
            != "Alpha Vantage TIME_SERIES_DAILY"
        ):
            missing += 1
            continue
        gross = (exit_close / entry - 1.0) * 100.0
        output.append(
            {
                **row,
                "label_next_complete_session_close_gross_pct": gross,
                TARGET: gross - args.round_trip_cost_pct,
                "label_next_complete_session_exit_close": exit_close,
                "label_next_complete_session_exit_market_date": exit_date,
                "target_horizon_sessions": 1,
                "clone_label_contract": (
                    "enter frozen 09:30 ET Alpha Vantage intraday open; "
                    "exit Alpha Vantage official close of the following "
                    "complete regular session"
                ),
                "clone_label_source": "Alpha Vantage source-pure",
                "round_trip_cost_pct": args.round_trip_cost_pct,
                "research_only": True,
                "execution_enabled": False,
            }
        )
    if missing or len(output) != len(intraday):
        raise ValueError(
            f"incomplete source-pure next-session outcomes: "
            f"{len(output)} labeled, {missing} missing"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    dates = set()
    with args.output.open("wb") as handle:
        for row in output:
            payload = (
                json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
            ).encode("utf-8")
            handle.write(payload)
            digest.update(payload)
            dates.add(str(row["market_date"]))
    manifest = {
        "status": "complete",
        "schema_version": 1,
        "research_only": True,
        "execution_enabled": False,
        "source_model_id": "ai_semiconductor_60m_calls_frozen_20260731",
        "clone_model_id": "ai_semiconductor_calls_next_session_close_v1",
        "universe_count": 17,
        "universe_path": str(args.universe),
        "universe_sha256": file_sha256(args.universe),
        "target_horizon_sessions": 1,
        "decision": "frozen premarket/intraday decision window",
        "entry": "frozen 09:30 ET Alpha Vantage interval open",
        "exit": "following complete regular session official Alpha close",
        "round_trip_cost_pct": args.round_trip_cost_pct,
        "provider_contract": (
            "Alpha Vantage intraday entry plus Alpha Vantage daily exit; "
            "no provider splicing"
        ),
        "intraday_panel": str(args.intraday_panel),
        "intraday_panel_sha256": file_sha256(args.intraday_panel),
        "alpha_daily_outcome_panel": str(args.alpha_daily_outcome_panel),
        "alpha_daily_outcome_panel_sha256": file_sha256(
            args.alpha_daily_outcome_panel
        ),
        "panel": str(args.output),
        "panel_sha256": digest.hexdigest(),
        "rows": len(output),
        "market_dates": len(dates),
        "first_market_date": min(dates),
        "last_market_date": max(dates),
        "warnings": [
            "fixed contemporary universe creates survivorship bias",
            "source-model evidence is not inherited by this clone",
        ],
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": "complete",
                "rows": len(output),
                "dates": len(dates),
                "panel": str(args.output),
                "manifest": str(args.manifest),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
