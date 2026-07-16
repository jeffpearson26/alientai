from __future__ import annotations

import argparse
import csv
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


BUILD = "ALIENTAI_V2_RUSSELL2000_DAILY_SCHWAB_MAX_DOWNLOADER_V1"

PROJECT_ROOT = Path(__file__).resolve().parent
TOKEN_PATH = PROJECT_ROOT / "token.json"
OUT_DIR = PROJECT_ROOT / "data_v2" / "daily_schwab_max_history"
SUMMARY_PATH = OUT_DIR / "russell2000_daily_download_summary.json"
SYMBOLS_OUT_PATH = OUT_DIR / "russell2000_symbols_used.txt"

SCHWAB_PRICE_HISTORY_URL = "https://api.schwabapi.com/marketdata/v1/pricehistory"


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


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


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)

    data = json.loads(path.read_text(encoding="utf-8-sig"))

    if not isinstance(data, dict):
        raise RuntimeError(f"{path} did not contain a JSON object.")

    return data


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_access_token() -> str:
    token = load_json(TOKEN_PATH)
    access_token = token.get("access_token")

    if not access_token:
        raise RuntimeError("token.json does not contain access_token. Refresh Schwab token first.")

    return str(access_token)


def schwab_get_json(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    access_token = get_access_token()

    clean_params = {
        k: v for k, v in params.items()
        if v is not None and v != ""
    }

    full_url = url + "?" + urllib.parse.urlencode(clean_params)

    req = urllib.request.Request(
        full_url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)

    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise RuntimeError("Schwab HTTP 401 unauthorized. Refresh Schwab token first.") from exc

        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Schwab HTTP {exc.code}: {body[:1000]}") from exc


def schwab_symbol_variants(symbol: str) -> List[str]:
    """
    Some S&P 500 symbols have class-share punctuation.

    Examples:
      BRK.B
      BF.B

    Different data providers represent these differently.
    This tries a few common variants.
    """
    s = symbol.upper().strip()

    variants = [s]

    if "." in s:
        variants.append(s.replace(".", "/"))
        variants.append(s.replace(".", "-"))
        variants.append(s.replace(".", ""))

    if "-" in s:
        variants.append(s.replace("-", "/"))
        variants.append(s.replace("-", "."))
        variants.append(s.replace("-", ""))

    # Deduplicate while keeping order.
    return list(dict.fromkeys(variants))


def fetch_daily_history(symbol: str, period_years: int = 20) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Fetch daily Schwab candles.

    Schwab commonly supports periodType=year, period=20 for daily history.
    That is usually the max daily range available through this endpoint.
    """
    last_error = None

    for schwab_symbol in schwab_symbol_variants(symbol):
        params = {
            "symbol": schwab_symbol,
            "periodType": "year",
            "period": period_years,
            "frequencyType": "daily",
            "frequency": 1,
            "needPreviousClose": "true",
            "needExtendedHoursData": "false",
        }

        try:
            data = schwab_get_json(SCHWAB_PRICE_HISTORY_URL, params)
            candles = data.get("candles") or []

            if isinstance(candles, list) and candles:
                return schwab_symbol, candles, data

            last_error = f"No candles returned for {schwab_symbol}"

        except Exception as exc:
            last_error = str(exc)

    raise RuntimeError(last_error or f"No candles returned for {symbol}")


def candle_datetime(ms_value: Any) -> str:
    ms = safe_int(ms_value, 0)
    if ms <= 0:
        return ""

    try:
        return datetime.fromtimestamp(ms / 1000.0).replace(microsecond=0).isoformat()
    except Exception:
        return ""


def candle_date(ms_value: Any) -> str:
    dt_text = candle_datetime(ms_value)
    return dt_text[:10] if dt_text else ""


def write_candles_csv(path: Path, requested_symbol: str, schwab_symbol: str, candles: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "symbol",
        "schwab_symbol",
        "date",
        "datetime",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for c in candles:
            writer.writerow({
                "symbol": requested_symbol,
                "schwab_symbol": schwab_symbol,
                "date": candle_date(c.get("datetime")),
                "datetime": candle_datetime(c.get("datetime")),
                "open": c.get("open"),
                "high": c.get("high"),
                "low": c.get("low"),
                "close": c.get("close"),
                "volume": c.get("volume"),
            })


def load_symbols_from_file(path: Path) -> List[str]:
    symbols: List[str] = []

    for line in path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip().upper()

        if not s:
            continue
        if s.startswith("#"):
            continue

        # Allow CSV-ish first column.
        if "," in s:
            s = s.split(",", 1)[0].strip().upper()

        symbols.append(s)

    return list(dict.fromkeys(symbols))


def fetch_sp500_symbols_from_wikipedia() -> List[str]:
    """
    Pull current S&P 500 symbols from Wikipedia using pandas.read_html.

    This requires internet access and pandas/lxml/html5lib support.
    If it fails, use --symbols-file instead.
    """
    try:
        import pandas as pd
    except Exception as exc:
        raise RuntimeError("pandas is required for --use-wikipedia. Use --symbols-file instead.") from exc

    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = pd.read_html(url)

    if not tables:
        raise RuntimeError("No tables found on Wikipedia S&P 500 page.")

    df = tables[0]

    if "Symbol" not in df.columns:
        raise RuntimeError(f"Wikipedia table did not contain Symbol column. Columns={list(df.columns)}")

    symbols = [
        str(x).upper().strip()
        for x in df["Symbol"].tolist()
        if str(x).strip()
    ]

    return list(dict.fromkeys(symbols))


def load_existing_summary() -> Dict[str, Any]:
    if SUMMARY_PATH.exists():
        try:
            return load_json(SUMMARY_PATH)
        except Exception:
            pass

    return {
        "build": BUILD,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "completed": {},
        "failed": {},
        "symbols_total": 0,
        "symbols_done": 0,
        "symbols_failed": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols-file", default="")
    parser.add_argument("--use-wikipedia", action="store_true")
    parser.add_argument("--period-years", type=int, default=20)
    parser.add_argument("--delay", type=float, default=0.35)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-symbols", type=int, default=0)
    parser.add_argument("--start-at", default="")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.use_wikipedia:
        symbols = fetch_sp500_symbols_from_wikipedia()
    elif args.symbols_file:
        symbols = load_symbols_from_file(Path(args.symbols_file))
    else:
        raise SystemExit("Use --use-wikipedia or --symbols-file .\\sp500_symbols.txt")

    if args.start_at:
        start = args.start_at.upper().strip()
        if start in symbols:
            symbols = symbols[symbols.index(start):]
        else:
            print(f"WARNING: --start-at {start} not found in symbols list. Starting from beginning.")

    if args.max_symbols > 0:
        symbols = symbols[: args.max_symbols]

    SYMBOLS_OUT_PATH.write_text("\n".join(symbols) + "\n", encoding="utf-8")

    summary = load_existing_summary()
    summary["build"] = BUILD
    summary["updated_at"] = now_iso()
    summary["symbols_total"] = len(symbols)
    summary["period_years"] = args.period_years
    summary["output_dir"] = str(OUT_DIR)
    summary["symbols_file_used"] = str(SYMBOLS_OUT_PATH)

    completed = summary.setdefault("completed", {})
    failed = summary.setdefault("failed", {})

    print(f"Build: {BUILD}")
    print(f"Output dir: {OUT_DIR}")
    print(f"Symbols: {len(symbols)}")
    print(f"Period years requested: {args.period_years}")
    print(f"Resume: {args.resume}")
    print("This downloads paper/research data only. It does not trade.")
    print("")

    for idx, symbol in enumerate(symbols, start=1):
        out_path = OUT_DIR / f"{symbol.replace('/', '-').replace('.', '-')}_schwab_1d_max.csv"

        if args.resume and not args.force and symbol in completed and out_path.exists():
            print(f"[{idx}/{len(symbols)}] SKIP {symbol}: already completed")
            continue

        print(f"[{idx}/{len(symbols)}] Downloading {symbol}...")

        try:
            schwab_symbol, candles, raw = fetch_daily_history(symbol, period_years=args.period_years)

            write_candles_csv(
                path=out_path,
                requested_symbol=symbol,
                schwab_symbol=schwab_symbol,
                candles=candles,
            )

            first_date = candle_date(candles[0].get("datetime")) if candles else ""
            last_date = candle_date(candles[-1].get("datetime")) if candles else ""

            completed[symbol] = {
                "status": "success",
                "requested_symbol": symbol,
                "schwab_symbol": schwab_symbol,
                "candles": len(candles),
                "first_date": first_date,
                "last_date": last_date,
                "csv_path": str(out_path),
                "updated_at": now_iso(),
            }

            if symbol in failed:
                failed.pop(symbol, None)

            print(f"  success candles={len(candles)} first={first_date} last={last_date} schwab_symbol={schwab_symbol}")

        except Exception as exc:
            failed[symbol] = {
                "status": "error",
                "error": str(exc),
                "updated_at": now_iso(),
            }
            print(f"  ERROR {symbol}: {exc}")

            if "401 unauthorized" in str(exc).lower():
                print("")
                print("Schwab token expired. Run:")
                print("python .\\refresh_schwab_token_standalone.py")
                print("Then resume:")
                print("python .\\download_sp500_daily_schwab_max.py --use-wikipedia --resume")
                save_json(SUMMARY_PATH, summary)
                raise SystemExit(1)

        summary["updated_at"] = now_iso()
        summary["symbols_done"] = len(completed)
        summary["symbols_failed"] = len(failed)
        save_json(SUMMARY_PATH, summary)

        if args.delay > 0:
            time.sleep(args.delay)

    summary["updated_at"] = now_iso()
    summary["symbols_done"] = len(completed)
    summary["symbols_failed"] = len(failed)
    summary["status"] = "complete"
    save_json(SUMMARY_PATH, summary)

    print("")
    print("DONE")
    print(json.dumps({
        "status": "complete",
        "build": BUILD,
        "symbols_requested": len(symbols),
        "symbols_done": len(completed),
        "symbols_failed": len(failed),
        "summary_path": str(SUMMARY_PATH),
        "symbols_used_path": str(SYMBOLS_OUT_PATH),
        "output_dir": str(OUT_DIR),
    }, indent=2))


if __name__ == "__main__":
    main()
