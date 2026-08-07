from __future__ import annotations

"""Refresh the living data-dependency inventory for promising AlienTAI models."""

import argparse
import csv
import json
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def newest_match(root: Path, pattern: str) -> Path | None:
    candidate = Path(pattern)
    if candidate.is_absolute():
        anchor = Path(candidate.anchor)
        relative = str(candidate)[len(candidate.anchor):].lstrip("\\/")
        matches = list(anchor.glob(relative))
    else:
        matches = list(root.glob(pattern))
    return max(matches, key=lambda path: path.stat().st_mtime) if matches else None


def read_symbols(path: Path) -> list[str]:
    return [
        line.strip().upper()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

def prior_weekday(day: date) -> date:
    value = day - timedelta(days=1)
    while value.weekday() >= 5:
        value -= timedelta(days=1)
    return value


def expected_session_date(now_utc: datetime, mode: str) -> str:
    eastern = now_utc.astimezone(ZoneInfo("America/New_York"))
    if mode == "current":
        return eastern.date().isoformat()
    if mode != "latest_completed":
        raise ValueError(f"unsupported expected-session mode: {mode}")
    if eastern.weekday() < 5 and eastern.time() >= time(16, 15):
        return eastern.date().isoformat()
    return prior_weekday(eastern.date()).isoformat()


def audit_jsonl(
    path: Path, spec: dict[str, Any], now_utc: datetime
) -> dict[str, Any]:
    rows = read_jsonl(path)
    symbols = {str(row.get("symbol") or "").upper() for row in rows}
    dates = sorted(
        {
            str(row.get(spec["date_field"]) or "")
            for row in rows
            if spec.get("date_field") and row.get(spec["date_field"])
        }
    )
    usable = rows
    if spec.get("boolean_field"):
        usable = [row for row in usable if row.get(spec["boolean_field"]) is True]
    if spec.get("availability_field"):
        usable = [
            row
            for row in usable
            if float(row.get(spec["availability_field"]) or 0)
            >= float(spec.get("minimum_value") or 0)
        ]
    required = int(spec.get("required_rows") or 0)
    latest_date = dates[-1] if dates else None
    expected_date = (
        expected_session_date(now_utc, spec["expected_session"])
        if spec.get("expected_session")
        else None
    )
    ready = (
        bool(rows)
        and (not required or len(usable) >= required)
        and (not expected_date or latest_date == expected_date)
    )
    if not rows or (required and len(usable) < required):
        reason = f"only {len(usable)} usable rows; {required or 1} required"
    elif expected_date and latest_date != expected_date:
        reason = f"stale date {latest_date}; expected {expected_date}"
    else:
        reason = None
    return {
        "state": "READY" if ready else "BLOCKED",
        "latest_path": str(path),
        "rows": len(rows),
        "usable_rows": len(usable),
        "unique_symbols": len(symbols - {""}),
        "latest_market_date": latest_date,
        "expected_market_date": expected_date,
        "reason": reason,
    }


def audit_daily_csv_universe(
    root: Path, spec: dict[str, Any], now_utc: datetime
) -> dict[str, Any]:
    directory = root / spec["path"]
    symbols_path = root / spec["symbols_file"]
    expected = read_symbols(symbols_path) + list(spec.get("include_symbols") or [])
    expected_date = (
        expected_session_date(now_utc, spec["expected_session"])
        if spec.get("expected_session")
        else None
    )
    common: set[str] | None = None
    missing = []
    duplicate_sessions: dict[str, list[str]] = {}
    for symbol in dict.fromkeys(expected):
        path = directory / f"{symbol}_schwab_1d_max.csv"
        if not path.exists():
            missing.append(symbol)
            continue
        with path.open(encoding="utf-8", newline="") as handle:
            date_counts = Counter(
                str(row.get("date") or "")
                for row in csv.DictReader(handle)
                if row.get("date")
            )
        duplicates = sorted(
            stored_date
            for stored_date, count in date_counts.items()
            if count > 1
        )
        if duplicates:
            duplicate_sessions[symbol] = duplicates
        dates = {
            stored_date
            for stored_date, count in date_counts.items()
            if count == 1
        }
        common = dates if common is None else common & dates
    latest_stored = max(common) if common else None
    latest_session = None
    if latest_stored:
        latest_session = (
            date.fromisoformat(latest_stored)
            + timedelta(days=int(spec.get("session_date_offset_days") or 0))
        ).isoformat()
    ready = (
        not missing
        and not duplicate_sessions
        and bool(common)
        and (not expected_date or latest_session == expected_date)
    )
    if missing:
        reason = "missing symbols: " + ", ".join(missing[:10])
    elif duplicate_sessions:
        examples = ", ".join(
            f"{symbol}={dates[-1]}"
            for symbol, dates in list(duplicate_sessions.items())[:5]
        )
        reason = (
            "duplicate source sessions are unusable for "
            f"{len(duplicate_sessions)}/{len(dict.fromkeys(expected))} "
            f"symbols; examples: {examples}"
        )
    elif not common:
        reason = "no common date"
    elif expected_date and latest_session != expected_date:
        reason = (
            f"stale session {latest_session} (stored {latest_stored}); "
            f"expected {expected_date}"
        )
    else:
        reason = None
    return {
        "state": "READY" if ready else "BLOCKED",
        "latest_path": str(directory),
        "expected_symbols": len(dict.fromkeys(expected)),
        "missing_symbols": missing,
        "duplicate_session_symbol_count": len(duplicate_sessions),
        "duplicate_session_examples": {
            symbol: dates
            for symbol, dates in list(duplicate_sessions.items())[:10]
        },
        "latest_stored_date": latest_stored,
        "latest_market_date": latest_session,
        "expected_market_date": expected_date,
        "reason": reason,
    }


def audit_manifest(path: Path, spec: dict[str, Any]) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    status = str(manifest.get("status") or "")
    completed_field = str(spec.get("completed_field") or "completed")
    completed = len(manifest.get(completed_field) or [])
    unavailable = len(manifest.get("unavailable") or [])
    failed = len(manifest.get("failed") or [])
    required = int(spec.get("required_completed") or 0)
    required_accounted = int(spec.get("required_accounted") or 0)
    accounted = completed + unavailable
    ready = (
        status == "complete"
        and failed == 0
        and completed >= required
        and accounted >= required_accounted
    )
    thresholds = []
    if required:
        thresholds.append(f"{required} completed")
    if required_accounted:
        thresholds.append(f"{required_accounted} accounted")
    threshold_text = " and ".join(thresholds) if thresholds else "complete status"
    return {
        "state": "READY" if ready else "BLOCKED",
        "latest_path": str(path),
        "manifest_status": status,
        "completed": completed,
        "unavailable": unavailable,
        "accounted": accounted,
        "failed": failed,
        "latest_market_date": manifest.get(
            str(spec.get("date_field") or "current_date")
        ),
        "reason": None
        if ready
        else (
            f"manifest status={status}, completed={completed}, "
            f"unavailable={unavailable}, failed={failed}; "
            f"{threshold_text} required"
        ),
    }


def audit_requirement(
    root: Path, spec: dict[str, Any], now_utc: datetime
) -> dict[str, Any]:
    kind = spec.get("kind")
    if kind == "logical":
        return {
            "state": "CONTRACT",
            "latest_path": None,
            "reason": "validated when each observation reaches this stage",
        }
    if kind == "daily_csv_universe":
        return audit_daily_csv_universe(root, spec, now_utc)
    pattern = str(spec.get("path") or "")
    if kind in {"glob", "jsonl_glob", "manifest_glob"}:
        path = newest_match(root, pattern)
    else:
        candidate = Path(pattern)
        path = candidate if candidate.is_absolute() else root / candidate
        if not path.exists():
            path = None
    if path is None:
        return {
            "state": "BLOCKED",
            "latest_path": None,
            "reason": f"no file matches {pattern}",
        }
    if kind == "jsonl_glob":
        return audit_jsonl(path, spec, now_utc)
    if kind == "manifest_glob":
        return audit_manifest(path, spec)
    if kind == "json_status":
        payload = json.loads(path.read_text(encoding="utf-8"))
        actual = payload.get(str(spec.get("status_field", "status")))
        expected = spec.get("required_status")
        ready = actual == expected
        return {
            "state": "READY" if ready else "BLOCKED",
            "latest_path": str(path),
            "modified_at_utc": datetime.fromtimestamp(
                path.stat().st_mtime, tz=timezone.utc
            ).isoformat(),
            "reason": (
                None
                if ready
                else f"JSON status={actual!r}; required {expected!r}"
            ),
        }
    return {
        "state": "READY",
        "latest_path": str(path),
        "modified_at_utc": datetime.fromtimestamp(
            path.stat().st_mtime, tz=timezone.utc
        ).isoformat(),
        "reason": None,
    }


def build_inventory(root: Path, registry: dict[str, Any]) -> dict[str, Any]:
    now_utc = datetime.now(timezone.utc)
    requirements = {
        key: {**value, **audit_requirement(root, value, now_utc)}
        for key, value in registry["requirements"].items()
    }
    models = []
    for model in registry["models"]:
        states = [requirements[key]["state"] for key in model["requirements"]]
        blocked = [
            key
            for key in model["requirements"]
            if requirements[key]["state"] == "BLOCKED"
        ]
        lifecycle = model.get("lifecycle", "frozen")
        models.append(
            {
                **model,
                "state": (
                    "DEVELOPMENT_NOT_TESTING"
                    if lifecycle == "development"
                    else ("BLOCKED" if blocked else "DATA_PATH_PRESENT")
                ),
                "blocked_requirements": blocked,
                "requirement_states": {
                    key: requirements[key]["state"] for key in model["requirements"]
                },
            }
        )
    settings_path = root / "data_v2" / "v2_settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    enabled = [str(value) for value in settings.get("enabled_engines") or []]
    buy_allowlist = [
        str(value) for value in settings.get("main_account_enabled_buy_engines") or []
    ]
    paper_model_id = "nasdaq100_complete_101_baseline_v1"
    live_flags = {
        key: bool(settings.get(key, False))
        for key in (
            "options_live_trading_enabled",
            "options_real_trading_enabled",
            "live_options_trading_enabled",
            "similarity_engine_sandbox_real_trading_enabled",
        )
    }
    payloads = sorted((
        root / "data_v2" / "rcef_research" / "nasdaq101_baseline_paper"
    ).glob("nasdaq101_baseline_paper_payload_????-??-??.json"))
    exact_single_model = enabled == [paper_model_id] and buy_allowlist == [paper_model_id]
    input_state = requirements.get("schwab_nasdaq101_daily", {}).get("state")
    paper_state = (
        "DISABLED"
        if not settings.get("paper_trading_enabled") or not exact_single_model
        else ("READY_TO_SCORE" if payloads else "ENABLED_ABSTAINING")
    )
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "models": models,
        "requirements": requirements,
        "paper_control": {
            "state": paper_state,
            "paper_trading_enabled": bool(settings.get("paper_trading_enabled")),
            "sole_enabled_model": paper_model_id if exact_single_model else None,
            "enabled_engines": enabled,
            "main_account_enabled_buy_engines": buy_allowlist,
            "all_live_flags_false": not any(live_flags.values()),
            "latest_payload": str(payloads[-1]) if payloads else None,
            "input_state": input_state,
            "blocker": (
                requirements.get("schwab_nasdaq101_daily", {}).get("reason")
                if not payloads
                else None
            ),
        },
    }


