from __future__ import annotations

"""Download a dated IWM equity-holdings proxy for research-universe setup.

IWM holdings are a current, public ETF holdings proxy, not official Russell
2000 constituent history. This tool never trains, trades, changes settings, or
uses a provider credential. It stores source provenance alongside the snapshot.
"""

import argparse
import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


DEFAULT_URL = (
    "https://www.ishares.com/us/products/239710/ishares-russell-2000-etf/"
    "1467271812596.ajax?fileType=csv&fileName=IWM_holdings&dataType=fund"
)


def holdings_rows(csv_text: str) -> list[dict[str, str]]:
    if csv_text.lstrip().lower().startswith("<!doctype html"):
        raise ValueError("IWM holdings endpoint returned HTML instead of CSV; download the holdings CSV manually and use --input-csv")
    lines = csv_text.replace("\ufeff", "").splitlines()
    header_index = next((idx for idx, line in enumerate(lines) if line.strip().lower().startswith("ticker,")), None)
    if header_index is None:
        raise ValueError("IWM holdings CSV does not contain a Ticker header")
    return [dict(row) for row in csv.DictReader(io.StringIO("\n".join(lines[header_index:]))) if row]


def snapshot_from_csv(csv_text: str, *, source_url: str, retrieved_at_utc: str) -> dict[str, Any]:
    rows = holdings_rows(csv_text)
    equity_rows = [
        row for row in rows
        if str(row.get("Ticker") or "").strip()
        and str(row.get("Asset Class") or "").strip().lower() == "equity"
    ]
    symbols = sorted({str(row["Ticker"]).strip().upper() for row in equity_rows})
    if not symbols:
        raise ValueError("IWM CSV contains no equity tickers")
    as_of_date = ""
    for line in csv_text.splitlines()[:20]:
        if " as of " in line.lower():
            candidate = line.split(" as of ", 1)[1].strip().strip('"')
            try:
                as_of_date = datetime.strptime(candidate, "%b %d, %Y").date().isoformat()
                break
            except ValueError:
                continue
    if not as_of_date:
        raise ValueError("IWM CSV does not contain a parseable holdings as-of date")
    return {
        "schema_version": "1",
        "universe_name": "IWM equity holdings proxy (not official Russell 2000 membership)",
        "as_of_date": as_of_date,
        "retrieved_at_utc": retrieved_at_utc,
        "source_name": "iShares IWM holdings CSV",
        "source_url": source_url,
        "symbols": symbols,
        "source_row_count": len(rows),
        "equity_row_count": len(equity_rows),
        "limitations": [
            "This is a current ETF-holdings proxy, not official Russell 2000 historical constituent membership.",
            "It may include ETF-specific implementation holdings and does not establish historical membership for backtesting.",
        ],
    }


def fetch_csv(url: str) -> str:
    request = Request(url, headers={"User-Agent": "AlienTAI research contact@example.com", "Accept": "text/csv,text/plain,*/*"})
    with urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8-sig")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download a current IWM holdings proxy with provenance.")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--input-csv", type=Path, help="Manually downloaded iShares holdings CSV; avoids any automated provider request.")
    parser.add_argument("--source-url", help="Original public source URL for a manually downloaded CSV.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    retrieved_at_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    csv_text = args.input_csv.read_text(encoding="utf-8-sig") if args.input_csv else fetch_csv(args.url)
    source_url = args.source_url or args.url
    snapshot = snapshot_from_csv(csv_text, source_url=source_url, retrieved_at_utc=retrieved_at_utc)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: snapshot[key] for key in ("universe_name", "as_of_date", "source_row_count", "equity_row_count")}, indent=2))


if __name__ == "__main__":
    main()
