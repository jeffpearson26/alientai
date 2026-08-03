from __future__ import annotations

"""Summarize all frozen AlienTAI prospective journals without scoring or trading."""

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


JOURNALS = {
    "nasdaq100_five_session": "nasdaq100_prospective/journal.jsonl",
    "nasdaq100_five_session_outcomes": "nasdaq100_prospective/outcomes.jsonl",
    "nasdaq80_champion": "nasdaq80_champion_prospective/journal.jsonl",
    "nasdaq80_champion_outcomes": (
        "nasdaq80_champion_prospective/outcomes.jsonl"
    ),
    "ai_semiconductor_five_session": (
        "ai_semiconductor_premarket_prospective_journal.jsonl"
    ),
    "ai_semiconductor_intraday": (
        "ai_semiconductor_intraday_prospective_journal.jsonl"
    ),
    "ai_semiconductor_intraday_outcomes": (
        "ai_semiconductor_intraday_prospective_outcomes.jsonl"
    ),
    "pick_competition": "pick_competition_journal.jsonl",
    "pick_competition_intraday_outcomes": (
        "pick_competition_intraday_outcomes.jsonl"
    ),
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
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


def observation_date(row: dict[str, Any]) -> str | None:
    for key in (
        "decision_date",
        "market_session_date",
        "entry_session_date",
        "market_date",
    ):
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return None


def status_value(row: dict[str, Any]) -> str:
    return str(
        row.get("status")
        or row.get("outcome_status")
        or row.get("gate_status")
        or "unspecified"
    )


def summarize_journal(
    program: str,
    path: Path,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    dates = sorted(
        {
            value
            for row in rows
            if (value := observation_date(row)) is not None
        }
    )
    statuses = Counter(status_value(row) for row in rows)
    models = Counter(
        str(row.get("model_id"))
        for row in rows
        if str(row.get("model_id") or "").strip()
    )
    symbols = sorted(
        {
            str(row.get("symbol")).upper()
            for row in rows
            if str(row.get("symbol") or "").strip()
        }
    )
    result: dict[str, Any] = {
        "program": program,
        "path": str(path),
        "exists": path.exists(),
        "observations": len(rows),
        "unique_dates": len(dates),
        "earliest_date": dates[0] if dates else None,
        "latest_date": dates[-1] if dates else None,
        "status_counts": dict(sorted(statuses.items())),
        "model_counts": dict(sorted(models.items())),
        "unique_symbols": len(symbols),
    }
    if program == "pick_competition":
        participants: dict[str, list[dict[str, Any]]] = defaultdict(list)
        competition_symbols: set[str] = set()
        for row in rows:
            participants[str(row.get("participant") or "unknown")].append(row)
            competition_symbols.update(
                str(symbol).strip().upper()
                for symbol in row.get("picks") or []
                if str(symbol).strip()
            )
        result["unique_symbols"] = len(competition_symbols)
        result["participants"] = {
            participant: {
                "submissions": len(items),
                "pick_count": sum(int(item.get("pick_count") or 0) for item in items),
                "latest_picks": list(items[-1].get("picks") or []),
            }
            for participant, items in sorted(participants.items())
        }
    return result


def latest_contextual_gate(root: Path) -> dict[str, Any]:
    paths = sorted(root.glob("contextual_options_prospective_gate_*.json"))
    if not paths:
        return {
            "program": "contextual_options_five_session",
            "exists": False,
            "status": "missing",
        }
    path = paths[-1]
    payload = json.loads(path.read_text(encoding="utf-8"))
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    return {
        "program": "contextual_options_five_session",
        "exists": True,
        "path": str(path),
        "status": payload.get("status") or payload.get("gate_status"),
        "completed_signals": (
            payload.get("completed_outcomes")
            if payload.get("completed_outcomes") is not None
            else metrics.get("signals")
        ),
        "distinct_decision_dates": (
            payload.get("distinct_market_dates")
            if payload.get("distinct_market_dates") is not None
            else metrics.get("cohort_exit_date_count")
        ),
        "mean_net_return_pct": metrics.get("mean_net_return_pct"),
        "median_net_return_pct": metrics.get("median_net_return_pct"),
        "win_rate_after_cost": metrics.get("win_rate_after_cost"),
        "failure_reasons": list(
            (payload.get("rare_signal_gate") or {}).get("failure_reasons") or []
        ),
    }


def latest_intraday_gate(root: Path) -> dict[str, Any]:
    paths = sorted(root.glob("ai_semiconductor_intraday_gate_*.json"))
    if not paths:
        return {
            "program": "ai_semiconductor_intraday_gate",
            "exists": False,
            "status": "missing",
        }
    path = paths[-1]
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "program": "ai_semiconductor_intraday_gate",
        "exists": True,
        "path": str(path),
        "decision_date": payload.get("decision_date"),
        "status": payload.get("status"),
        "provider_status": payload.get("provider_status"),
        "journal_written": payload.get("journal_written"),
        "outcome_written": payload.get("outcome_written"),
        "reasons": list(payload.get("reasons") or []),
    }


def build_summary(root: Path, generated_at: datetime | None = None) -> dict[str, Any]:
    programs = []
    for name, relative in JOURNALS.items():
        path = root / relative
        programs.append(summarize_journal(name, path, load_jsonl(path)))
    programs.append(latest_contextual_gate(root))
    programs.append(latest_intraday_gate(root))
    return {
        "schema_version": 1,
        "research_only": True,
        "execution_enabled": False,
        "generated_at_utc": (
            generated_at or datetime.now(timezone.utc)
        ).astimezone(timezone.utc).isoformat(),
        "programs": programs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--research-root",
        type=Path,
        default=Path("data_v2/rcef_research"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data_v2/rcef_research/prospective_program_status.json"),
    )
    args = parser.parse_args()
    summary = build_summary(args.research_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
