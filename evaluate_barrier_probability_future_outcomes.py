from __future__ import annotations

"""Append exact future barrier outcomes without retuning the frozen model."""

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from alientai_v2.research.barrier_probability_model import (
    adjusted_daily_candles,
    resolve_barrier,
)


MODEL_ID = "barrier_probability_48_h10_alpha_vantage_v1_20260807"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def filename(symbol: str) -> str:
    return f"{symbol.replace('/', '-').replace('.', '-')}_daily.json"


def brier(rows: list[dict[str, Any]], label: str, probability: str) -> float:
    return float(
        np.mean(
            [
                (int(row[label]) - float(row[probability])) ** 2
                for row in rows
            ]
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--outcomes", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    archive_audit_path = args.archive / "content_audit.json"
    archive_audit = json.loads(
        archive_audit_path.read_text(encoding="utf-8")
    )
    if (
        archive_audit.get("status") != "PASS"
        or archive_audit.get("provider") != "Alpha Vantage"
    ):
        raise ValueError("outcome archive audit must pass")
    observations = [
        row
        for row in read_jsonl(args.journal)
        if row.get("model_id") == MODEL_ID
    ]
    existing = read_jsonl(args.outcomes)
    existing_keys = {
        (
            str(row["model_id"]),
            str(row["decision_date"]),
            str(row["symbol"]),
        )
        for row in existing
    }
    cache: dict[str, tuple[list[dict[str, Any]], dict[str, int], str]] = {}
    appended = []
    pending = []
    for observation in observations:
        decision_date = str(observation["decision_date"])
        for prediction in observation["predictions"]:
            symbol = str(prediction["symbol"])
            key = (MODEL_ID, decision_date, symbol)
            if key in existing_keys:
                continue
            if symbol not in cache:
                path = args.archive / filename(symbol)
                candles = adjusted_daily_candles(path, symbol)
                cache[symbol] = (
                    candles,
                    {
                        str(row["market_date"]): index
                        for index, row in enumerate(candles)
                    },
                    sha256(path),
                )
            candles, date_index, source_hash = cache[symbol]
            index = date_index.get(decision_date)
            if index is None:
                pending.append(
                    {
                        "decision_date": decision_date,
                        "symbol": symbol,
                        "reason": "decision date absent from outcome source",
                    }
                )
                continue
            if not np.isclose(
                float(candles[index]["close"]),
                float(prediction["decision_adjusted_close"]),
                rtol=1e-10,
                atol=1e-10,
            ):
                raise ValueError(
                    f"{symbol} {decision_date}: decision close changed"
                )
            result = resolve_barrier(
                candles,
                index,
                upper_pct=0.015,
                lower_pct=0.005,
                horizon_sessions=10,
            )
            if result.get("label_lower_bound") is None:
                pending.append(
                    {
                        "decision_date": decision_date,
                        "symbol": symbol,
                        "reason": result["outcome_status"],
                    }
                )
                continue
            appended.append(
                {
                    "schema_version": 1,
                    "model_id": MODEL_ID,
                    "decision_date": decision_date,
                    "symbol": symbol,
                    "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
                    "source_provider": "Alpha Vantage",
                    "source_archive": str(args.archive.resolve()),
                    "source_audit_sha256": sha256(archive_audit_path),
                    "source_file_sha256": source_hash,
                    "conservative_lower_probability": prediction[
                        "conservative_lower_probability"
                    ],
                    "optimistic_upper_probability": prediction[
                        "optimistic_upper_probability"
                    ],
                    "diagnostic_midpoint_probability": prediction[
                        "diagnostic_midpoint_probability"
                    ],
                    **result,
                    "research_only": True,
                    "execution_decision": "AVOID",
                }
            )
            existing_keys.add(key)

    if appended:
        args.outcomes.parent.mkdir(parents=True, exist_ok=True)
        with args.outcomes.open("a", encoding="utf-8", newline="\n") as handle:
            for row in appended:
                handle.write(
                    json.dumps(row, sort_keys=True, separators=(",", ":"))
                    + "\n"
                )
    all_outcomes = read_jsonl(args.outcomes)
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in all_outcomes:
        by_date[str(row["decision_date"])].append(row)
    summary = {
        "status": "collecting",
        "model_id": MODEL_ID,
        "research_only": True,
        "execution_enabled": False,
        "completed_rows": len(all_outcomes),
        "completed_decision_dates": len(by_date),
        "pending_rows_this_pass": len(pending),
        "new_rows_this_pass": len(appended),
        "conservative_brier": (
            brier(
                all_outcomes,
                "label_lower_bound",
                "conservative_lower_probability",
            )
            if all_outcomes
            else None
        ),
        "optimistic_brier": (
            brier(
                all_outcomes,
                "label_upper_bound",
                "optimistic_upper_probability",
            )
            if all_outcomes
            else None
        ),
        "outcome_counts": {
            status: sum(
                row["outcome_status"] == status for row in all_outcomes
            )
            for status in sorted(
                {row["outcome_status"] for row in all_outcomes}
            )
        },
        "warning": (
            "prospective evidence remains too small until many independent "
            "decision dates mature; no trading is authorized"
        ),
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
