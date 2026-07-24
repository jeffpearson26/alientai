from __future__ import annotations

"""Read-only integrity and timing audit for the matched catalyst panel."""

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def row_key(row: Mapping[str, Any]) -> str:
    return "|".join(str(row.get(field) or "").strip() for field in ("study_event_id", "symbol", "market_date", "study_role"))


def parse_time(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def audit(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    all_rows = list(rows)
    keys = [row_key(row) for row in all_rows]
    key_counts = Counter(keys)
    duplicates = sum(count - 1 for key, count in key_counts.items() if key.strip("|") and count > 1)
    unique_symbol_dates = {(str(row.get("symbol") or ""), str(row.get("market_date") or "")) for row in all_rows}
    malformed_as_of = 0
    as_of_date_mismatch = 0
    news_after_cutoff = 0
    news_available = 0
    option_available = 0
    option_chain_available = 0
    for row in all_rows:
        as_of = parse_time(row.get("as_of_utc"))
        if as_of is None:
            malformed_as_of += 1
        elif as_of.date().isoformat() != str(row.get("market_date") or ""):
            as_of_date_mismatch += 1
        if row.get("news_available"):
            news_available += 1
        latest_news = parse_time(row.get("news_latest_published_utc"))
        if as_of is not None and latest_news is not None and latest_news > as_of:
            news_after_cutoff += 1
        if row.get("option_available"):
            option_available += 1
        if row.get("option_chain_available"):
            option_chain_available += 1
    return {
        "status": "complete",
        "research_only": True,
        "panel_type": "matched_case_control_only",
        "rows": len(all_rows),
        "unique_row_keys": len(key_counts),
        "duplicate_row_keys": duplicates,
        "unique_symbol_market_dates": len(unique_symbol_dates),
        "news_available_rows": news_available,
        "option_available_rows": option_available,
        "option_chain_available_rows": option_chain_available,
        "malformed_as_of_rows": malformed_as_of,
        "as_of_date_mismatch_rows": as_of_date_mismatch,
        "news_after_as_of_cutoff_rows": news_after_cutoff,
        "audit_passes": duplicates == 0 and malformed_as_of == 0 and as_of_date_mismatch == 0 and news_after_cutoff == 0,
        "limitations": [
            "This verifies the compiled matched panel, not natural-universe calibration or expected trading performance.",
            "Option snapshot provenance is retained in the archive; this compact panel alone does not add a per-row option timestamp field.",
            "A passing audit does not permit model promotion, paper trading, or live trading.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit matched catalyst-panel key and timing integrity.")
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(read_jsonl(args.panel))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
