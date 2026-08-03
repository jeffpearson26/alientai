from __future__ import annotations

"""Append exact unmanaged 20/60-minute outcomes for the pick competition."""

import argparse
import csv
import gzip
import hashlib
import json
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping
from zoneinfo import ZoneInfo

from alientai_v2.research.pick_competition import post_cost_return_pct
from download_alpha_vantage_matched_premarket import archive_path


EASTERN = ZoneInfo("America/New_York")
HORIZON_BARS = {
    "20m": ("09:45:00", time(9, 50)),
    "60m": ("10:25:00", time(10, 30)),
}
STOP_LOSS_PCT = -5.0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def read_symbol_month(
    archive: Path, symbol: str, decision_date: str
) -> dict[str, dict[str, str]]:
    path = archive_path(archive, symbol, decision_date[:7])
    if not path.exists():
        raise ValueError(f"missing realtime archive for {symbol}")
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {
        str(row.get("timestamp") or ""): row
        for row in rows
        if str(row.get("timestamp") or "").startswith(decision_date)
    }


def stop_managed_exit(
    *,
    rows: Mapping[str, Mapping[str, str]],
    decision_date: str,
    entry_price: float,
    exit_bar_time: str,
    unmanaged_exit_price: float,
) -> dict[str, Any]:
    threshold = entry_price * (1.0 + STOP_LOSS_PCT / 100.0)
    entry_stamp = f"{decision_date} 09:30:00"
    exit_stamp = f"{decision_date} {exit_bar_time}"
    path = sorted(
        (
            (timestamp, row)
            for timestamp, row in rows.items()
            if entry_stamp <= timestamp <= exit_stamp
        ),
        key=lambda item: item[0],
    )
    expected = []
    cursor = datetime.strptime(entry_stamp, "%Y-%m-%d %H:%M:%S")
    final = datetime.strptime(exit_stamp, "%Y-%m-%d %H:%M:%S")
    while cursor <= final:
        expected.append(cursor.strftime("%Y-%m-%d %H:%M:%S"))
        cursor += timedelta(minutes=5)
    if [timestamp for timestamp, _ in path] != expected:
        raise ValueError("stop path lacks exact entry-to-exit candle coverage")
    for index, (timestamp, row) in enumerate(path):
        bar_open = float(row["open"])
        bar_low = float(row["low"])
        if bar_open <= threshold:
            observed = datetime.strptime(
                timestamp, "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=EASTERN)
            return {
                "stop_applied": True,
                "stop_managed_exit_price": bar_open,
                "stop_managed_exit_at_utc": observed.astimezone(
                    timezone.utc
                ).isoformat(),
                "stop_fill_rule": "observed_bar_open_gap",
            }
        if bar_low <= threshold:
            if index + 1 < len(path):
                next_timestamp, next_row = path[index + 1]
                observed = datetime.strptime(
                    next_timestamp, "%Y-%m-%d %H:%M:%S"
                ).replace(tzinfo=EASTERN)
                return {
                    "stop_applied": True,
                    "stop_managed_exit_price": float(next_row["open"]),
                    "stop_managed_exit_at_utc": observed.astimezone(
                        timezone.utc
                    ).isoformat(),
                    "stop_fill_rule": (
                        "next_bar_open_after_completed_bar_crossing"
                    ),
                }
            observed = (
                datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                .replace(tzinfo=EASTERN)
                + timedelta(minutes=5)
            )
            return {
                "stop_applied": True,
                "stop_managed_exit_price": unmanaged_exit_price,
                "stop_managed_exit_at_utc": observed.astimezone(
                    timezone.utc
                ).isoformat(),
                "stop_fill_rule": "horizon_close_after_final_bar_crossing",
            }
    exit_observed = (
        datetime.strptime(exit_stamp, "%Y-%m-%d %H:%M:%S")
        .replace(tzinfo=EASTERN)
        + timedelta(minutes=5)
    )
    return {
        "stop_applied": False,
        "stop_managed_exit_price": unmanaged_exit_price,
        "stop_managed_exit_at_utc": exit_observed.astimezone(
            timezone.utc
        ).isoformat(),
        "stop_fill_rule": "not_triggered",
    }


def validate_manifest(
    archive: Path,
    decision_date: str,
    required_complete_et: time,
) -> tuple[dict[str, Any], str]:
    path = archive / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "status": "complete",
        "bar_interval_minutes": 5,
        "timestamp_convention": "interval_start",
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"Alpha Vantage archive manifest mismatch for {key}")
    mode = str(manifest.get("mode") or "")
    entitlement = str(manifest.get("entitlement") or "")
    if (mode, entitlement) not in {
        ("current", "realtime"),
        ("historical", "historical"),
    }:
        raise ValueError("Alpha Vantage archive freshness contract is invalid")
    if mode == "current" and manifest.get("current_date") != decision_date:
        raise ValueError("realtime archive current-date mismatch")
    observed = datetime.fromisoformat(str(manifest.get("updated_at_utc") or ""))
    if observed.tzinfo is None or observed.utcoffset() is None:
        raise ValueError("archive completion timestamp must be timezone-aware")
    required = datetime.combine(
        date.fromisoformat(decision_date),
        required_complete_et,
        tzinfo=EASTERN,
    )
    if observed.astimezone(EASTERN) < required:
        raise ValueError("Alpha Vantage archive completed before the exit candle matured")
    return manifest, sha256(path)


