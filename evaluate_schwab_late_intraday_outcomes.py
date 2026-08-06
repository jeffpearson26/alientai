from __future__ import annotations

"""Append outcomes for frozen 09:35-entry Schwab intraday observations."""

import argparse
import json
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

from build_ai_semiconductor_20min_panel import intraday_label, schwab_context
from journal_ai_semiconductor_intraday_models import append_unique, read_jsonl, sha256


EASTERN = ZoneInfo("America/New_York")


def observations_for_archive(
    observations: Sequence[Mapping[str, Any]], archive: Path
) -> list[Mapping[str, Any]]:
    """Select only the cumulative-journal rows matching this outcome snapshot."""
    manifest = json.loads((archive / "manifest.json").read_text(encoding="utf-8"))
    decision_date = str(manifest.get("decision_date") or "")
    if not decision_date:
        raise ValueError("outcome snapshot has no decision date")
    selected = [
        row
        for row in observations
        if str(row.get("market_date") or "") == decision_date
    ]
    if not selected:
        raise ValueError(
            f"no journal observations match outcome date {decision_date}"
        )
    return selected


def completed_outcomes(
    observations: Sequence[Mapping[str, Any]],
    archive: Path,
    now_utc: datetime | None = None,
) -> list[dict[str, Any]]:
    if not observations:
        raise ValueError("no observations exist")
    dates = {str(row.get("market_date") or "") for row in observations}
    if "" in dates or len(dates) != 1:
        raise ValueError("outcome batch must contain one decision date")
    decision_date = next(iter(dates))
    now = now_utc or datetime.now(timezone.utc)
    now_et = now.astimezone(EASTERN)
    if now_et.date() != date.fromisoformat(decision_date) or now_et.time() < time(10, 35):
        raise ValueError("60-minute late-entry outcome is unavailable before 10:35 ET")
    manifest_path = archive / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    captured = datetime.fromisoformat(str(manifest.get("captured_at_utc") or ""))
    if (
        manifest.get("status") != "complete"
        or manifest.get("source") != "Schwab pricehistory"
        or manifest.get("decision_date") != decision_date
        or captured.astimezone(EASTERN).time() < time(10, 35)
    ):
        raise ValueError("outcome snapshot is incomplete or source-mismatched")

    output = []
    for row in observations:
        if int(row.get("horizon_minutes") or 0) != 60:
            raise ValueError("only the frozen 60-minute late-entry horizon is supported")
        label = intraday_label(
            schwab_context(archive, str(row["symbol"]), decision_date),
            decision_date,
            60,
            "09:35",
        )
        if label is None:
            raise ValueError(f"complete outcome bars unavailable for {row['symbol']}")
        output.append({
            "model_id": row["model_id"],
            "model_sha256": row["model_sha256"],
            "market_date": decision_date,
            "symbol": row["symbol"],
            "rank": row["rank"],
            "model_score": row["model_score"],
            "horizon_minutes": 60,
            **label,
            "source_manifest": str(manifest_path),
            "source_manifest_sha256": sha256(manifest_path),
            "status": "complete",
            "research_only": True,
            "execution_decision": "AVOID",
        })
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--outcomes", type=Path, required=True)
    args = parser.parse_args()
    observations = observations_for_archive(read_jsonl(args.journal), args.archive)
    rows = completed_outcomes(observations, args.archive)
    additions = append_unique(args.outcomes, rows)
    print(json.dumps({
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "available_outcomes": len(rows),
        "appended": additions,
    }, indent=2))


if __name__ == "__main__":
    main()
