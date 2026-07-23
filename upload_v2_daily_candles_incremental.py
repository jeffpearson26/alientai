from __future__ import annotations

"""Dry-run-first uploader for daily candles newer than Supabase's current latest row."""

import argparse
import json
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

import requests

from upload_v2_daily_candles_to_supabase import (
    ENV_PATH,
    env_value,
    load_env_file,
    parse_daily_csv,
    supabase_headers,
    supabase_upsert_batch,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_SP500_INPUT_DIR = ROOT / "data_v2" / "sp500_daily_schwab_max_history"


def rows_newer_than(rows: Iterable[Mapping[str, Any]], latest_ms: int | None) -> list[dict[str, Any]]:
    boundary = int(latest_ms or 0)
    return [dict(row) for row in rows if int(row.get("datetime_ms") or 0) > boundary]


def remote_symbol(rows: Iterable[Mapping[str, Any]], fallback: str) -> str:
    """Use the CSV's original symbol, not its filename-safe dash variant."""
    for row in rows:
        value = str(row.get("symbol") or "").strip().upper()
        if value:
            return value
    return fallback.strip().upper()


def fetch_latest_ms(supabase_url: str, service_key: str, table: str, symbol: str) -> int | None:
    response = requests.get(
        supabase_url.rstrip("/") + f"/rest/v1/{table}",
        headers=supabase_headers(service_key),
        params={
            "select": "datetime_ms", "symbol": f"eq.{symbol}",
            "order": "datetime_ms.desc", "limit": "1",
        },
        timeout=60,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Supabase latest-row check failed for {symbol}: HTTP {response.status_code}")
    payload = response.json()
    if not isinstance(payload, list) or not payload:
        return None
    value = payload[0].get("datetime_ms")
    return int(value) if value is not None else None


def chunks(rows: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
    for start in range(0, len(rows), size):
        yield rows[start:start + size]


def main() -> None:
    parser = argparse.ArgumentParser(description="Incremental daily-candle upload; defaults to dry-run.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_SP500_INPUT_DIR)
    parser.add_argument("--table", default="v2_daily_candles")
    parser.add_argument("--only-symbol", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=250)
    parser.add_argument("--delay-seconds", type=float, default=0.05)
    parser.add_argument("--apply", action="store_true", help="Actually upsert rows; otherwise only report candidates.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.batch_size <= 0 or args.delay_seconds < 0:
        raise ValueError("batch-size must be positive and delay-seconds cannot be negative")

    load_env_file(ENV_PATH)
    url = env_value("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")
    key = env_value("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("Supabase URL or service key is missing.")
    files = sorted(args.input_dir.glob("*_schwab_1d_max.csv"))
    if args.only_symbol:
        files = [path for path in files if path.name.upper() == f"{args.only_symbol.upper()}_SCHWAB_1D_MAX.CSV"]
    if args.limit:
        files = files[:args.limit]

    results = []
    for index, path in enumerate(files, 1):
        filename_symbol, rows = parse_daily_csv(path)
        symbol = remote_symbol(rows, filename_symbol)
        latest = fetch_latest_ms(url, key, args.table, symbol)
        new_rows = rows_newer_than(rows, latest)
        uploaded = 0
        if args.apply:
            for batch in chunks(new_rows, args.batch_size):
                response = supabase_upsert_batch(supabase_url=url, service_key=key, table=args.table, rows=batch)
                if response.status_code not in {200, 201, 204}:
                    raise RuntimeError(f"Supabase incremental upload failed for {symbol}: HTTP {response.status_code}")
                uploaded += len(batch)
                if args.delay_seconds:
                    time.sleep(args.delay_seconds)
        results.append({"symbol": symbol, "existing_latest_ms": latest, "candidate_rows": len(new_rows), "uploaded_rows": uploaded})
        print(f"[{index}/{len(files)}] {symbol}: candidates={len(new_rows)} uploaded={uploaded}")

    report = {
        "status": "complete", "research_only": True, "apply": bool(args.apply), "table": args.table,
        "files_seen": len(files), "candidate_rows": sum(row["candidate_rows"] for row in results),
        "uploaded_rows": sum(row["uploaded_rows"] for row in results), "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "apply", "files_seen", "candidate_rows", "uploaded_rows")}, indent=2))


if __name__ == "__main__":
    main()