def build_outcomes(
    *,
    submissions: Iterable[Mapping[str, Any]],
    archive: Path,
    decision_date: str,
    horizon: str,
) -> list[dict[str, Any]]:
    if horizon not in HORIZON_BARS:
        raise ValueError("intraday horizon must be 20m or 60m")
    exit_bar_time, required_complete = HORIZON_BARS[horizon]
    manifest, manifest_hash = validate_manifest(
        archive, decision_date, required_complete
    )
    mode = str(manifest["mode"])
    selected = [
        dict(row)
        for row in submissions
        if str(row.get("decision_date") or "") == decision_date
    ]
    if not selected:
        raise ValueError("no frozen submissions exist for the decision date")
    symbols = sorted(
        {
            str(symbol).strip().upper()
            for row in selected
            for symbol in row.get("picks") or []
            if str(symbol).strip()
        }
    )
    prices: dict[str, tuple[float, float, dict[str, Any]]] = {}
    for symbol in symbols:
        rows = read_symbol_month(archive, symbol, decision_date)
        entry = rows.get(f"{decision_date} 09:30:00")
        exit_row = rows.get(f"{decision_date} {exit_bar_time}")
        if entry is None or exit_row is None:
            raise ValueError(
                f"missing exact {horizon} entry/exit candle for {symbol}"
            )
        entry_price = float(entry["open"])
        exit_price = float(exit_row["close"])
        if entry_price <= 0 or exit_price <= 0:
            raise ValueError(f"invalid exact price for {symbol}")
        managed = stop_managed_exit(
            rows=rows,
            decision_date=decision_date,
            entry_price=entry_price,
            exit_bar_time=exit_bar_time,
            unmanaged_exit_price=exit_price,
        )
        prices[symbol] = (entry_price, exit_price, managed)

    exit_start = datetime.fromisoformat(
        f"{decision_date}T{exit_bar_time}"
    ).replace(tzinfo=EASTERN)
    exit_complete = exit_start + timedelta(minutes=5)
    entry_at = datetime.combine(
        date.fromisoformat(decision_date), time(9, 30), tzinfo=EASTERN
    )
    output = []
    for submission in selected:
        for symbol_value in submission.get("picks") or []:
            symbol = str(symbol_value).strip().upper()
            entry_price, exit_price, managed = prices[symbol]
            output.append(
                {
                    "round_id": submission["round_id"],
                    "participant": submission["participant"],
                    "decision_date": decision_date,
                    "symbol": symbol,
                    "horizon": horizon,
                    "entry_price": entry_price,
                    "entry_at_utc": entry_at.astimezone(timezone.utc).isoformat(),
                    "unmanaged_exit_price": exit_price,
                    "unmanaged_exit_at_utc": exit_complete.astimezone(
                        timezone.utc
                    ).isoformat(),
                    "unmanaged_net_return_pct": post_cost_return_pct(
                        entry_price, exit_price
                    ),
                    "stop_managed_exit_price": managed[
                        "stop_managed_exit_price"
                    ],
                    "stop_managed_exit_at_utc": managed[
                        "stop_managed_exit_at_utc"
                    ],
                    "stop_managed_net_return_pct": post_cost_return_pct(
                        entry_price,
                        managed["stop_managed_exit_price"],
                    ),
                    "stop_applied": managed["stop_applied"],
                    "stop_fill_rule": managed["stop_fill_rule"],
                    "stop_managed_status": "complete_5minute_observable",
                    "source": (
                        "Alpha Vantage TIME_SERIES_INTRADAY "
                        f"{'realtime' if mode == 'current' else 'historical'}"
                    ),
                    "source_manifest_sha256": manifest_hash,
                    "status": "complete_unmanaged",
                    "research_only": True,
                    "execution_decision": "AVOID",
                }
            )
    return output


