from __future__ import annotations

import argparse
import csv
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


BUILD = "ALIENTAI_V2_DAILY_MAX_HISTORY_SCHWAB_DOWNLOADER_V1"

PROJECT_ROOT = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / ".env"

DEFAULT_SYMBOLS_FILE = PROJECT_ROOT / "v2_live_watchlist_symbols.txt"
DEFAULT_OUT_DIR = PROJECT_ROOT / "data_v2" / "daily_schwab_max_history"

TOKEN_PATH = PROJECT_ROOT / "token.json"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and value:
            os.environ[key] = value


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}

    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def read_symbols(path: Path, limit: int = 0) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"Symbols file not found: {path}")

    symbols: List[str] = []

    for line in path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        symbol = line.strip().upper()

        if not symbol or symbol.startswith("#"):
            continue

        symbols.append(symbol)

    symbols = sorted(set(symbols))

    if limit and limit > 0:
        symbols = symbols[:limit]

    return symbols


def token_from_token_json() -> str:
    token_data = read_json(TOKEN_PATH)

    access_token = str(token_data.get("access_token") or "").strip()

    if access_token:
        return access_token

    # Some older token files may nest it.
    for key in ["token", "schwab_token"]:
        nested = token_data.get(key)

        if isinstance(nested, dict):
            access_token = str(nested.get("access_token") or "").strip()

            if access_token:
                return access_token

    return ""


def schwab_headers() -> Dict[str, str]:
    token = token_from_token_json()

    if not token:
        raise RuntimeError(
            "No Schwab access_token found in token.json. "
            "Refresh/re-authorize Schwab first."
        )

    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


