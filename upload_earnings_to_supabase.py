from __future__ import annotations

"""Idempotent uploader for normalized quarterly earnings events."""

import argparse
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Sequence

from dotenv import load_dotenv
from supabase import Client, create_client


ROOT = Path(__file__).resolve().parent
DEFAULT_ROWS = ROOT / "data_v2" / "earnings_history" / "earnings_events.jsonl"
DEFAULT_STATE = ROOT / "data_v2" / "earnings_history" / "upload_state.json"
DEFAULT_TABLE = "v2_earnings_events"
SERVER_GENERATED_FIELDS = {"imported_at_utc"}


def load_rows(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sanitize_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    cleaned = {key: value for key, value in row.items() if key not in SERVER_GENERATED_FIELDS}
    required = ("event_id", "ticker", "fiscal_date_ending", "reported_date", "available_at_utc", "source_url")
    missing = [key for key in required if cleaned.get(key) in (None, "")]
    if missing:
        raise ValueError(f"row missing required fields: {', '.join(missing)}")
    flags = list(cleaned.get("quality_flags") or [])
    try:
        fiscal = date.fromisoformat(str(cleaned["fiscal_date_ending"]))
        reported = date.fromisoformat(str(cleaned["reported_date"]))
        available = datetime.fromisoformat(str(cleaned["available_at_utc"]).replace("Z", "+00:00"))
    except ValueError:
        flags.append("INVALID_DATE")
    else:
        if fiscal > reported:
            flags.append("FISCAL_DATE_AFTER_REPORTED_DATE")
        if available.date() < reported:
            flags.append("AVAILABLE_BEFORE_REPORTED_DATE")
    cleaned["quality_flags"] = sorted(set(flags))
    cleaned["is_training_eligible"] = bool(cleaned.get("is_training_eligible", True)) and not flags
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


def upload(
    client: Any, rows: Sequence[Dict[str, Any]], batch_size: int,
    state_path: Path | None = None, dry_run: bool = False,
) -> Dict[str, Any]:
    cleaned = [sanitize_row(row) for row in rows]
    state: Dict[str, Any] = {
        "status": "dry_run" if dry_run else "running", "table": DEFAULT_TABLE,
        "input_rows": len(cleaned), "uploaded_rows": 0, "completed_batches": 0,
    }
    if not dry_run:
        for batch in batches(cleaned, batch_size):
            client.table(DEFAULT_TABLE).upsert(batch, on_conflict="event_id").execute()
            state["uploaded_rows"] += len(batch)
            state["completed_batches"] += 1
            state["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
            if state_path:
                atomic_json(state_path, state)
        state["status"] = "complete"
    state["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    if state_path:
        atomic_json(state_path, state)
    return state


def client_from_env() -> Client:
    load_dotenv(ROOT / ".env", override=False)
    url = str(os.getenv("SUPABASE_URL") or "").strip()
    key = str(os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
    return create_client(url, key)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=Path, default=DEFAULT_ROWS)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--batch-size", type=int, default=250)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    rows = load_rows(args.rows)
    result = upload(
        None if args.dry_run else client_from_env(), rows, args.batch_size,
        state_path=args.state, dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
