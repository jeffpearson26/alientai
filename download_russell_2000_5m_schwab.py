from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


PROJECT_ROOT = Path(__file__).resolve().parent
TOKEN_PATH = PROJECT_ROOT / "token.json"
ENV_PATH = PROJECT_ROOT / ".env"

DEFAULT_SYMBOL_FILE = PROJECT_ROOT / "russell_2000_symbols.txt"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data_v2" / "russell_2000_5m_schwab"

SCHWAB_TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"
SCHWAB_PRICE_HISTORY_URL = "https://api.schwabapi.com/marketdata/v1/pricehistory"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


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


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def token_has_access_token(token: Dict[str, Any]) -> bool:
    return bool(token.get("access_token"))


def token_expired_or_close(token: Dict[str, Any]) -> bool:
    """
    Schwab access tokens are short-lived.
    If token has expires_at, use it.
    If not, assume we should try using it first.
    """

    expires_at = token.get("expires_at")

    if not expires_at:
        return False

    try:
        return time.time() > float(expires_at) - 60
    except Exception:
        return False


def refresh_schwab_token() -> Dict[str, Any]:
    load_env_file(ENV_PATH)

    client_id = os.environ.get("SCHWAB_CLIENT_ID")
    client_secret = os.environ.get("SCHWAB_CLIENT_SECRET")

    token = load_json(TOKEN_PATH, {})
    refresh_token = token.get("refresh_token")

    if not client_id or not client_secret:
        return {
            "status": "error",
            "message": "SCHWAB_CLIENT_ID or SCHWAB_CLIENT_SECRET missing from .env.",
        }

    if not refresh_token:
        return {
            "status": "error",
            "message": "refresh_token missing from token.json. Re-authorize Schwab first.",
        }

    auth_raw = f"{client_id}:{client_secret}".encode("utf-8")
    auth_b64 = base64.b64encode(auth_raw).decode("utf-8")

    headers = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    try:
        response = requests.post(
            SCHWAB_TOKEN_URL,
            headers=headers,
            data=data,
            timeout=30,
        )
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Token refresh request failed: {exc}",
        }

    if response.status_code != 200:
        return {
            "status": "error",
            "message": f"Token refresh HTTP {response.status_code}: {response.text[:500]}",
        }

    new_token = response.json()

    # Preserve refresh token if Schwab does not send a new one.
    if not new_token.get("refresh_token") and refresh_token:
        new_token["refresh_token"] = refresh_token

    expires_in = new_token.get("expires_in")
    if expires_in:
        try:
            new_token["expires_at"] = time.time() + float(expires_in)
        except Exception:
            pass

    save_json(TOKEN_PATH, new_token)

    return {
        "status": "success",
        "message": "Schwab token refreshed.",
        "expires_in": expires_in,
    }


def get_access_token() -> str:
    token = load_json(TOKEN_PATH, {})

    if not token_has_access_token(token):
        refresh_result = refresh_schwab_token()
        if refresh_result.get("status") != "success":
            raise RuntimeError(refresh_result.get("message"))
        token = load_json(TOKEN_PATH, {})

    if token_expired_or_close(token):
        refresh_result = refresh_schwab_token()
        if refresh_result.get("status") != "success":
            raise RuntimeError(refresh_result.get("message"))
        token = load_json(TOKEN_PATH, {})

    access_token = token.get("access_token")

    if not access_token:
        raise RuntimeError("No access_token available after refresh attempt.")

    return str(access_token)


def read_symbols(path: Path, limit: int = 0) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"Symbol file not found: {path}")

    raw = path.read_text(encoding="utf-8", errors="ignore")

    symbols: List[str] = []

    for chunk in raw.replace("\n", ",").replace("\r", ",").split(","):
        symbol = chunk.strip().upper()

        if not symbol:
            continue

        # Keep simple stock/ETF symbols. Skip weird blank/header rows.
        if symbol in {"SYMBOL", "TICKER", "TICKERS"}:
            continue

        symbols.append(symbol)

    # De-dupe while preserving order.
    seen = set()
    clean = []

    for symbol in symbols:
        if symbol not in seen:
            clean.append(symbol)
            seen.add(symbol)

    if limit and limit > 0:
        clean = clean[:limit]

    return clean


