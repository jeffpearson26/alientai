from __future__ import annotations

"""Fail loudly before the Schwab late-entry decision window."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_symbols(path: Path) -> set[str]:
    values = {
        line.strip().upper()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if not values:
        raise ValueError("frozen universe is empty")
    return values


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise ValueError(f"required readiness file is missing: {path}")
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        raise ValueError(f"required readiness file is empty: {path}")
    return rows


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact_rows(
    rows: list[dict[str, Any]], expected: set[str], expected_date: str, name: str
) -> None:
    symbols = [str(row.get("symbol") or "").strip().upper() for row in rows]
    if len(rows) != len(expected) or set(symbols) != expected or len(set(symbols)) != len(symbols):
        raise ValueError(f"{name} does not contain one row for every frozen symbol")
    dates = {str(row.get("market_date") or "") for row in rows}
    if dates != {expected_date}:
        raise ValueError(f"{name} is stale: expected {expected_date}, found {sorted(dates)}")


def build_readiness(
    technical_path: Path,
    call_path: Path,
    symbols_path: Path,
    manifest_path: Path,
    decision_date: str,
    prior_session_date: str,
    minimum_call_history: int = 10,
) -> dict[str, Any]:
    expected = read_symbols(symbols_path)
    technical, calls = read_jsonl(technical_path), read_jsonl(call_path)
    exact_rows(technical, expected, prior_session_date, "technical panel")
    exact_rows(calls, expected, prior_session_date, "call panel")
    if {str(row.get("source") or "") for row in technical} != {
        "alpha_vantage_time_series_daily"
    }:
        raise ValueError("technical panel source contract mismatch")
    histories = [int(row.get("call_activity_history_count") or 0) for row in calls]
    if min(histories) < minimum_call_history:
        raise ValueError(
            f"call panel minimum history is {min(histories)}; "
            f"{minimum_call_history} required"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("status") != "frozen"
        or manifest.get("research_only") is not True
        or manifest.get("execution_enabled") is not False
        or int(manifest.get("universe_size") or 0) != len(expected)
    ):
        raise ValueError("late-entry frozen manifest contract mismatch")
    return {
        "schema_version": 1,
        "status": "READY",
        "research_only": True,
        "execution_enabled": False,
        "decision_date": decision_date,
        "prior_session_date": prior_session_date,
        "universe_size": len(expected),
        "minimum_call_history": min(histories),
        "technical_sha256": sha256(technical_path),
        "call_sha256": sha256(call_path),
        "manifest_sha256": sha256(manifest_path),
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--technical", type=Path, required=True)
    parser.add_argument("--calls", type=Path, required=True)
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--decision-date", required=True)
    parser.add_argument("--prior-session-date", required=True)
    parser.add_argument("--minimum-call-history", type=int, default=10)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_readiness(
        args.technical, args.calls, args.symbols_file, args.manifest,
        args.decision_date, args.prior_session_date, args.minimum_call_history,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
