from __future__ import annotations

"""Build paired, exact-key Nasdaq catalyst-ablation panels."""

import argparse
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping


INSIDER_FEATURES = (
    "insider_purchase_available",
    "insider_purchase_total_visible",
    "insider_purchase_count_7d",
    "insider_purchase_count_30d",
    "insider_purchase_count_90d",
    "insider_unique_buyers_7d",
    "insider_unique_buyers_30d",
    "insider_unique_buyers_90d",
    "insider_log_total_value_7d",
    "insider_log_total_value_30d",
    "insider_log_total_value_90d",
    "insider_max_purchase_value_7d",
    "insider_max_purchase_value_30d",
    "insider_max_purchase_value_90d",
    "insider_officer_buy_count_30d",
    "insider_director_buy_count_30d",
    "insider_ten_percent_owner_buy_count_30d",
    "insider_cluster_buy_30d",
    "insider_large_purchase_30d",
    "insider_max_ownership_increase_ratio_30d",
    "insider_days_since_latest_purchase",
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _market_day(row: Mapping[str, Any]) -> str:
    return str(row.get("market_date") or "")


def _visible_on_market_day(row: Mapping[str, Any]) -> bool:
    raw = str(row.get("as_of_utc") or "").strip()
    if not raw:
        return False
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date() <= date.fromisoformat(
            _market_day(row)
        )
    except ValueError:
        return False


def paired_panels(
    base_rows: Iterable[Mapping[str, Any]],
    catalyst_rows: Iterable[Mapping[str, Any]],
    feature_names: Iterable[str] = INSIDER_FEATURES,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    catalyst_by_key: dict[tuple[str, str], Mapping[str, Any]] = {}
    duplicates = set()
    rejected_future = 0
    for row in catalyst_rows:
        key = (str(row.get("symbol") or "").upper(), _market_day(row))
        if not all(key):
            continue
        if not _visible_on_market_day(row):
            rejected_future += 1
            continue
        if key in catalyst_by_key:
            duplicates.add(key)
        catalyst_by_key[key] = row
    if duplicates:
        raise ValueError(f"duplicate catalyst keys: {len(duplicates)}")

    baseline, enriched = [], []
    names = tuple(feature_names)
    for raw in base_rows:
        row = dict(raw)
        key = (str(row.get("symbol") or "").upper(), _market_day(row))
        catalyst = catalyst_by_key.get(key)
        if catalyst is None:
            continue
        baseline.append(row)
        joined = dict(row)
        for name in names:
            value = catalyst.get(name)
            joined[f"technical_catalyst_{name}"] = 0.0 if value is None else value
        enriched.append(joined)
    summary = {
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "base_rows": len(list(base_rows)) if isinstance(base_rows, list) else None,
        "eligible_catalyst_keys": len(catalyst_by_key),
        "paired_rows": len(baseline),
        "rejected_future_or_invalid_rows": rejected_future,
        "feature_names": list(names),
    }
    return baseline, enriched, summary


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--catalyst", type=Path, required=True)
    parser.add_argument("--baseline-output", type=Path, required=True)
    parser.add_argument("--enriched-output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    base_rows = read_jsonl(args.base)
    baseline, enriched, summary = paired_panels(base_rows, read_jsonl(args.catalyst))
    write_jsonl(args.baseline_output, baseline)
    write_jsonl(args.enriched_output, enriched)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
