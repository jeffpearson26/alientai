from __future__ import annotations

"""Fail-closed readiness audit for the exact Nasdaq/AI five-day roadmap."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from alientai_v2.research.nasdaq_ai_roadmap_5d import (
    REQUIRED_CONTEXT_SYMBOLS,
    REQUIRED_POINT_IN_TIME_COLUMNS,
    load_json,
    manifest_symbols,
    read_jsonl,
    read_symbols,
    sha256,
    validate_contract,
    validate_membership_rows,
    validate_point_in_time_rows,
)


def family(status: str, evidence: Any, blockers: list[str]) -> dict[str, Any]:
    return {
        "status": status,
        "evidence": evidence,
        "blockers": blockers,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("nasdaq_ai_roadmap_5d_contract.json"),
    )
    parser.add_argument(
        "--nasdaq-current",
        type=Path,
        default=Path("nasdaq100_2026-06_symbols.txt"),
    )
    parser.add_argument(
        "--ai-overlay",
        type=Path,
        default=Path(
            "research_universes/nasdaq_ai_roadmap_overlay_20260805.txt"
        ),
    )
    parser.add_argument(
        "--membership-history",
        type=Path,
        default=Path(
            r"D:\AlientAI\Data\PointInTime"
            r"\nasdaq100_quarterly_membership.jsonl"
        ),
    )
    parser.add_argument(
        "--primary-daily-root",
        type=Path,
        default=Path(
            r"D:\AlientAI\Data\AlphaVantage_2026"
            r"\nasdaq101_qqq_spy_daily_adjusted_full_20260805"
        ),
    )
    parser.add_argument(
        "--supplement-daily-root",
        type=Path,
        default=Path(
            r"D:\AlientAI\Data\AlphaVantage_2026"
            r"\nasdaq_ai_roadmap_supplement_adjusted_full"
        ),
    )
    parser.add_argument(
        "--fundamentals",
        type=Path,
        default=Path(
            r"D:\AlientAI\Data\PointInTime"
            r"\nasdaq_ai_roadmap_fundamentals.jsonl"
        ),
    )
    parser.add_argument(
        "--earnings-calendar",
        type=Path,
        default=Path(
            r"D:\AlientAI\Data\PointInTime"
            r"\nasdaq_ai_roadmap_earnings_calendar.jsonl"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            r"data_v2\rcef_research"
            r"\nasdaq_ai_roadmap_5d_readiness.json"
        ),
    )
    args = parser.parse_args()

    contract = load_json(args.contract)
    validate_contract(contract)
    nasdaq = read_symbols(args.nasdaq_current)
    overlay = read_symbols(args.ai_overlay)
    current_union = sorted(set(nasdaq) | set(overlay))
    families: dict[str, Any] = {}

    universe_blockers = []
    if len(nasdaq) != 101:
        universe_blockers.append(
            f"current Nasdaq reference has {len(nasdaq)}, expected 101"
        )
    if len(overlay) != 22:
        universe_blockers.append(
            f"AI overlay has {len(overlay)}, expected exact 22"
        )
    if len(current_union) != 103:
        universe_blockers.append(
            f"current union has {len(current_union)}, expected 103"
        )
    families["current_universe_reference"] = family(
        "READY" if not universe_blockers else "BLOCKED",
        {
            "nasdaq_count": len(nasdaq),
            "overlay_count": len(overlay),
            "current_union_count": len(current_union),
            "overlay_outside_current_nasdaq": sorted(set(overlay) - set(nasdaq)),
            "nasdaq_sha256": sha256(args.nasdaq_current),
            "overlay_sha256": sha256(args.ai_overlay),
        },
        universe_blockers,
    )

    membership_blockers = []
    membership_evidence: dict[str, Any] = {"path": str(args.membership_history)}
    if not args.membership_history.exists():
        membership_blockers.append(
            "dated quarterly Nasdaq-100 membership history is absent"
        )
    else:
        rows = read_jsonl(args.membership_history)
        membership_blockers.extend(validate_membership_rows(rows))
        membership_evidence.update(
            {
                "rows": len(rows),
                "sha256": sha256(args.membership_history),
                "first_effective_from": (
                    rows[0].get("effective_from") if rows else None
                ),
                "last_effective_from": (
                    rows[-1].get("effective_from") if rows else None
                ),
            }
        )
    families["historical_membership"] = family(
        "READY" if not membership_blockers else "BLOCKED",
        membership_evidence,
        membership_blockers,
    )

    primary, primary_errors = manifest_symbols(args.primary_daily_root)
    supplement, supplement_errors = manifest_symbols(
        args.supplement_daily_root
    )
    available = primary | supplement
    required_price_symbols = set(current_union) | set(REQUIRED_CONTEXT_SYMBOLS)
    price_blockers = [
        *primary_errors,
        *supplement_errors,
    ]
    missing_prices = sorted(required_price_symbols - available)
    if missing_prices:
        price_blockers.append(
            f"full adjusted daily history missing: {missing_prices}"
        )
    families["adjusted_daily_prices_and_regimes"] = family(
        "READY" if not price_blockers else "BLOCKED",
        {
            "primary_root": str(args.primary_daily_root),
            "supplement_root": str(args.supplement_daily_root),
            "required_symbol_count": len(required_price_symbols),
            "available_manifest_symbol_count": len(available),
            "context_symbols": list(REQUIRED_CONTEXT_SYMBOLS),
            "missing_symbols": missing_prices,
        },
        price_blockers,
    )

    for name, path in (
        ("point_in_time_fundamentals", args.fundamentals),
        ("earnings_calendar", args.earnings_calendar),
    ):
        blockers = []
        evidence = {"path": str(path)}
        key = (
            "fundamentals"
            if name == "point_in_time_fundamentals"
            else "earnings_calendar"
        )
        if not path.exists():
            blockers.append(f"required point-in-time table is absent: {path}")
        else:
            rows = read_jsonl(path)
            blockers.extend(
                validate_point_in_time_rows(
                    rows, REQUIRED_POINT_IN_TIME_COLUMNS[key]
                )
            )
            symbols = {str(row.get("symbol", "")).upper() for row in rows}
            missing = sorted(set(current_union) - symbols)
            if missing:
                blockers.append(
                    f"current-union symbol coverage missing: {missing}"
                )
            evidence.update(
                {
                    "rows": len(rows),
                    "symbol_count": len(symbols),
                    "sha256": sha256(path),
                }
            )
        families[name] = family(
            "READY" if not blockers else "BLOCKED",
            evidence,
            blockers,
        )

    optional = {
        "short_interest_change": {
            "status": "AVAILABLE_FOR_LATER_AUDIT"
            if Path(r"D:\AlientAI\Data\FINRA_Short_Interest").exists()
            else "ABSENT_OPTIONAL",
            "path": r"D:\AlientAI\Data\FINRA_Short_Interest",
        },
        "prior_session_options_implied_move": {
            "status": "ABSENT_OPTIONAL",
            "reason": (
                "existing option archives do not provide complete dated "
                "current-universe coverage under this model contract"
            ),
        },
        "point_in_time_finbert_news": {
            "status": "ABSENT_OPTIONAL",
            "reason": (
                "existing news archives do not provide complete exact-universe "
                "point-in-time coverage under this model contract"
            ),
        },
    }
    mandatory_ready = all(
        entry["status"] == "READY" for entry in families.values()
    )
    report = {
        "status": "READY_TO_BUILD_PANEL" if mandatory_ready else "BLOCKED",
        "model_id": contract["model_id"],
        "research_only": True,
        "execution_enabled": False,
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "contract": str(args.contract),
        "contract_sha256": sha256(args.contract),
        "mandatory_families": families,
        "optional_families": optional,
        "next_action": (
            "build the exact point-in-time panel"
            if mandatory_ready
            else "acquire only the listed mandatory missing data; do not train"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    if not mandatory_ready:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
