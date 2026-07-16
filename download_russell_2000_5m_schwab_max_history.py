from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests

from download_russell_2000_5m_schwab import (
    SCHWAB_PRICE_HISTORY_URL,
    get_access_token,
    refresh_schwab_token,
    read_symbols,
    candles_to_rows,
    write_symbol_csv,
    load_json,
    save_json,
    now_iso,
)


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_SYMBOL_FILE = PROJECT_ROOT / "russell_2000_symbols.txt"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data_v2" / "russell_2000_5m_schwab_max"


def dt_to_ms(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def ms_to_iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def append_report_row(report_path: Path, row: Dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "time",
        "symbol",
        "chunk_start_utc",
        "chunk_end_utc",
        "status",
        "candles",
        "oldest_candle_utc",
        "newest_candle_utc",
        "message",
    ]

    exists = report_path.exists()

    with report_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not exists:
            writer.writeheader()

        writer.writerow({
            "time": row.get("time", ""),
            "symbol": row.get("symbol", ""),
            "chunk_start_utc": row.get("chunk_start_utc", ""),
            "chunk_end_utc": row.get("chunk_end_utc", ""),
            "status": row.get("status", ""),
            "candles": row.get("candles", 0),
            "oldest_candle_utc": row.get("oldest_candle_utc", ""),
            "newest_candle_utc": row.get("newest_candle_utc", ""),
            "message": row.get("message", ""),
        })


def download_price_history_range(
    symbol: str,
    start_dt: datetime,
    end_dt: datetime,
    need_extended_hours: bool,
) -> Tuple[str, Dict[str, Any]]:
    access_token = get_access_token()

    params = {
        "symbol": symbol,
        "periodType": "day",
        "frequencyType": "minute",
        "frequency": "5",
        "startDate": str(dt_to_ms(start_dt)),
        "endDate": str(dt_to_ms(end_dt)),
        "needExtendedHoursData": "true" if need_extended_hours else "false",
        "needPreviousClose": "false",
    }

    url = SCHWAB_PRICE_HISTORY_URL + "?" + urllib.parse.urlencode(params)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    response = requests.get(url, headers=headers, timeout=45)

    if response.status_code == 401:
        refresh_result = refresh_schwab_token()
        if refresh_result.get("status") == "success":
            access_token = get_access_token()
            headers["Authorization"] = f"Bearer {access_token}"
            response = requests.get(url, headers=headers, timeout=45)

    if response.status_code != 200:
        return "error", {
            "symbol": symbol,
            "http_status": response.status_code,
            "message": response.text[:500],
            "url": url,
        }

    try:
        payload = response.json()
    except Exception as exc:
        return "error", {
            "symbol": symbol,
            "message": f"Could not parse JSON: {exc}",
            "text": response.text[:500],
            "url": url,
        }

    candles = payload.get("candles", [])

    if not isinstance(candles, list):
        candles = []

    return "success", {
        "symbol": symbol,
        "candles": candles,
        "empty": payload.get("empty"),
        "url": url,
    }


def load_existing_rows(path: Path) -> Dict[int, Dict[str, Any]]:
    rows_by_ms: Dict[int, Dict[str, Any]] = {}

    if not path.exists():
        return rows_by_ms

    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    ms = int(row.get("datetime_ms") or 0)
                except Exception:
                    continue

                if ms > 0:
                    rows_by_ms[ms] = row
    except Exception:
        return rows_by_ms

    return rows_by_ms


def save_merged_symbol_file(path: Path, rows_by_ms: Dict[int, Dict[str, Any]]) -> None:
    rows = [rows_by_ms[k] for k in sorted(rows_by_ms.keys())]
    write_symbol_csv(path, rows)


def summarize_rows(rows_by_ms: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    if not rows_by_ms:
        return {
            "candles": 0,
            "oldest": "",
            "newest": "",
        }

    keys = sorted(rows_by_ms.keys())

    return {
        "candles": len(keys),
        "oldest": ms_to_iso(keys[0]),
        "newest": ms_to_iso(keys[-1]),
    }


def load_previous_symbol_summaries(summary_path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Reads previous max_history_download_summary.json so --resume can skip
    symbols that already completed, including no_data symbols.
    """
    if not summary_path.exists():
        return {}

    try:
        data = json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    summaries = {}

    for row in data.get("symbol_summaries", []):
        symbol = str(row.get("symbol") or "").upper().strip()
        if symbol:
            summaries[symbol] = row

    return summaries

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download Russell 2000 5-minute candles as far back as Schwab allows."
    )
    parser.add_argument("--symbols", default=str(DEFAULT_SYMBOL_FILE))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--years-back", type=float, default=3.0)
    parser.add_argument("--chunk-days", type=int, default=30)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--extended-hours", action="store_true")
    parser.add_argument("--max-empty-chunks", type=int, default=3)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    symbol_path = Path(args.symbols)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    report_path = out_dir / "max_history_download_report.csv"
    summary_path = out_dir / "max_history_download_summary.json"

    previous_summaries = load_previous_symbol_summaries(summary_path) if args.resume else {}

    symbols = read_symbols(symbol_path, limit=args.limit)

    end_anchor = datetime.now(timezone.utc)
    oldest_requested = end_anchor - timedelta(days=int(args.years_back * 365.25))

    print("Build: ALIENTAI_RUSSELL_2000_5M_MAX_HISTORY_DOWNLOADER_V1")
    print(f"Symbols loaded: {len(symbols)}")
    print(f"Output dir: {out_dir}")
    print(f"Years back requested: {args.years_back}")
    print(f"Oldest requested UTC: {oldest_requested.isoformat()}")
    print(f"Chunk days: {args.chunk_days}")
    print(f"Extended hours: {args.extended_hours}")
    print(f"Delay seconds: {args.delay}")
    print("This does NOT touch the V2 paper account.")
    print("")

    overall = {
        "status": "running",
        "started_at": now_iso(),
        "symbols_requested": len(symbols),
        "years_back_requested": args.years_back,
        "chunk_days": args.chunk_days,
        "extended_hours": args.extended_hours,
        "symbol_summaries": [],
    }

    for symbol_index, symbol in enumerate(symbols, start=1):
        output_file = out_dir / f"{symbol}_schwab_5m_max.csv"

        previous = previous_summaries.get(symbol)
        if args.resume and previous is not None:
            previous_candles = int(previous.get("candles") or 0)
            previous_output = str(previous.get("output_file") or "")

            if previous_candles > 0 and previous_output:
                print(f"[{symbol_index}/{len(symbols)}] SKIP completed success {symbol}: {previous_candles} candles")
                overall["symbol_summaries"].append(previous)
                continue

            if previous_candles == 0:
                print(f"[{symbol_index}/{len(symbols)}] SKIP completed no_data {symbol}")
                overall["symbol_summaries"].append(previous)
                continue
        rows_by_ms = load_existing_rows(output_file) if args.resume else {}

        symbol_empty_chunks = 0
        chunks_attempted = 0
        chunks_with_data = 0

        chunk_end = end_anchor

        print(f"[{symbol_index}/{len(symbols)}] {symbol}")

        while chunk_end > oldest_requested:
            chunk_start = max(oldest_requested, chunk_end - timedelta(days=args.chunk_days))

            chunks_attempted += 1

            print(
                f"  chunk {chunks_attempted}: "
                f"{chunk_start.date()} -> {chunk_end.date()}",
                end="",
            )

            status, result = download_price_history_range(
                symbol=symbol,
                start_dt=chunk_start,
                end_dt=chunk_end,
                need_extended_hours=args.extended_hours,
            )

            if status != "success":
                message = str(result.get("message", "unknown error"))
                print(f" ERROR {message[:120]}")

                append_report_row(report_path, {
                    "time": now_iso(),
                    "symbol": symbol,
                    "chunk_start_utc": chunk_start.isoformat(),
                    "chunk_end_utc": chunk_end.isoformat(),
                    "status": "error",
                    "candles": 0,
                    "message": message,
                })

                # Do not kill the whole run for one bad chunk.
                symbol_empty_chunks += 1

                if symbol_empty_chunks >= args.max_empty_chunks:
                    print(f"  stopping {symbol}: too many empty/error chunks.")
                    break

                time.sleep(args.delay)
                chunk_end = chunk_start
                continue

            candles = result.get("candles", [])
            rows = candles_to_rows(symbol, candles)

            if not rows:
                symbol_empty_chunks += 1
                print(" no data")

                append_report_row(report_path, {
                    "time": now_iso(),
                    "symbol": symbol,
                    "chunk_start_utc": chunk_start.isoformat(),
                    "chunk_end_utc": chunk_end.isoformat(),
                    "status": "no_data",
                    "candles": 0,
                    "message": "No candles returned.",
                })

                if symbol_empty_chunks >= args.max_empty_chunks:
                    print(f"  stopping {symbol}: reached {args.max_empty_chunks} empty chunks.")
                    break
            else:
                symbol_empty_chunks = 0
                chunks_with_data += 1

                for row in rows:
                    try:
                        ms = int(row.get("datetime_ms") or 0)
                    except Exception:
                        continue

                    if ms > 0:
                        rows_by_ms[ms] = row

                first_ms = int(rows[0].get("datetime_ms") or 0)
                last_ms = int(rows[-1].get("datetime_ms") or 0)

                print(f" OK {len(rows)} candles | {ms_to_iso(first_ms)} -> {ms_to_iso(last_ms)}")

                append_report_row(report_path, {
                    "time": now_iso(),
                    "symbol": symbol,
                    "chunk_start_utc": chunk_start.isoformat(),
                    "chunk_end_utc": chunk_end.isoformat(),
                    "status": "success",
                    "candles": len(rows),
                    "oldest_candle_utc": ms_to_iso(first_ms),
                    "newest_candle_utc": ms_to_iso(last_ms),
                    "message": "",
                })

                save_merged_symbol_file(output_file, rows_by_ms)

            time.sleep(args.delay)
            chunk_end = chunk_start

        symbol_summary = summarize_rows(rows_by_ms)
        symbol_summary.update({
            "symbol": symbol,
            "output_file": str(output_file) if rows_by_ms else "",
            "chunks_attempted": chunks_attempted,
            "chunks_with_data": chunks_with_data,
        })

        overall["symbol_summaries"].append(symbol_summary)

        print(
            f"  SUMMARY {symbol}: "
            f"{symbol_summary['candles']} candles | "
            f"{symbol_summary['oldest']} -> {symbol_summary['newest']}"
        )
        print("")

        overall["status"] = "running"
        overall["updated_at"] = now_iso()
        save_json(summary_path, overall)

    overall["status"] = "complete"
    overall["finished_at"] = now_iso()
    save_json(summary_path, overall)

    print("DONE")
    print(json.dumps({
        "status": "complete",
        "symbols_requested": len(symbols),
        "summary_path": str(summary_path),
        "report_path": str(report_path),
        "out_dir": str(out_dir),
    }, indent=2))


if __name__ == "__main__":
    main()

