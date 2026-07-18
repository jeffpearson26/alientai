from __future__ import annotations

"""Idempotent, batched uploader for normalized SEC Form 4 purchases."""

import argparse
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Sequence

from dotenv import load_dotenv
from supabase import Client, create_client


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_ROWS = PROJECT_ROOT / "data_v2" / "sec_form4_purchases" / "sec_form4_purchases.jsonl"
DEFAULT_STATE = PROJECT_ROOT / "data_v2" / "sec_form4_purchases" / "upload_state.json"
DEFAULT_TABLE = "v2_sec_form4_purchases"
SERVER_GENERATED_FIELDS = {"total_value", "imported_at_utc"}


def load_rows(path: Path, limit: int = 0) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rows.append(json.loads(line))
            if limit and len(rows) >= limit:
                break
    return rows


def sanitize_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    cleaned = {key: value for key, value in row.items() if key not in SERVER_GENERATED_FIELDS}
    if cleaned.get("transaction_code") != "P":
        raise ValueError("uploader accepts only transaction code P")
    required = (
        "transaction_id", "ticker", "cik", "accession_number", "filing_timestamp_utc",
        "available_at_utc", "transaction_date", "shares", "price", "source_url",
    )
    missing = [key for key in required if cleaned.get(key) in (None, "")]
    if missing:
        raise ValueError(f"row missing required fields: {', '.join(missing)}")
    flags: List[str] = []
    try:
        transaction_date = date.fromisoformat(str(cleaned["transaction_date"]))
        availability_date = datetime.fromisoformat(
            str(cleaned["available_at_utc"]).replace("Z", "+00:00")
        ).date()
    except ValueError:
        flags.append("INVALID_DATE")
    else:
        if transaction_date < date(2000, 1, 1):
            flags.append("TRANSACTION_DATE_BEFORE_2000")
        if transaction_date > availability_date:
            flags.append("TRANSACTION_DATE_AFTER_AVAILABILITY")
    cleaned["quality_flags"] = flags
    cleaned["is_training_eligible"] = not flags
    return cleaned


def batches(rows: Sequence[Dict[str, Any]], size: int) -> Iterator[List[Dict[str, Any]]]:
    if size <= 0:
        raise ValueError("batch size must be positive")
    for start in range(0, len(rows), size):
        yield list(rows[start:start + size])


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def supabase_client(env_path: Path) -> Client:
    load_dotenv(env_path, override=False)
    url = str(os.getenv("SUPABASE_URL") or "").strip()
    key = str(os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
    return create_client(url, key)


def upload(
    *, client: Any, table: str, rows: Sequence[Dict[str, Any]], batch_size: int,
    state_path: Path | None = None, dry_run: bool = False,
) -> Dict[str, Any]:
    cleaned = [sanitize_row(row) for row in rows]
    state: Dict[str, Any] = {
        "status": "dry_run" if dry_run else "running", "table": table,
        "input_rows": len(cleaned), "uploaded_rows": 0, "completed_batches": 0,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    if dry_run:
        if state_path:
            atomic_json(state_path, state)
        return state
    try:
        for batch in batches(cleaned, batch_size):
            client.table(table).upsert(batch, on_conflict="transaction_id").execute()
            state["uploaded_rows"] += len(batch)
            state["completed_batches"] += 1
            state["last_transaction_id"] = batch[-1]["transaction_id"]
            state["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
            if state_path:
                atomic_json(state_path, state)
    except Exception as exc:
        state["status"] = "failed_closed"
        state["error"] = str(exc)
        state["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        if state_path:
            atomic_json(state_path, state)
        raise
    state["status"] = "complete"
    state["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    if state_path:
        atomic_json(state_path, state)
    return state


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=Path, default=DEFAULT_ROWS)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--table", default=DEFAULT_TABLE)
    parser.add_argument("--batch-size", type=int, default=250)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    rows = load_rows(args.rows, args.limit)
    client = None if args.dry_run else supabase_client(PROJECT_ROOT / ".env")
    result = upload(
        client=client, table=args.table, rows=rows, batch_size=args.batch_size,
        state_path=args.state, dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