def candles_to_rows(symbol: str, candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for candle in candles:
        ms = candle.get("datetime")

        try:
            ms_int = int(ms)
            dt_utc = datetime.fromtimestamp(ms_int / 1000, tz=timezone.utc).isoformat()
        except Exception:
            ms_int = 0
            dt_utc = ""

        rows.append({
            "symbol": symbol,
            "datetime_ms": ms_int,
            "datetime_utc": dt_utc,
            "open": candle.get("open"),
            "high": candle.get("high"),
            "low": candle.get("low"),
            "close": candle.get("close"),
            "volume": candle.get("volume"),
        })

    rows.sort(key=lambda r: int(r.get("datetime_ms") or 0))
    return rows


def write_symbol_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "symbol",
        "datetime_ms",
        "datetime_utc",
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


def download_price_history(
    symbol: str,
    period_days: int,
    need_extended_hours: bool,
) -> Tuple[str, Dict[str, Any]]:
    access_token = get_access_token()

    params = {
        "symbol": symbol,
        "periodType": "day",
        "period": str(period_days),
        "frequencyType": "minute",
        "frequency": "5",
        "needExtendedHoursData": "true" if need_extended_hours else "false",
        "needPreviousClose": "false",
    }

    url = SCHWAB_PRICE_HISTORY_URL + "?" + urllib.parse.urlencode(params)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code == 401:
        refresh_result = refresh_schwab_token()
        if refresh_result.get("status") == "success":
            access_token = get_access_token()
            headers["Authorization"] = f"Bearer {access_token}"
            response = requests.get(url, headers=headers, timeout=30)

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


def load_previous_report_statuses(report_path: Path) -> Dict[str, str]:
    """
    Reads the existing download_report.csv so --resume can skip symbols
    that already succeeded or already returned no_data.
    """
    statuses: Dict[str, str] = {}

    if not report_path.exists():
        return statuses

    try:
        with report_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                symbol = str(row.get("symbol") or "").upper().strip()
                status = str(row.get("status") or "").lower().strip()
                if symbol and status:
                    statuses[symbol] = status
    except Exception:
        return statuses

    return statuses

def append_report_row(report_path: Path, row: Dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)

    exists = report_path.exists()

    fieldnames = [
        "time",
        "symbol",
        "status",
        "candles",
        "output_file",
        "message",
    ]

    with report_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not exists:
            writer.writeheader()

        writer.writerow({
            "time": row.get("time"),
            "symbol": row.get("symbol"),
            "status": row.get("status"),
            "candles": row.get("candles"),
            "output_file": row.get("output_file"),
            "message": row.get("message"),
        })


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Russell 2000 5-minute candles from Schwab.")
    parser.add_argument("--symbols", default=str(DEFAULT_SYMBOL_FILE), help="Symbol file path.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output folder.")
    parser.add_argument("--period-days", type=int, default=10, help="Schwab intraday day period to request. 10 is usually the max useful starting point.")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of symbols for testing. 0 means all.")
    parser.add_argument("--delay", type=float, default=0.35, help="Delay between API calls in seconds.")
    parser.add_argument("--extended-hours", action="store_true", help="Include premarket/after-hours candles.")
    parser.add_argument("--resume", action="store_true", help="Skip symbols that already have CSV files.")
    parser.add_argument("--combine", action="store_true", help="Also write one combined CSV. This can get large.")
    args = parser.parse_args()

    load_env_file(ENV_PATH)

    symbol_path = Path(args.symbols)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    report_path = out_dir / "download_report.csv"
    combined_path = out_dir / "russell_2000_5m_combined.csv"

    symbols = read_symbols(symbol_path, limit=args.limit)
    previous_statuses = load_previous_report_statuses(report_path)

    print("Build: ALIENTAI_RUSSELL_2000_5M_SCHWAB_DOWNLOADER_V1")
    print(f"Symbols file: {symbol_path}")
    print(f"Symbols loaded: {len(symbols)}")
    print(f"Output dir: {out_dir}")
    print(f"Period days requested: {args.period_days}")
    print(f"Extended hours: {args.extended_hours}")
    print(f"Resume: {args.resume}")
    print("This does NOT touch the V2 paper account.")
    print("")

    combined_rows_written = 0

    if args.combine and combined_path.exists():
        combined_path.unlink()

    for index, symbol in enumerate(symbols, start=1):
        output_file = out_dir / f"{symbol}_schwab_5m_{args.period_days}d.csv"

        previous_status = previous_statuses.get(symbol, "")

        if args.resume and previous_status in {"success", "no_data"}:
            print(f"[{index}/{len(symbols)}] SKIP previous {previous_status} {symbol}")
            continue

        if args.resume and output_file.exists() and output_file.stat().st_size > 100:
            print(f"[{index}/{len(symbols)}] SKIP existing {symbol}")
            continue

        print(f"[{index}/{len(symbols)}] Downloading {symbol}...")

        try:
            status, result = download_price_history(
                symbol=symbol,
                period_days=args.period_days,
                need_extended_hours=args.extended_hours,
            )
        except Exception as exc:
            message = str(exc)
            print(f"  ERROR {symbol}: {message}")

            append_report_row(report_path, {
                "time": now_iso(),
                "symbol": symbol,
                "status": "error",
                "candles": 0,
                "output_file": "",
                "message": message,
            })

            time.sleep(args.delay)
            continue

        if status != "success":
            message = str(result.get("message", "unknown error"))
            print(f"  ERROR {symbol}: {message}")

            append_report_row(report_path, {
                "time": now_iso(),
                "symbol": symbol,
                "status": "error",
                "candles": 0,
                "output_file": "",
                "message": message,
            })

            time.sleep(args.delay)
            continue

        candles = result.get("candles", [])
        rows = candles_to_rows(symbol, candles)

        if not rows:
            print(f"  NO DATA {symbol}")

            append_report_row(report_path, {
                "time": now_iso(),
                "symbol": symbol,
                "status": "no_data",
                "candles": 0,
                "output_file": "",
                "message": "No candles returned.",
            })

            time.sleep(args.delay)
            continue

        write_symbol_csv(output_file, rows)

        if args.combine:
            combined_exists = combined_path.exists()
            with combined_path.open("a", newline="", encoding="utf-8") as f:
                fieldnames = [
                    "symbol",
                    "datetime_ms",
                    "datetime_utc",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)

                if not combined_exists:
                    writer.writeheader()

                writer.writerows(rows)
                combined_rows_written += len(rows)

        first_time = rows[0].get("datetime_utc")
        last_time = rows[-1].get("datetime_utc")

        print(f"  OK {symbol}: {len(rows)} candles | {first_time} -> {last_time}")

        append_report_row(report_path, {
            "time": now_iso(),
            "symbol": symbol,
            "status": "success",
            "candles": len(rows),
            "output_file": str(output_file),
            "message": f"{first_time} -> {last_time}",
        })

        time.sleep(args.delay)

    summary = {
        "status": "complete",
        "finished_at": now_iso(),
        "symbols_requested": len(symbols),
        "output_dir": str(out_dir),
        "report_path": str(report_path),
        "combined_path": str(combined_path) if args.combine else None,
        "combined_rows_written": combined_rows_written,
        "period_days_requested": args.period_days,
        "extended_hours": args.extended_hours,
    }

    save_json(out_dir / "download_summary.json", summary)

    print("")
    print("DONE")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

