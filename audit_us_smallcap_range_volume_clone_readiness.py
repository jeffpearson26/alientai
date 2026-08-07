from __future__ import annotations

"""Fail-closed readiness audit for the all-market model-3 universe clone."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from alientai_v2.research.us_smallcap_range_volume_clone import (
    active_stock_symbols,
    parse_utc,
    read_jsonl,
    screen_universe,
    sha256,
    validate_clone_contract,
)


ROOT = Path(__file__).resolve().parent


def audit(args: argparse.Namespace) -> dict[str, Any]:
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    model_path = ROOT / contract["source_artifacts"]["model_path"]
    report_path = ROOT / contract["source_artifacts"]["report_path"]
    validate_clone_contract(
        contract,
        model_path=model_path,
        report_path=report_path,
    )
    symbols = active_stock_symbols(args.listing_status)
    blockers: list[str] = []
    counts: dict[str, Any] | None = None
    if args.technical_snapshot is None or not args.technical_snapshot.is_file():
        blockers.append(
            f"missing source-pure Schwab technical snapshot for all "
            f"{len(symbols):,} active stocks"
        )
    if args.market_cap_snapshot is None or not args.market_cap_snapshot.is_file():
        blockers.append(
            f"missing same-cutoff source-pure Schwab market-cap snapshot for "
            f"all {len(symbols):,} active stocks"
        )
    if not blockers:
        if not args.decision_date or not args.decision_cutoff_utc:
            blockers.append("decision date and cutoff are required with snapshots")
        else:
            cutoff = parse_utc(args.decision_cutoff_utc)
            _, counts = screen_universe(
                symbols,
                read_jsonl(args.technical_snapshot),
                read_jsonl(args.market_cap_snapshot),
                decision_date=args.decision_date,
                cutoff_utc=cutoff,
                provider=contract["source_provider"],
                maximum_market_cap_usd=contract["universe_screen"][
                    "maximum_market_cap_usd_exclusive"
                ],
                maximum_price_usd=contract["universe_screen"][
                    "maximum_close_usd_exclusive"
                ],
                minimum_relative_volume_20=contract["universe_screen"][
                    "minimum_relative_volume_20"
                ],
                minimum_atr14_pct=contract["universe_screen"][
                    "minimum_atr14_pct"
                ],
            )
            if counts["missing_technical"]:
                blockers.append(
                    f"technical snapshot misses {counts['missing_technical']} "
                    "active stocks"
                )
            if counts["missing_market_cap"]:
                blockers.append(
                    f"market-cap snapshot misses {counts['missing_market_cap']} "
                    "active stocks"
                )
            if counts["wrong_decision_date"]:
                blockers.append(
                    f"{counts['wrong_decision_date']} technical rows have the "
                    "wrong decision date"
                )
    return {
        "schema_version": 1,
        "model_id": contract["model_id"],
        "status": "READY_TO_SCORE" if not blockers else "BLOCKED_WITH_EXACT_DATA_EVIDENCE",
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "listing_snapshot": {
            "path": str(args.listing_status.resolve()),
            "sha256": sha256(args.listing_status),
            "active_stocks": len(symbols),
        },
        "required_source_provider": contract["source_provider"],
        "screen_counts": counts,
        "technical_snapshot": (
            str(args.technical_snapshot.resolve())
            if args.technical_snapshot and args.technical_snapshot.exists()
            else None
        ),
        "market_cap_snapshot": (
            str(args.market_cap_snapshot.resolve())
            if args.market_cap_snapshot and args.market_cap_snapshot.exists()
            else None
        ),
        "blockers": blockers,
        "universe_compiled": False,
        "observation_written": False,
        "research_only": True,
        "execution_decision": "AVOID",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--listing-status", type=Path, required=True)
    parser.add_argument("--technical-snapshot", type=Path)
    parser.add_argument("--market-cap-snapshot", type=Path)
    parser.add_argument("--decision-date")
    parser.add_argument("--decision-cutoff-utc")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
