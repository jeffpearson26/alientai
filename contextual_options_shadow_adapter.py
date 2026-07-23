from __future__ import annotations

"""Validate a complete daily options/technical panel for shadow-policy input.

This command never contacts a provider, starts the engine, writes settings, or
records a shadow signal.  It only converts a locally supplied complete panel to
a reviewable research payload.  A later reviewed integration may choose to
pass that payload to the existing shadow journal.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from alientai_v2.research.contextual_options_shadow_policy import select_shadow_candidates


REQUIRED_FIELDS = ("symbol", "market_date", "technical_context_score", "call_volume_unusual", "call_activity_history_count")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def validate_daily_panel(rows: Iterable[Mapping[str, Any]], minimum_universe_rows: int = 400, minimum_history: int = 10) -> list[dict[str, Any]]:
    normalized = [dict(row) for row in rows if isinstance(row, Mapping)]
    if len(normalized) < minimum_universe_rows:
        raise ValueError(f"incomplete universe: need at least {minimum_universe_rows} rows, got {len(normalized)}")
    days = {str(row.get("market_date") or "") for row in normalized}
    if len(days) != 1 or "" in days:
        raise ValueError("input must contain one non-empty market_date")
    symbols = {str(row.get("symbol") or "").upper().strip() for row in normalized}
    if "" in symbols or len(symbols) != len(normalized):
        raise ValueError("input must contain one unique non-empty row per symbol")
    missing = [field for field in REQUIRED_FIELDS if any(field not in row for row in normalized)]
    if missing:
        raise ValueError(f"input missing required fields: {', '.join(missing)}")
    usable_history = sum(1 for row in normalized if int(float(row.get("call_activity_history_count") or 0)) >= minimum_history)
    if usable_history < minimum_universe_rows * 0.90:
        raise ValueError("insufficient prior call-volume history for a complete daily unusualness calculation")
    return normalized


def build_payload(rows: Iterable[Mapping[str, Any]], minimum_universe_rows: int = 400) -> dict[str, Any]:
    panel = validate_daily_panel(rows, minimum_universe_rows=minimum_universe_rows)
    candidates = select_shadow_candidates(panel)
    return {
        "status": "research_payload_ready",
        "research_only": True,
        "execution_enabled": False,
        "market_date": panel[0]["market_date"],
        "universe_rows": len(panel),
        "candidates": candidates,
        "warning": "Payload is not journaled or traded. Review a prospective-data adapter before any shadow-journal integration.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a validation-only contextual-options shadow payload.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--minimum-universe-rows", type=int, default=400)
    args = parser.parse_args()
    payload = build_payload(read_jsonl(args.input), args.minimum_universe_rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
