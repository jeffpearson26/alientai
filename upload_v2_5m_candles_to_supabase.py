from __future__ import annotations

import argparse
import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


PROJECT_ROOT = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / ".env"

DEFAULT_INPUT_DIR = PROJECT_ROOT / "data_v2" / "russell_2000_5m_schwab_max"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "data_v2" / "supabase_5m_upload_report.csv"

DEFAULT_TABLE = "v2_5min_candles"


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


def env_value(*names: str) -> Optional[str]:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def safe_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except Exception:
        return None


def read_candle_csv(path: Path, limit_rows: int = 0) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for raw in reader:
            symbol = str(raw.get("symbol") or "").upper().strip()
            datetime_ms = safe_int(raw.get("datetime_ms"))
            datetime_utc = str(raw.get("datetime_utc") or "").strip()

            if not symbol or not datetime_ms or not datetime_utc:
                continue

            rows.append({
                "symbol": symbol,
                "datetime_ms": datetime_ms,
                "datetime_utc": datetime_utc,
                "open": safe_float(raw.get("open")),
                "high": safe_float(raw.get("high")),
                "low": safe_float(raw.get("low")),
                "close": safe_float(raw.get("close")),
                "volume": safe_int(raw.get("volume")),
                "source": "schwab",
                "timeframe": "5m",
                "extended_hours": True,
            })

            if limit_rows and len(rows) >= limit_rows:
                break

    return rows


def chunked(rows: List[Dict[str, Any]], size: int):
    for i in range(0, len(rows), size):
        yield rows[i:i + size]


def load_successful_uploaded_files(report_path: Path) -> set[str]:
    """
    Reads previous upload report and returns file paths that already uploaded successfully.
    This lets us resume without re-uploading every completed file.
    """
    successful: set[str] = set()

    if not report_path.exists():
        return successful

    try:
        with report_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                status = str(row.get("status") or "").lower().strip()
                file_path = str(row.get("file") or "").strip()

                if status == "success" and file_path:
                    successful.add(file_path)
    except Exception:
        return successful

    return successful


def append_report_row(report_path: Path, row: Dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "time",
        "file",
        "symbol",
        "status",
        "rows_read",
        "rows_uploaded",
        "batches",
        "message",
    ]

    exists = report_path.exists()

    with report_path.open("a", newline="", encoding="utf-8") as f:
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
            "batches": row.get("batches", 0),
            "message": row.get("message", ""),
        })


def supabase_upsert_batch(
    *,
    supabase_url: str,
    supabase_key: str,
    table: str,
    rows: List[Dict[str, Any]],
    timeout: int = 90,
) -> requests.Response:
    url = supabase_url.rstrip("/") + f"/rest/v1/{table}"

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
        "Connection": "close",
    }

    params = {
        "on_conflict": "symbol,datetime_ms,source,timeframe",
    }

    return requests.post(
        url,
        headers=headers,
        params=params,
        data=json.dumps(rows),
        timeout=timeout,
    )


def upsert_batch_with_retries(
    *,
    supabase_url: str,
    supabase_key: str,
    table: str,
    batch: List[Dict[str, Any]],
    max_retries: int,
    retry_sleep: float,
) -> tuple[bool, str]:
    """
    Returns:
        (success, message)
    """
    last_message = ""

    for attempt in range(1, max_retries + 1):
        try:
            response = supabase_upsert_batch(
                supabase_url=supabase_url,
                supabase_key=supabase_key,
                table=table,
                rows=batch,
            )

            if response.status_code in {200, 201, 204}:
                return True, "OK"

            last_message = f"Supabase HTTP {response.status_code}: {response.text[:500]}"

        except requests.exceptions.RequestException as exc:
            last_message = f"Request error attempt {attempt}/{max_retries}: {exc}"

        print(f"    retry needed: {last_message}")
        time.sleep(retry_sleep * attempt)

    return False, last_message


