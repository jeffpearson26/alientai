from __future__ import annotations

"""Capture a bounded, research-only Schwab five-minute snapshot."""

import argparse
import hashlib
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from download_russell_2000_5m_schwab import candles_to_rows, write_symbol_csv
from download_russell_2000_5m_schwab_max_history import download_price_history_range


EASTERN = ZoneInfo("America/New_York")


def read_symbols(path: Path) -> list[str]:
    symbols = [
        line.strip().upper()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not symbols or len(symbols) != len(set(symbols)):
        raise ValueError("symbols file is empty or contains duplicates")
    return symbols


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def capture(
    symbols: list[str],
    decision_date: str,
    output: Path,
    now_utc: datetime | None = None,
    purpose: str = "entry",
) -> dict[str, object]:
    decision = date.fromisoformat(decision_date)
    observed = now_utc or datetime.now(timezone.utc)
    if observed.tzinfo is None or observed.utcoffset() is None:
        raise ValueError("now_utc must be timezone-aware")
    now_et = observed.astimezone(EASTERN)
    if now_et.date() != decision:
        raise ValueError("decision date must be the current Eastern date")
    if purpose == "entry":
        if not time(9, 30) <= now_et.time() < time(9, 35):
            raise ValueError(
                "entry snapshot must be captured from 09:30 through 09:34:59 ET"
            )
    elif purpose == "outcome":
        if now_et.time() < time(10, 35):
            raise ValueError("outcome snapshot is unavailable before 10:35 ET")
    else:
        raise ValueError("purpose must be entry or outcome")

    start = datetime.combine(decision, time(0, 0), tzinfo=EASTERN).astimezone(timezone.utc)
    output.mkdir(parents=True, exist_ok=False)
    summaries = []
    for symbol in symbols:
        status, payload = download_price_history_range(
            symbol,
            start,
            observed,
            True,
        )
        candles = payload.get("candles") or []
        if status != "success" or not candles:
            raise RuntimeError(
                f"Schwab snapshot failed for {symbol}: "
                f"{payload.get('http_status') or payload.get('message') or 'no candles'}"
            )
        rows = candles_to_rows(symbol, candles)
        path = output / f"{symbol}_schwab_5m_max.csv"
        write_symbol_csv(path, rows)
        summaries.append({
            "symbol": symbol,
            "rows": len(rows),
            "sha256": sha256(path),
        })

    manifest = {
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "source": "Schwab pricehistory",
        "mode": "current",
        "bar_interval_minutes": 5,
        "timestamp_convention": "interval_start",
        "extended_hours": True,
        "purpose": purpose,
        "decision_date": decision_date,
        "captured_at_utc": observed.astimezone(timezone.utc).isoformat(),
        "symbols": summaries,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--decision-date", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--purpose",
        choices=("entry", "outcome"),
        default="entry",
        help="entry enforces 09:30-09:34:59 ET; outcome enforces 10:35 ET or later",
    )
    args = parser.parse_args()
    manifest = capture(
        read_symbols(args.symbols_file),
        args.decision_date,
        args.output,
        purpose=args.purpose,
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
