from __future__ import annotations

import argparse
import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests


BUILD = "ALIENTAI_V2_DAILY_SUPABASE_UPLOADER_V1"

PROJECT_ROOT = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / ".env"

DEFAULT_INPUT_DIR = PROJECT_ROOT / "data_v2" / "daily_schwab_max_history"
DEFAULT_TABLE = "v2_daily_candles"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "data_v2" / "daily_supabase_upload_report.csv"
DEFAULT_STATE_PATH = PROJECT_ROOT / "data_v2" / "daily_supabase_upload_state.json"


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


def env_value(*names: str) -> str:
    for name in names:
        value = os.environ.get(name)

        if value:
            return value

    return ""


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


def datetime_ms_from_row(raw: Dict[str, Any]) -> Tuple[int, str]:
    """
    Accept both uploader-native rows with datetime_ms/datetime_utc
    and Schwab daily CSV rows with date/datetime columns.

    S&P downloader CSV format:
      symbol,schwab_symbol,date,datetime,open,high,low,close,volume
    """
    existing_ms = safe_int(raw.get("datetime_ms"), 0)
    existing_utc = str(raw.get("datetime_utc") or "").strip()

    if existing_ms > 0:
        return existing_ms, existing_utc

    dt_text = str(
        raw.get("datetime")
        or raw.get("datetime_utc")
        or raw.get("date")
        or raw.get("timestamp")
        or ""
    ).strip()

    if not dt_text:
        return 0, ""

    try:
        # Handle Schwab-style ISO without timezone:
        # 2006-07-09T22:00:00
        clean = dt_text.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)

        # If timezone missing, treat it as UTC for research consistency.
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        dt_utc = dt.astimezone(timezone.utc)
        ms = int(dt_utc.timestamp() * 1000)
        return ms, dt_utc.isoformat()

    except Exception:
        # Last fallback: date only, e.g. 2006-07-09
        try:
            date_text = str(raw.get("date") or "").strip()
            if not date_text:
                return 0, ""

            dt = datetime.fromisoformat(date_text).replace(tzinfo=timezone.utc)
            ms = int(dt.timestamp() * 1000)
            return ms, dt.isoformat()
        except Exception:
            return 0, ""


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default

    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def supabase_headers(service_key: str) -> Dict[str, str]:
    return {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }


def supabase_upsert_batch(
    *,
    supabase_url: str,
    service_key: str,
    table: str,
    rows: List[Dict[str, Any]],
    timeout: int = 90,
) -> requests.Response:
    url = supabase_url.rstrip("/") + f"/rest/v1/{table}"

    # on_conflict tells Supabase which primary-key fields define duplicates.
    params = {
        "on_conflict": "symbol,timeframe,datetime_ms",
    }

    return requests.post(
        url,
        headers=supabase_headers(service_key),
        params=params,
        json=rows,
        timeout=timeout,
    )


def parse_daily_csv(path: Path) -> Tuple[str, List[Dict[str, Any]]]:
    rows: List[Dict[str, Any]] = []

    symbol_from_name = path.name.replace("_schwab_1d_max.csv", "").upper().strip()

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for raw in reader:
            symbol = str(raw.get("symbol") or symbol_from_name).upper().strip()
            datetime_ms, datetime_utc = datetime_ms_from_row(raw)

            if not symbol or datetime_ms <= 0:
                continue

            row = {
                "symbol": symbol,
                "timeframe": "1d",
                "datetime_ms": datetime_ms,
                "datetime_utc": datetime_utc,
                "date": str(raw.get("date") or str(datetime_utc)[:10]),
                "open": safe_float(raw.get("open"), 0.0),
                "high": safe_float(raw.get("high"), 0.0),
                "low": safe_float(raw.get("low"), 0.0),
                "close": safe_float(raw.get("close"), 0.0),
                "volume": safe_int(raw.get("volume"), 0),
                "source": "schwab",
            }

            rows.append(row)

    rows.sort(key=lambda r: int(r.get("datetime_ms") or 0))

    return symbol_from_name, rows


def chunks(values: List[Dict[str, Any]], size: int):
    for start in range(0, len(values), size):
        yield values[start:start + size]


def append_report(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "time",
        "file",
        "symbol",
        "status",
        "rows_read",
        "rows_uploaded",
        "message",
    ]

    exists = path.exists()

    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not exists:
            writer.writeheader()

        writer.writerow({
            "time": row.get("time", ""),
            "file": row.get("file", ""),
            "symbol": row.get("symbol", ""),
            "status": row.get("status", ""),
            "rows_read": row.get("rows_read", 0),
            "rows_uploaded": row.get("rows_uploaded", 0),
            "message": row.get("message", ""),
        })


