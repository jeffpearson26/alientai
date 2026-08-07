from __future__ import annotations

"""Build an isolated one-session panel for the contextual unusual-call clone."""

import argparse
import csv
import hashlib
import json
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

from alientai_v2.research.unusual_call_activity import unusual_call_features
from attach_next_session_close_labels import (
    index_schwab_daily,
    price_anchored_next_session_label_from_index,
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def option_feature_map(
    path: Path,
) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, int]]:
    raw_rows = read_jsonl(path)
    computed = unusual_call_features(raw_rows)
    raw = {
        (
            str(row.get("symbol") or "").strip().upper(),
            str(row.get("market_date") or ""),
        ): row
        for row in raw_rows
    }
    if len(raw) != len(raw_rows):
        raise ValueError("duplicate symbol/date keys in option feature panel")
    output: dict[tuple[str, str], dict[str, Any]] = {}
    for feature in computed:
        key = (
            str(feature.get("symbol") or "").strip().upper(),
            str(feature.get("market_date") or ""),
        )
        if key not in raw:
            raise ValueError("computed unusual-call feature lost its source row")
        output[key] = {**raw[key], **feature}
    return output, {
        "option_rows": len(output),
        "option_dates": len({key[1] for key in output}),
        "unusual_call_rows": sum(
            1 for row in output.values() if row.get("call_volume_unusual")
        ),
        "unusual_call_dates": len(
            {
                key[1]
                for key, row in output.items()
                if row.get("call_volume_unusual")
            }
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-rows", type=Path, required=True)
    parser.add_argument("--option-features", type=Path, required=True)
    parser.add_argument("--daily-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    args = parser.parse_args()
    if args.output.exists() or args.manifest.exists():
        raise FileExistsError("output and manifest paths must both be new")
    if args.round_trip_cost_pct != 0.25:
        raise ValueError("clone contract requires exactly 0.25% cost")

    option_by_key, option_counts = option_feature_map(args.option_features)

    @lru_cache(maxsize=8)
    def daily_index(symbol: str):
        path = args.daily_dir / f"{symbol}_schwab_1d_max.csv"
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8", newline="") as handle:
            return index_schwab_daily(csv.DictReader(handle))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    input_rows = 0
    labeled_rows = 0
    contextual_rows = 0
    contextual_unusual_rows = 0
    symbols: set[str] = set()
    dates: set[str] = set()
    unavailable = Counter()

    with (
        args.base_rows.open("r", encoding="utf-8-sig") as source,
        args.output.open("wb") as target,
    ):
        for raw_line in source:
            if not raw_line.strip():
                continue
            input_rows += 1
            row = json.loads(raw_line)
            symbol = str(row.get("symbol") or "").strip().upper()
            market_date = str(row.get("market_date") or "")
            if not symbol or not market_date:
                unavailable["invalid_base_key"] += 1
                continue
            index = daily_index(symbol)
            if index is None:
                unavailable["missing_daily_history"] += 1
                continue
            labeled = price_anchored_next_session_label_from_index(
                row,
                index,
                round_trip_cost_pct=args.round_trip_cost_pct,
            )
            if labeled is None:
                unavailable["unmatched_or_missing_next_session"] += 1
                continue
            option = option_by_key.get((symbol, market_date))
            if option is not None:
                labeled.update(option)
                contextual_rows += 1
                contextual_unusual_rows += int(
                    bool(option.get("call_volume_unusual"))
                )
            payload = (
                json.dumps(labeled, sort_keys=True, separators=(",", ":"))
                + "\n"
            ).encode("utf-8")
            target.write(payload)
            digest.update(payload)
            labeled_rows += 1
            symbols.add(symbol)
            dates.add(market_date)

    if labeled_rows == 0 or contextual_rows == 0:
        raise ValueError("one-session panel is empty or lacks contextual rows")
    manifest = {
        "status": "complete",
        "schema_version": 1,
        "research_only": True,
        "execution_enabled": False,
        "source_model_id": "contextual_options_top_quarter",
        "clone_model_id": "contextual_options_next_session_close_v1",
        "target_horizon_sessions": 1,
        "decision": "after completed regular-session close",
        "entry": "next regular-session open",
        "exit": "that next regular session's official close",
        "round_trip_cost_pct": args.round_trip_cost_pct,
        "base_rows": str(args.base_rows),
        "base_rows_sha256": file_sha256(args.base_rows),
        "option_features": str(args.option_features),
        "option_features_sha256": file_sha256(args.option_features),
        "daily_dir": str(args.daily_dir),
        "panel": str(args.output),
        "panel_sha256": digest.hexdigest(),
        "input_rows": input_rows,
        "labeled_rows": labeled_rows,
        "symbols": len(symbols),
        "market_dates": len(dates),
        "first_market_date": min(dates),
        "last_market_date": max(dates),
        "contextual_rows": contextual_rows,
        "contextual_unusual_rows": contextual_unusual_rows,
        **option_counts,
        "unavailable_rows": sum(unavailable.values()),
        "unavailable_reasons": dict(sorted(unavailable.items())),
        "date_normalization": (
            "decision candle is price-anchored within +/-3 calendar days at "
            "0.001% tolerance; label uses the immediately following stored "
            "session; reported U.S. session date is Schwab datetime date plus "
            "one calendar day"
        ),
        "warnings": [
            "historical archive is retrospective and cannot authorize trading",
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
                "labeled_rows": labeled_rows,
                "contextual_rows": contextual_rows,
                "contextual_unusual_rows": contextual_unusual_rows,
                "unavailable_rows": sum(unavailable.values()),
                "output": str(args.output),
                "manifest": str(args.manifest),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
