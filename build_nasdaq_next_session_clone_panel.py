from __future__ import annotations

"""Build an isolated next-session panel for a frozen Nasdaq daily model."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from build_nasdaq100_one_day_labels import (
    TARGET,
    attach_labels,
    load_daily,
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def symbols(path: Path) -> list[str]:
    return [
        line.strip().upper()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--daily-dir", type=Path, required=True)
    parser.add_argument("--universe", type=Path, required=True)
    parser.add_argument("--clone-model-id", required=True)
    parser.add_argument("--source-model-id", required=True)
    parser.add_argument("--expected-universe-count", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    args = parser.parse_args()
    if args.output.exists() or args.manifest.exists():
        raise FileExistsError("output and manifest paths must both be new")
    if args.round_trip_cost_pct != 0.25:
        raise ValueError("clone contract requires exactly 0.25% cost")

    rows = [
        json.loads(line)
        for line in args.input.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    expected = symbols(args.universe)
    if (
        args.expected_universe_count < 2
        or len(expected) != args.expected_universe_count
        or len(set(expected)) != args.expected_universe_count
    ):
        raise ValueError("universe file does not match its frozen count")
    observed = sorted(
        {str(row.get("symbol") or "").strip().upper() for row in rows}
    )
    if set(observed) != set(expected):
        raise ValueError("source panel universe does not match frozen universe")
    daily = load_daily(args.daily_dir)
    labeled, counts = attach_labels(rows, daily, horizon_sessions=1)
    if counts["labeled_rows"] != counts["input_rows"]:
        raise ValueError(f"incomplete one-session labels: {counts}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    dates: set[str] = set()
    with args.output.open("wb") as handle:
        for row in labeled:
            gross = float(row[TARGET])
            output: dict[str, Any] = {
                **row,
                "label_forward_return_1d_gross_pct": gross,
                "label_forward_return_1d_pct": (
                    gross - args.round_trip_cost_pct
                ),
                "round_trip_cost_pct": args.round_trip_cost_pct,
                "target_horizon_sessions": 1,
                "research_only": True,
                "execution_enabled": False,
            }
            payload = (
                json.dumps(output, sort_keys=True, separators=(",", ":"))
                + "\n"
            ).encode("utf-8")
            handle.write(payload)
            digest.update(payload)
            dates.add(str(row["market_date"]))
    manifest = {
        "status": "complete",
        "schema_version": 1,
        "research_only": True,
        "execution_enabled": False,
        "source_model_id": args.source_model_id,
        "clone_model_id": args.clone_model_id,
        "target_horizon_sessions": 1,
        "decision": "after completed regular-session close",
        "entry": "next regular-session open",
        "exit": "that next regular session's official close",
        "round_trip_cost_pct": args.round_trip_cost_pct,
        "source_panel": str(args.input),
        "source_panel_sha256": file_sha256(args.input),
        "universe_path": str(args.universe),
        "universe_sha256": file_sha256(args.universe),
        "universe_count": len(expected),
        "daily_dir": str(args.daily_dir),
        "panel": str(args.output),
        "panel_sha256": digest.hexdigest(),
        "rows": len(labeled),
        "market_dates": len(dates),
        "first_market_date": min(dates),
        "last_market_date": max(dates),
        "label_counts": counts,
        "warnings": [
            "fixed June 2026 membership creates survivorship bias",
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
                "rows": len(labeled),
                "dates": len(dates),
                "panel": str(args.output),
                "manifest": str(args.manifest),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