def render_markdown(inventory: dict[str, Any]) -> str:
    lines = [
        "# Promising Model Data Inventory",
        "",
        f"Automatically refreshed: `{inventory['generated_at_utc']}`",
        "",
        "This is a readiness inventory, not a profitability claim. `DATA_PATH_PRESENT` "
        "means no required local dependency is missing; each dated observation must "
        "still pass its exact freshness, timing, universe, and hash checks.",
        "",
        "## Paper control readiness",
        "",
        "| State | Sole enabled model | Paper buys | Live trading | Current payload / blocker |",
        "|---|---|---|---|---|",
        (
            f"| **{inventory['paper_control']['state']}** | "
            f"`{inventory['paper_control']['sole_enabled_model'] or 'configuration mismatch'}` | "
            f"{'enabled' if inventory['paper_control']['paper_trading_enabled'] else 'disabled'} | "
            f"{'disabled' if inventory['paper_control']['all_live_flags_false'] else 'CONFIGURATION ERROR'} | "
            f"{str(inventory['paper_control']['latest_payload'] or inventory['paper_control']['blocker'] or 'none').replace('|', '/')} |"
        ),
        "",
        "Paper-account actions are simulation evidence and are never merged into prospective model evidence.",
        "",
        "## Model readiness",
        "",
        "| Model | State | Blocking data |",
        "|---|---|---|",
    ]
    for model in inventory["models"]:
        blockers = ", ".join(model["blocked_requirements"]) or "None in current local audit"
        lines.append(
            f"| {model['display_name']} | **{model['state']}** | {blockers} |"
        )
    lines.extend(
        [
            "",
            "## Data requirements",
            "",
            "| Requirement | Data type | Source | Latest usable date | State | Timing contract / blocker |",
            "|---|---|---|---|---|---|",
        ]
    )
    for key, item in inventory["requirements"].items():
        detail = item.get("reason") or item.get("timing_contract") or ""
        detail = str(detail).replace("|", "/")
        lines.append(
            f"| `{key}` | {item.get('data_type', '')} | {item.get('source', '')} | "
            f"{item.get('latest_market_date') or '—'} | **{item['state']}** | {detail} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("promising_model_data_requirements.json"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("data_v2/rcef_research/promising_model_data_inventory.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("PROMISING_MODEL_DATA_INVENTORY.md"),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    registry = json.loads((root / args.registry).read_text(encoding="utf-8"))
    inventory = build_inventory(root, registry)
    json_output = root / args.json_output
    markdown_output = root / args.markdown_output
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    markdown_output.write_text(render_markdown(inventory), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "complete",
                "models": len(inventory["models"]),
                "blocked_models": sum(
                    model["state"] == "BLOCKED" for model in inventory["models"]
                ),
                "json_output": str(json_output),
                "markdown_output": str(markdown_output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
