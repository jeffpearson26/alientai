from __future__ import annotations

"""Build exact-universe event requests for a prospective 09:25 ET snapshot."""

import argparse
import json
from datetime import date, datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


EASTERN = ZoneInfo("America/New_York")
FROZEN_CUTOFF = time(9, 25)


def symbols(path: Path) -> list[str]:
    values = [
        line.strip().lstrip("\ufeff").upper()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not values or len(values) != len(set(values)):
        raise ValueError("symbols file must contain unique nonblank symbols")
    return values


def build_requests(
    symbol_values: list[str],
    market_date_text: str,
    as_of_utc_text: str,
) -> list[dict]:
    market_date = date.fromisoformat(market_date_text)
    as_of = datetime.fromisoformat(as_of_utc_text)
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of_utc must be timezone-aware")
    eastern = as_of.astimezone(EASTERN)
    if eastern.date() != market_date or eastern.time().replace(tzinfo=None) != FROZEN_CUTOFF:
        raise ValueError("as_of_utc must equal 09:25 ET on market_date")
    normalized = as_of.astimezone(timezone.utc).isoformat()
    return [
        {
            "as_of_utc": normalized,
            "market_date": market_date.isoformat(),
            "research_only": True,
            "study_role": "all",
            "symbol": symbol,
        }
        for symbol in symbol_values
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--market-date", required=True)
    parser.add_argument("--as-of-utc", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = build_requests(
        symbols(args.symbols_file),
        args.market_date,
        args.as_of_utc,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "complete",
                "research_only": True,
                "execution_enabled": False,
                "market_date": args.market_date,
                "rows": len(rows),
                "output": str(args.output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