def ms_from_dt(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def parse_schwab_candles(payload: Dict[str, Any], symbol: str) -> List[Dict[str, Any]]:
    candles_raw = payload.get("candles") or []

    rows: List[Dict[str, Any]] = []

    for c in candles_raw:
        datetime_ms = safe_int(c.get("datetime"), 0)

        if datetime_ms <= 0:
            continue

        dt_utc = datetime.fromtimestamp(datetime_ms / 1000.0, tz=timezone.utc)

        rows.append({
            "symbol": symbol.upper(),
            "datetime_ms": datetime_ms,
            "datetime_utc": dt_utc.isoformat(),
            "date": dt_utc.date().isoformat(),
            "open": safe_float(c.get("open"), 0.0),
            "high": safe_float(c.get("high"), 0.0),
            "low": safe_float(c.get("low"), 0.0),
            "close": safe_float(c.get("close"), 0.0),
            "volume": safe_int(c.get("volume"), 0),
        })

    rows.sort(key=lambda r: int(r.get("datetime_ms") or 0))
    return rows


def schwab_daily_history(
    *,
    symbol: str,
    years_back: float,
    include_extended_hours: bool,
    timeout: int = 60,
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Downloads daily candles from Schwab pricehistory.

    Schwab may cap how far back it returns, even if we request more years.
    That is okay. We ask for a very old start date and accept as much as
    Schwab returns.
    """
    end_dt = utc_now()
    start_dt = end_dt - timedelta(days=int(years_back * 365.25))

    url = "https://api.schwabapi.com/marketdata/v1/pricehistory"

    params = {
        "symbol": symbol.upper(),
        "periodType": "year",
        "frequencyType": "daily",
        "frequency": "1",
        "startDate": str(ms_from_dt(start_dt)),
        "endDate": str(ms_from_dt(end_dt)),
        "needExtendedHoursData": str(bool(include_extended_hours)).lower(),
        "needPreviousClose": "true",
    }

    response = requests.get(
        url,
        headers=schwab_headers(),
        params=params,
        timeout=timeout,
    )

    if response.status_code == 401:
        raise RuntimeError("Schwab HTTP 401 unauthorized. Token likely expired. Refresh Schwab token.")

    if response.status_code == 403:
        raise RuntimeError("Schwab HTTP 403 forbidden. Check Schwab app/data permissions.")

    if response.status_code not in {200, 201}:
        raise RuntimeError(f"Schwab HTTP {response.status_code}: {response.text[:500]}")

    payload = response.json()

    rows = parse_schwab_candles(payload, symbol)

    return rows, response.url


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "symbol",
        "datetime_ms",
        "datetime_utc",
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def append_report(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "time",
        "symbol",
        "status",
        "candles",
        "oldest",
        "newest",
        "output_file",
        "message",
    ]

    exists = path.exists()

    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not exists:
            writer.writeheader()

        writer.writerow({
            "time": row.get("time", ""),
            "symbol": row.get("symbol", ""),
            "status": row.get("status", ""),
            "candles": row.get("candles", 0),
            "oldest": row.get("oldest", ""),
            "newest": row.get("newest", ""),
            "output_file": row.get("output_file", ""),
            "message": row.get("message", ""),
        })


def existing_file_has_rows(path: Path) -> bool:
    if not path.exists():
        return False

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for _ in reader:
                return True
    except Exception:
        return False

    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Download as much Schwab daily candle history as available.")
    parser.add_argument("--symbols", default=str(DEFAULT_SYMBOLS_FILE))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--years-back", type=float, default=30.0)
    parser.add_argument("--delay", type=float, default=0.75)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--extended-hours", action="store_true")
    parser.add_argument("--only-symbol", default="")
    args = parser.parse_args()

    load_env_file(ENV_PATH)

    symbols_file = Path(args.symbols)
    out_dir = Path(args.out_dir)
    report_path = out_dir / "daily_download_report.csv"
    summary_path = out_dir / "daily_download_summary.json"

    if args.only_symbol:
        symbols = [args.only_symbol.upper().strip()]
    else:
        symbols = read_symbols(symbols_file, limit=args.limit)

    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Build: {BUILD}")
    print(f"Symbols file: {symbols_file}")
    print(f"Symbols loaded: {len(symbols)}")
    print(f"Output dir: {out_dir}")
    print(f"Years back requested: {args.years_back}")
    print(f"Extended hours: {args.extended_hours}")
    print(f"Resume: {args.resume}")
    print(f"Delay seconds: {args.delay}")
    print("This does NOT touch the V2 paper account.")
    print("")

    summaries: List[Dict[str, Any]] = []

    for index, symbol in enumerate(symbols, start=1):
        output_file = out_dir / f"{symbol}_schwab_1d_max.csv"

        if args.resume and existing_file_has_rows(output_file):
            print(f"[{index}/{len(symbols)}] SKIP existing {symbol}")

            row = {
                "time": now_iso(),
                "symbol": symbol,
                "status": "skipped_existing",
                "candles": "",
                "oldest": "",
                "newest": "",
                "output_file": str(output_file),
                "message": "Existing file found and resume enabled.",
            }
            append_report(report_path, row)
            summaries.append(row)
            continue

        print(f"[{index}/{len(symbols)}] Downloading daily {symbol}...")

        try:
            rows, request_url = schwab_daily_history(
                symbol=symbol,
                years_back=args.years_back,
                include_extended_hours=args.extended_hours,
            )

            if rows:
                write_csv(output_file, rows)

                oldest = str(rows[0].get("date") or rows[0].get("datetime_utc") or "")
                newest = str(rows[-1].get("date") or rows[-1].get("datetime_utc") or "")

                row = {
                    "time": now_iso(),
                    "symbol": symbol,
                    "status": "success",
                    "candles": len(rows),
                    "oldest": oldest,
                    "newest": newest,
                    "output_file": str(output_file),
                    "message": "OK",
                }

                print(f"  OK {symbol}: {len(rows)} daily candles | {oldest} -> {newest}")

            else:
                row = {
                    "time": now_iso(),
                    "symbol": symbol,
                    "status": "no_data",
                    "candles": 0,
                    "oldest": "",
                    "newest": "",
                    "output_file": "",
                    "message": "Schwab returned no candles.",
                }

                print(f"  NO DATA {symbol}")

        except Exception as exc:
            row = {
                "time": now_iso(),
                "symbol": symbol,
                "status": "error",
                "candles": 0,
                "oldest": "",
                "newest": "",
                "output_file": "",
                "message": str(exc),
            }

            print(f"  ERROR {symbol}: {exc}")

            if "401 unauthorized" in str(exc).lower() or "token likely expired" in str(exc).lower():
                print("")
                print("STOPPING: Schwab token is expired. Run:")
                print("python .\\refresh_schwab_token_standalone.py")
                append_report(report_path, row)
                summaries.append(row)
                break

        append_report(report_path, row)
        summaries.append(row)

        if args.delay > 0:
            time.sleep(args.delay)

    successes = [r for r in summaries if r.get("status") == "success"]
    errors = [r for r in summaries if r.get("status") == "error"]
    no_data = [r for r in summaries if r.get("status") == "no_data"]
    skipped = [r for r in summaries if r.get("status") == "skipped_existing"]

    total_candles = 0

    for r in successes:
        total_candles += safe_int(r.get("candles"), 0)

    summary = {
        "status": "complete",
        "finished_at": now_iso(),
        "build": BUILD,
        "symbols_requested": len(symbols),
        "successes": len(successes),
        "errors": len(errors),
        "no_data": len(no_data),
        "skipped_existing": len(skipped),
        "total_daily_candles": total_candles,
        "years_back_requested": args.years_back,
        "out_dir": str(out_dir),
        "report_path": str(report_path),
    }

    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("")
    print("DONE")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

