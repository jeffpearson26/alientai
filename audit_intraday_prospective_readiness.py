from __future__ import annotations

"""Fail-closed readiness audit for the frozen intraday prospective program."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MODEL_DIRECTORIES = (
    "ai_semiconductor_20min_technical",
    "ai_semiconductor_20min_premarket",
    "ai_semiconductor_20min_calls",
    "ai_semiconductor_60min_technical",
    "ai_semiconductor_60min_premarket",
    "ai_semiconductor_60min_calls",
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number} is not a JSON object")
        rows.append(row)
    return rows


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def symbols(rows: list[dict[str, Any]]) -> set[str]:
    return {
        str(row.get("symbol") or "").strip().upper()
        for row in rows
        if str(row.get("symbol") or "").strip()
    }


def require_exact_panel(
    *,
    name: str,
    rows: list[dict[str, Any]],
    expected_symbols: set[str],
    expected_date: str,
) -> None:
    if len(rows) != len(expected_symbols) or symbols(rows) != expected_symbols:
        raise ValueError(f"{name} does not contain the exact frozen universe")
    dates = {str(row.get("market_date") or "") for row in rows}
    if dates != {expected_date}:
        raise ValueError(f"{name} date mismatch: {sorted(dates)}")


def build_audit(
    *,
    technical_path: Path,
    call_history_path: Path,
    events_path: Path,
    model_root: Path,
    symbols_path: Path,
    decision_date: str,
    prior_session_date: str,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    expected_symbols = {
        line.strip().upper()
        for line in symbols_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if not expected_symbols:
        raise ValueError("frozen universe is empty")

    technical = load_jsonl(technical_path)
    calls = load_jsonl(call_history_path)
    events = load_jsonl(events_path)
    require_exact_panel(
        name="technical panel",
        rows=technical,
        expected_symbols=expected_symbols,
        expected_date=prior_session_date,
    )
    require_exact_panel(
        name="call-history panel",
        rows=calls,
        expected_symbols=expected_symbols,
        expected_date=prior_session_date,
    )
    require_exact_panel(
        name="event panel",
        rows=events,
        expected_symbols=expected_symbols,
        expected_date=decision_date,
    )
    as_of_values = {str(row.get("as_of_utc") or "") for row in events}
    if len(as_of_values) != 1:
        raise ValueError("event panel must use one exact cutoff timestamp")
    as_of = datetime.fromisoformat(next(iter(as_of_values)))
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("event cutoff must be timezone-aware")
    if as_of.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z") != (
        f"{decision_date}T13:25:00+0000"
    ):
        raise ValueError("event cutoff must be exactly 09:25 ET / 13:25 UTC")

    model_artifacts = []
    for directory_name in MODEL_DIRECTORIES:
        directory = model_root / directory_name
        model_path = directory / "natural_technical_context_classifier.txt"
        report_path = directory / "natural_technical_context_report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("research_only") is not True:
            raise ValueError(f"{directory_name} is not marked research-only")
        if report.get("execution_enabled") is not False:
            raise ValueError(f"{directory_name} does not fail closed on execution")
        model_artifacts.append(
            {
                "model_id": directory_name,
                "model_sha256": sha256(model_path),
                "report_sha256": sha256(report_path),
                "target": report.get("target"),
            }
        )

    return {
        "schema_version": 1,
        "status": "ready_for_exact_0925_collection",
        "research_only": True,
        "execution_enabled": False,
        "decision_date": decision_date,
        "prior_session_date": prior_session_date,
        "exact_cutoff_utc": as_of.astimezone(timezone.utc).isoformat(),
        "universe_size": len(expected_symbols),
        "technical_rows": len(technical),
        "call_history_rows": len(calls),
        "event_rows": len(events),
        "technical_sha256": sha256(technical_path),
        "call_history_sha256": sha256(call_history_path),
        "events_sha256": sha256(events_path),
        "models": model_artifacts,
        "generated_at_utc": (
            generated_at or datetime.now(timezone.utc)
        ).astimezone(timezone.utc).isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--technical", type=Path, required=True)
    parser.add_argument("--call-history", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--decision-date", required=True)
    parser.add_argument("--prior-session-date", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit = build_audit(
        technical_path=args.technical,
        call_history_path=args.call_history,
        events_path=args.events,
        model_root=args.model_root,
        symbols_path=args.symbols_file,
        decision_date=args.decision_date,
        prior_session_date=args.prior_session_date,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