def upload_file(
    *,
    path: Path,
    supabase_url: str,
    supabase_key: str,
    table: str,
    batch_size: int,
    delay: float,
    limit_rows: int,
    report_path: Path,
    max_retries: int,
    retry_sleep: float,
) -> Dict[str, Any]:
    rows = read_candle_csv(path, limit_rows=limit_rows)

    symbol = ""
    if rows:
        symbol = str(rows[0].get("symbol") or "")

    if not rows:
        result = {
            "time": now_iso(),
            "file": str(path),
            "symbol": symbol,
            "status": "no_rows",
            "rows_read": 0,
            "rows_uploaded": 0,
            "batches": 0,
            "message": "No valid rows found.",
        }
        append_report_row(report_path, result)
        return result

    uploaded = 0
    batches = 0

    for batch in chunked(rows, batch_size):
        batches += 1

        ok, message = upsert_batch_with_retries(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            table=table,
            batch=batch,
            max_retries=max_retries,
            retry_sleep=retry_sleep,
        )

        if not ok:
            result = {
                "time": now_iso(),
                "file": str(path),
                "symbol": symbol,
                "status": "error",
                "rows_read": len(rows),
                "rows_uploaded": uploaded,
                "batches": batches,
                "message": message,
            }
            append_report_row(report_path, result)
            return result

        uploaded += len(batch)

        if delay > 0:
            time.sleep(delay)

    result = {
        "time": now_iso(),
        "file": str(path),
        "symbol": symbol,
        "status": "success",
        "rows_read": len(rows),
        "rows_uploaded": uploaded,
        "batches": batches,
        "message": "Uploaded with Supabase upsert.",
    }

    append_report_row(report_path, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload V2 Schwab 5-minute candles to Supabase.")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--table", default=DEFAULT_TABLE)
    parser.add_argument("--limit-files", type=int, default=0)
    parser.add_argument("--limit-rows-per-file", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--delay", type=float, default=0.35)
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--only-symbol", default="")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-retries", type=int, default=6)
    parser.add_argument("--retry-sleep", type=float, default=3.0)
    args = parser.parse_args()

    load_env_file(ENV_PATH)

    supabase_url = env_value("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")
    supabase_key = env_value("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY")

    if not supabase_url:
        raise RuntimeError("SUPABASE_URL missing from .env.")

    if not supabase_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY missing from .env.")

    input_dir = Path(args.input_dir)
    report_path = Path(args.report)

    files = sorted(input_dir.glob("*_schwab_5m_max.csv"))

    if args.only_symbol:
        want = args.only_symbol.upper().strip()
        files = [p for p in files if p.name.upper().startswith(want + "_")]

    if args.limit_files and args.limit_files > 0:
        files = files[:args.limit_files]

    successful_files = load_successful_uploaded_files(report_path) if args.resume else set()

    print("Build: ALIENTAI_V2_5M_SUPABASE_UPLOADER_V2_RETRY_RESUME")
    print(f"Input dir: {input_dir}")
    print(f"Files found: {len(files)}")
    print(f"Table: {args.table}")
    print(f"Batch size: {args.batch_size}")
    print(f"Delay: {args.delay}")
    print(f"Resume: {args.resume}")
    print(f"Max retries: {args.max_retries}")
    print("This does NOT touch the V2 paper account.")
    print("")

    total_uploaded = 0
    total_rows = 0
    successes = 0
    errors = 0
    skipped = 0

    for index, file_path in enumerate(files, start=1):
        if args.resume and str(file_path) in successful_files:
            skipped += 1
            print(f"[{index}/{len(files)}] SKIP already uploaded {file_path.name}")
            continue

        print(f"[{index}/{len(files)}] Uploading {file_path.name}...")

        result = upload_file(
            path=file_path,
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            table=args.table,
            batch_size=args.batch_size,
            delay=args.delay,
            limit_rows=args.limit_rows_per_file,
            report_path=report_path,
            max_retries=args.max_retries,
            retry_sleep=args.retry_sleep,
        )

        total_rows += int(result.get("rows_read") or 0)
        total_uploaded += int(result.get("rows_uploaded") or 0)

        if result.get("status") == "success":
            successes += 1
            print(f"  OK {result.get('symbol')}: {result.get('rows_uploaded')} rows")
        else:
            errors += 1
            print(f"  {str(result.get('status')).upper()} {result.get('symbol')}: {result.get('message')}")

    summary = {
        "status": "complete",
        "finished_at": now_iso(),
        "files_seen": len(files),
        "files_skipped": skipped,
        "successes": successes,
        "errors": errors,
        "total_rows_read_this_run": total_rows,
        "total_rows_uploaded_this_run": total_uploaded,
        "report_path": str(report_path),
        "table": args.table,
    }

    summary_path = report_path.parent / "supabase_5m_upload_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("")
    print("DONE")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