def append_unique(path: Path, outcomes: Iterable[Mapping[str, Any]]) -> int:
    existing = {
        (
            str(row.get("round_id")),
            str(row.get("participant")),
            str(row.get("decision_date")),
            str(row.get("symbol")),
            str(row.get("horizon")),
        )
        for row in read_jsonl(path)
    }
    additions = []
    for outcome in outcomes:
        key = (
            str(outcome.get("round_id")),
            str(outcome.get("participant")),
            str(outcome.get("decision_date")),
            str(outcome.get("symbol")),
            str(outcome.get("horizon")),
        )
        if key not in existing:
            additions.append(dict(outcome))
            existing.add(key)
    if additions:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            for row in additions:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    return len(additions)


def summarize(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[tuple[float, float]]] = defaultdict(list)
    for row in rows:
        if str(row.get("status")) != "complete_unmanaged":
            continue
        grouped[(str(row["participant"]), str(row["horizon"]))].append(
            (
                float(row["unmanaged_net_return_pct"]),
                float(row["stop_managed_net_return_pct"]),
            )
        )
    records = []
    for (participant, horizon), pairs in sorted(grouped.items()):
        unmanaged = [pair[0] for pair in pairs]
        managed = [pair[1] for pair in pairs]
        records.append(
            {
                "participant": participant,
                "horizon": horizon,
                "picks": len(pairs),
                "unmanaged_equal_weight_basket_net_return_pct": (
                    sum(unmanaged) / len(unmanaged)
                ),
                "unmanaged_median_pick_net_return_pct": median(unmanaged),
                "unmanaged_winning_picks": sum(
                    value > 0 for value in unmanaged
                ),
                "stop_managed_equal_weight_basket_net_return_pct": (
                    sum(managed) / len(managed)
                ),
                "stop_managed_median_pick_net_return_pct": median(managed),
                "stop_managed_winning_picks": sum(
                    value > 0 for value in managed
                ),
            }
        )
    return {
        "research_only": True,
        "execution_enabled": False,
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--decision-date", required=True)
    parser.add_argument("--horizon", choices=tuple(HORIZON_BARS), required=True)
    parser.add_argument("--outcomes", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    new_rows = build_outcomes(
        submissions=read_jsonl(args.journal),
        archive=args.archive,
        decision_date=args.decision_date,
        horizon=args.horizon,
    )
    appended = append_unique(args.outcomes, new_rows)
    all_rows = read_jsonl(args.outcomes)
    payload = summarize(all_rows)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "complete",
                "horizon": args.horizon,
                "evaluated": len(new_rows),
                "appended": appended,
                "research_only": True,
                "execution_enabled": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
