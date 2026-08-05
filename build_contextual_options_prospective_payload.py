"""Build one immutable, research-only contextual unusual-call observation.

The Alpha Vantage option-chain date is an actual U.S. market session.  The
legacy local Schwab daily archive stores that same session under the preceding
calendar date.  This command records both dates explicitly, scores only a
complete common universe, and emits a payload whose future five-session outcome
can be evaluated by the existing frozen evaluator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping
from zoneinfo import ZoneInfo

import lightgbm as lgb

from build_contextual_options_backfill_panel import build as score_complete_panel
from build_local_schwab_daily_technical_panel import build_panel as build_technical_panel
from build_daily_technical_panel import symbols
from compile_natural_options_daily_panel import compile_panel, read_jsonl
from contextual_options_shadow_adapter import build_payload


EASTERN = ZoneInfo("America/New_York")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("decision-at-utc must include a timezone")
    return parsed.astimezone(timezone.utc)


def validate_decision(
    actual_market_date: str,
    schwab_stored_market_date: str,
    decision_at_utc: str,
    now_utc: datetime | None = None,
) -> datetime:
    actual = date.fromisoformat(actual_market_date)
    stored = date.fromisoformat(schwab_stored_market_date)
    if stored + timedelta(days=1) != actual:
        raise ValueError("Schwab stored date must map to the following actual market session")
    decision = parse_aware(decision_at_utc)
    local = decision.astimezone(EASTERN)
    same_day_after_close = local.date() == actual and local.time() >= time(16, 0)
    later_day_before_open = local.date() > actual and local.time() < time(9, 30)
    if not (same_day_after_close or later_day_before_open):
        raise ValueError(
            "prospective payload must be frozen after the stated session close "
            "and before the next market open"
        )
    current = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if decision > current + timedelta(minutes=5):
        raise ValueError("decision-at-utc cannot be in the future")
    return decision


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True) + "\n")


def available_symbols(
    symbol_list: list[str],
    manifest_path: Path,
    actual_market_date: str,
) -> tuple[list[str], list[str]]:
    def normalized(symbol: str) -> str:
        return symbol.upper().replace(".", "-").replace("/", "-")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    completed = list(manifest.get("completed") or [])
    unavailable = list(manifest.get("unavailable") or [])
    failed = list(manifest.get("failed") or [])
    if manifest.get("status") != "complete" or failed:
        raise ValueError("option availability manifest is not complete and clean")
    accounted = [*completed, *unavailable]
    if any(
        str(key).rsplit("|", 1)[-1] != actual_market_date
        for key in accounted
    ):
        raise ValueError("option availability manifest date mismatch")
    requested = {normalized(symbol) for symbol in symbol_list}
    completed_symbols = {
        normalized(str(key).rsplit("|", 1)[0]) for key in completed
    }
    unavailable_symbols = {
        normalized(str(key).rsplit("|", 1)[0]) for key in unavailable
    }
    accounted_symbols = completed_symbols | unavailable_symbols
    if not accounted_symbols.issubset(requested):
        raise ValueError("option availability manifest contains foreign symbols")
    request_count = int(manifest.get("requests") or len(accounted))
    if len(accounted_symbols) != request_count:
        raise ValueError("option availability manifest request count mismatch")
    return (
        [
            symbol
            for symbol in symbol_list
            if normalized(symbol) in completed_symbols
        ],
        [
            symbol
            for symbol in symbol_list
            if normalized(symbol) in unavailable_symbols
        ],
    )


def build(
    *,
    actual_market_date: str,
    schwab_stored_market_date: str,
    decision_at_utc: str,
    symbol_list: list[str],
    daily_dir: Path,
    previous_features: Path,
    chains: Path,
    target_chains: Path | None,
    technical_model: Path,
    minimum_universe_rows: int = 400,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    decision = validate_decision(
        actual_market_date,
        schwab_stored_market_date,
        decision_at_utc,
    )
    technical_raw, technical_missing = build_technical_panel(
        schwab_stored_market_date, symbol_list, daily_dir
    )
    if len(technical_raw) < minimum_universe_rows:
        raise ValueError(
            f"incomplete technical universe: {len(technical_raw)} rows; "
            f"need {minimum_universe_rows}"
        )
    eligible_symbols = [str(row["symbol"]).upper() for row in technical_raw]
    price_rows = [
        {
            "symbol": row["symbol"],
            "market_date": actual_market_date,
            "close": row["close"],
        }
        for row in technical_raw
    ]
    option_rows, option_missing = compile_panel(
        eligible_symbols,
        read_jsonl(previous_features),
        chains,
        daily_dir,
        actual_market_date,
        price_rows,
        target_chains,
    )
    if option_missing:
        raise ValueError(
            f"incomplete option universe: missing {len(option_missing)} of "
            f"{len(eligible_symbols)} eligible symbols"
        )

    technical_rows = [
        {
            **row,
            "market_date": schwab_stored_market_date,
            "actual_market_session_date": actual_market_date,
            "schwab_stored_market_date": schwab_stored_market_date,
        }
        for row in technical_raw
    ]
    normalized_options = [
        {
            **row,
            "option_market_date": actual_market_date,
            "market_date": schwab_stored_market_date,
            "actual_market_session_date": actual_market_date,
            "schwab_stored_market_date": schwab_stored_market_date,
        }
        for row in option_rows
    ]
    model = lgb.Booster(model_file=str(technical_model))
    scored_rows, score_summary = score_complete_panel(
        technical_rows, normalized_options, model
    )
    for row in scored_rows:
        row.pop("backfill_only", None)
        row.update(
            {
                "prospective_observation": True,
                "decision_at_utc": decision.isoformat(),
                "execution_decision": "AVOID",
            }
        )

    payload = build_payload(
        scored_rows, minimum_universe_rows=minimum_universe_rows
    )
    payload.update(
        {
            "status": "prospective_research_payload_ready",
            "eligible_for_prospective_gate": True,
            "decision_at_utc": decision.isoformat(),
            "actual_market_session_date": actual_market_date,
            "schwab_stored_market_date": schwab_stored_market_date,
            "source_contract": {
                "technical": "schwab_local_daily_csv",
                "options": "alpha_vantage_historical_options",
                "outcomes": "schwab_local_daily_csv",
            },
            "artifact_sha256": {
                "previous_features": file_sha256(previous_features),
                "technical_model": file_sha256(technical_model),
            },
            "warning": (
                "Research-only frozen prospective observation. It cannot place "
                "an order or change settings."
            ),
        }
    )
    summary = {
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "eligible_for_prospective_gate": True,
        "actual_market_session_date": actual_market_date,
        "schwab_stored_market_date": schwab_stored_market_date,
        "decision_at_utc": decision.isoformat(),
        "requested_symbols": len(symbol_list),
        "technical_rows": len(technical_rows),
        "technical_missing": len(technical_missing),
        "option_rows": len(normalized_options),
        "option_missing": 0,
        "history_qualified_rows": sum(
            int(float(row.get("call_activity_history_count") or 0)) >= 10
            for row in scored_rows
        ),
        "candidates": len(payload["candidates"]),
        **score_summary,
    }
    return scored_rows, payload, summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a frozen prospective contextual unusual-call payload."
    )
    parser.add_argument("--actual-market-date", required=True)
    parser.add_argument("--schwab-stored-market-date", required=True)
    parser.add_argument("--decision-at-utc", required=True)
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--daily-dir", type=Path, required=True)
    parser.add_argument("--previous-features", type=Path, required=True)
    parser.add_argument("--chains", type=Path, required=True)
    parser.add_argument(
        "--target-chains",
        type=Path,
        help="Optional separate source root containing target-date chains.",
    )
    parser.add_argument(
        "--availability-manifest",
        type=Path,
        help=(
            "Completed manifest used to exclude only explicitly unavailable "
            "symbols from the complete common universe."
        ),
    )
    parser.add_argument("--technical-model", type=Path, required=True)
    parser.add_argument("--scored-output", type=Path, required=True)
    parser.add_argument("--payload-output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    parser.add_argument("--minimum-universe-rows", type=int, default=400)
    args = parser.parse_args()

    symbol_list = symbols(args.symbols_file)
    explicitly_unavailable: list[str] = []
    if args.availability_manifest:
        symbol_list, explicitly_unavailable = available_symbols(
            symbol_list,
            args.availability_manifest,
            args.actual_market_date,
        )
    scored, payload, summary = build(
        actual_market_date=args.actual_market_date,
        schwab_stored_market_date=args.schwab_stored_market_date,
        decision_at_utc=args.decision_at_utc,
        symbol_list=symbol_list,
        daily_dir=args.daily_dir,
        previous_features=args.previous_features,
        chains=args.chains,
        target_chains=args.target_chains,
        technical_model=args.technical_model,
        minimum_universe_rows=args.minimum_universe_rows,
    )
    summary["explicitly_unavailable_symbols"] = explicitly_unavailable
    summary["explicitly_unavailable_count"] = len(explicitly_unavailable)
    write_jsonl(args.scored_output, scored)
    args.payload_output.parent.mkdir(parents=True, exist_ok=True)
    args.payload_output.write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    args.summary_output.write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
