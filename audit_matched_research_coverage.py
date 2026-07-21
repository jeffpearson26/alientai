from __future__ import annotations

"""Read-only coverage and timing audit for the matched premarket research study."""

import argparse
import json
from collections import Counter
from datetime import datetime, time
from pathlib import Path
from typing import Any, Iterable, Mapping


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def matched_row_key(row: Mapping[str, Any]) -> str:
    """Return the actual identity of a winner/control study row.

    ``study_event_id`` identifies one winner event and is intentionally shared by
    its matched controls, so it must not be used as a unique row key.
    """
    return "|".join(
        str(row.get(name) or "").strip()
        for name in ("study_event_id", "symbol", "market_date", "study_role")
    )


def count_duplicate_values(rows: Iterable[Mapping[str, Any]], key: str | None = None) -> int:
    values = [matched_row_key(row) if key is None else str(row.get(key) or "").strip() for row in rows]
    counts = Counter(value for value in values if value)
    return sum(count - 1 for count in counts.values() if count > 1)


def cutoff_violations(rows: Iterable[Mapping[str, Any]]) -> int:
    """Count premarket rows whose recorded feature cutoff is after 09:25 ET."""
    violations = 0
    for row in rows:
        if not row.get("premarket_available"):
            continue
        stamp = str(row.get("premarket_last_timestamp_et") or "").strip()
        try:
            parsed = datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            violations += 1
            continue
        if parsed.time() > time(9, 25):
            violations += 1
    return violations


def coverage_summary(
    base_rows: list[Mapping[str, Any]],
    feature_rows: list[Mapping[str, Any]],
    label_rows: list[Mapping[str, Any]],
    option_rows: list[Mapping[str, Any]],
    fundamental_rows: list[Mapping[str, Any]],
) -> dict[str, Any]:
    base_ids = {matched_row_key(row) for row in base_rows}
    feature_ids = {matched_row_key(row) for row in feature_rows}
    label_ids = {matched_row_key(row) for row in label_rows}
    available_features = sum(bool(row.get("premarket_available")) for row in feature_rows)
    available_labels = sum(bool(row.get("premarket_label_available")) for row in label_rows)
    available_options = sum(bool(row.get("option_chain_available")) for row in option_rows)
    available_fundamentals = sum(bool(row.get("earnings_estimate_available")) for row in fundamental_rows)
    base_count = len(base_rows)

    return {
        "status": "complete",
        "base_rows": base_count,
        "base_row_key_duplicates": count_duplicate_values(base_rows),
        "premarket_features": {
            "rows": len(feature_rows),
            "row_key_duplicates": count_duplicate_values(feature_rows),
            "matched_base_rows": len(base_ids & feature_ids),
            "missing_base_rows": len(base_ids - feature_ids),
            "available_rows": available_features,
            "available_pct": round(100 * available_features / max(1, base_count), 6),
            "cutoff_violations": cutoff_violations(feature_rows),
        },
        "open_entry_labels": {
            "rows": len(label_rows),
            "row_key_duplicates": count_duplicate_values(label_rows),
            "matched_base_rows": len(base_ids & label_ids),
            "missing_base_rows": len(base_ids - label_ids),
            "available_rows": available_labels,
            "available_pct": round(100 * available_labels / max(1, base_count), 6),
        },
        "option_features": {
            "rows": len(option_rows),
            "available_rows": available_options,
            "note": "Rows are from the smaller matched option-event study; do not treat this count as complete coverage of the 18,326-row premarket study.",
        },
        "fundamental_features": {
            "rows": len(fundamental_rows),
            "earnings_estimate_available_rows": available_fundamentals,
            "note": "Snapshot features must be joined point-in-time by availability timestamp before model use.",
        },
        "audit_passes": (
            count_duplicate_values(base_rows) == 0
            and count_duplicate_values(feature_rows) == 0
            and count_duplicate_values(label_rows) == 0
            and len(base_ids - feature_ids) == 0
            and len(base_ids - label_ids) == 0
            and cutoff_violations(feature_rows) == 0
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rows", type=Path, required=True)
    parser.add_argument("--premarket-features", type=Path, required=True)
    parser.add_argument("--premarket-labels", type=Path, required=True)
    parser.add_argument("--option-features", type=Path, required=True)
    parser.add_argument("--fundamental-features", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = coverage_summary(
        read_jsonl(args.base_rows),
        read_jsonl(args.premarket_features),
        read_jsonl(args.premarket_labels),
        read_jsonl(args.option_features),
        read_jsonl(args.fundamental_features),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