def upload_file(
    *,
    file_path: Path,
    supabase_url: str,
    service_key: str,
    table: str,
    batch_size: int,
    delay: float,
    max_retries: int,
    retry_sleep: float,
) -> Dict[str, Any]:
    symbol, rows = parse_daily_csv(file_path)

    if not rows:
        return {
            "time": now_iso(),
            "file": str(file_path),
            "symbol": symbol,
            "status": "no_rows",
            "rows_read": 0,
            "rows_uploaded": 0,
            "message": "No valid rows found.",
        }

    uploaded = 0

    for batch_index, batch in enumerate(chunks(rows, batch_size), start=1):
        attempt = 0

        while True:
            attempt += 1

            try:
                response = supabase_upsert_batch(
                    supabase_url=supabase_url,
                    service_key=service_key,
                    table=table,
                    rows=batch,
                )

                if response.status_code in {200, 201, 204}:
                    uploaded += len(batch)
                    break

                message = response.text[:1000]

                if attempt > max_retries:
                    return {
                        "time": now_iso(),
                        "file": str(file_path),
                        "symbol": symbol,
                        "status": "error",
                        "rows_read": len(rows),
                        "rows_uploaded": uploaded,
                        "message": f"HTTP {response.status_code} after {attempt} attempts: {message}",
                    }

                print(
                    f"    retry {attempt}/{max_retries} batch {batch_index}: "
                    f"HTTP {response.status_code} {message[:200]}"
                )
                time.sleep(retry_sleep)

            except Exception as exc:
                if attempt > max_retries:
                    return {
                        "time": now_iso(),
                        "file": str(file_path),
                        "symbol": symbol,
                        "status": "error",
                        "rows_read": len(rows),
                        "rows_uploaded": uploaded,
                        "message": f"Exception after {attempt} attempts: {exc}",
                    }

                print(f"    retry {attempt}/{max_retries} batch {batch_index}: {exc}")
                time.sleep(retry_sleep)

        if delay > 0:
            time.sleep(delay)

    return {
        "time": now_iso(),
        "file": str(file_path),
        "symbol": symbol,
        "status": "success",
        "rows_read": len(rows),
        "rows_uploaded": uploaded,
        "message": "OK",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload V2 daily Schwab candles to Supabase.")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--table", default=DEFAULT_TABLE)
    parser.add_argument("--only-symbol", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--delay", type=float, default=0.15)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--retry-sleep", type=float, default=2.0)
    args = parser.parse_args()

    load_env_file(ENV_PATH)

    supabase_url = env_value("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")
    service_key = env_value("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY")

    if not supabase_url:
        raise RuntimeError("SUPABASE_URL missing from .env.")

    if not service_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY missing from .env.")

    input_dir = Path(args.input_dir)
    report_path = DEFAULT_REPORT_PATH
    state_path = DEFAULT_STATE_PATH

    if not input_dir.exists():
        raise FileNotFoundError(f"Input dir not found: {input_dir}")

    files = sorted(input_dir.glob("*_schwab_1d_max.csv"))

    if args.only_symbol:
        symbol = args.only_symbol.upper().strip()
        files = [f for f in files if f.name.upper() == f"{symbol}_SCHWAB_1D_MAX.CSV"]

    if args.limit and args.limit > 0:
        files = files[:args.limit]

    state = read_json(state_path, default={})
    uploaded_files = set(state.get("uploaded_files", [])) if isinstance(state, dict) else set()

    print(f"Build: {BUILD}")
    print(f"Input dir: {input_dir}")
    print(f"Files found: {len(files)}")
    print(f"Table: {args.table}")
    print(f"Batch size: {args.batch_size}")
    print(f"Delay: {args.delay}")
    print(f"Resume: {args.resume}")
    print(f"Max retries: {args.max_retries}")
    print("This does NOT touch the V2 paper account.")
    print("")

    files_processed = 0
    successes = 0
    errors = 0
    skipped = 0
    total_rows_read = 0
    total_rows_uploaded = 0

    for index, file_path in enumerate(files, start=1):
        state_key = str(file_path.resolve())

        if args.resume and state_key in uploaded_files:
            print(f"[{index}/{len(files)}] SKIP already uploaded {file_path.name}")
            skipped += 1
            continue

        print(f"[{index}/{len(files)}] Uploading {file_path.name}...")

        result = upload_file(
            file_path=file_path,
            supabase_url=supabase_url,
            service_key=service_key,
            table=args.table,
            batch_size=args.batch_size,
            delay=args.delay,
            max_retries=args.max_retries,
            retry_sleep=args.retry_sleep,
        )

        append_report(report_path, result)

        files_processed += 1
        total_rows_read += safe_int(result.get("rows_read"), 0)
        total_rows_uploaded += safe_int(result.get("rows_uploaded"), 0)

        if result.get("status") == "success":
            successes += 1
            uploaded_files.add(state_key)

            state = {
                "updated_at": now_iso(),
                "table": args.table,
                "uploaded_files": sorted(uploaded_files),
            }
            write_json(state_path, state)

            print(f"  OK {result.get('symbol')}: {result.get('rows_uploaded')} rows")

        else:
            errors += 1
            print(f"  {result.get('status')} {result.get('symbol')}: {result.get('message')}")

    final_summary = {
        "status": "complete",
        "finished_at": now_iso(),
        "build": BUILD,
        "input_dir": str(input_dir),
        "table": args.table,
        "files_seen": len(files),
        "files_processed_this_run": files_processed,
        "files_skipped_this_run": skipped,
        "successes_this_run": successes,
        "errors_this_run": errors,
        "total_rows_read_this_run": total_rows_read,
        "total_rows_uploaded_this_run": total_rows_uploaded,
        "report_path": str(report_path),
        "state_path": str(state_path),
    }

    summary_path = PROJECT_ROOT / "data_v2" / "daily_supabase_upload_summary.json"
    write_json(summary_path, final_summary)

    print("")
    print("DONE")
    print(json.dumps(final_summary, indent=2))


if __name__ == "__main__":
    main()
