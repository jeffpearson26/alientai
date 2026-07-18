from __future__ import annotations

"""Resumable SEC quarterly Form 4 purchase downloader and normalizer."""

import argparse
import json
import os
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import requests
from dotenv import load_dotenv

from alientai_v2.data.sec_form4 import normalize_quarterly_zip


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data_v2" / "sec_form4_purchases"
SEC_QUARTER_URL = (
    "https://www.sec.gov/files/datastandardsinnovation/data/"
    "insider-transactions-data-sets/{year}q{quarter}_form345.zip"
)


def quarter_url(year: int, quarter: int) -> str:
    if year < 2006 or quarter not in {1, 2, 3, 4}:
        raise ValueError("SEC ownership quarters begin in 2006 and quarter must be 1-4")
    return SEC_QUARTER_URL.format(year=year, quarter=quarter)


def quarter_range(start_year: int, start_quarter: int, end_year: int, end_quarter: int) -> List[Tuple[int, int]]:
    start = start_year * 4 + start_quarter - 1
    end = end_year * 4 + end_quarter - 1
    if end < start:
        raise ValueError("end quarter precedes start quarter")
    return [(value // 4, value % 4 + 1) for value in range(start, end + 1)]


def require_user_agent(env_path: Path) -> str:
    load_dotenv(env_path, override=False)
    value = str(os.getenv("SEC_USER_AGENT") or "").strip()
    if "@" not in value or len(value) < 12:
        raise RuntimeError("SEC_USER_AGENT must identify AlienTAI and contain a monitored email")
    return value


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def download_quarter(
    *, year: int, quarter: int, destination: Path, user_agent: str,
    timeout: float = 90.0, retries: int = 3,
) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and zipfile.is_zipfile(destination):
        return destination
    temporary = destination.with_suffix(destination.suffix + ".part")
    headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate", "Host": "www.sec.gov"}
    error = ""
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(quarter_url(year, quarter), headers=headers, timeout=timeout)
            response.raise_for_status()
            temporary.write_bytes(response.content)
            if not zipfile.is_zipfile(temporary):
                raise RuntimeError("SEC response was not a valid ZIP archive")
            temporary.replace(destination)
            return destination
        except Exception as exc:
            error = str(exc)
            if temporary.exists():
                temporary.unlink()
            if attempt < retries:
                time.sleep(min(2 ** attempt, 8))
    raise RuntimeError(f"failed SEC quarter {year}Q{quarter}: {error}")


def merge_records(existing_path: Path, new_rows: Sequence[Dict[str, Any]]) -> int:
    records: Dict[str, Dict[str, Any]] = {}
    if existing_path.exists():
        for line in existing_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("transaction_id"):
                records[row["transaction_id"]] = row
    for row in new_rows:
        records[row["transaction_id"]] = dict(row)
    existing_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = existing_path.with_suffix(existing_path.suffix + ".tmp")
    ordered = sorted(records.values(), key=lambda row: (row.get("available_at_utc", ""), row.get("ticker", ""), row["transaction_id"]))
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for row in ordered:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    temporary.replace(existing_path)
    return len(ordered)


def run(
    quarters: Iterable[Tuple[int, int]], output_dir: Path, user_agent: str,
    stop_on_error: bool = True, rebuild_completed: bool = False,
) -> Dict[str, Any]:
    cache = output_dir / "cache"
    rows_path = output_dir / "sec_form4_purchases.jsonl"
    state_path = output_dir / "download_state.json"
    state: Dict[str, Any] = {"status": "running", "completed": [], "failed": [], "record_count": 0}
    if state_path.exists():
        try:
            previous = json.loads(state_path.read_text(encoding="utf-8"))
            state["completed"] = list(dict.fromkeys(previous.get("completed", [])))
        except Exception:
            pass
    completed = set(state["completed"])
    for year, quarter in quarters:
        label = f"{year}Q{quarter}"
        if label in completed and not rebuild_completed:
            print(f"SKIP {label}: already completed")
            continue
        try:
            print(f"DOWNLOAD {label}")
            archive = download_quarter(
                year=year, quarter=quarter,
                destination=cache / f"{year}q{quarter}_form345.zip",
                user_agent=user_agent,
            )
            print(f"NORMALIZE {label}")
            rows = normalize_quarterly_zip(archive)
            state["record_count"] = merge_records(rows_path, rows)
            if label not in completed:
                state["completed"].append(label)
            completed.add(label)
            state["last_quarter_rows"] = len(rows)
            state["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
            atomic_json(state_path, state)
            print(f"DONE {label}: {len(rows)} purchases; total={state['record_count']}")
            time.sleep(0.15)
        except Exception as exc:
            state["failed"].append({"quarter": label, "error": str(exc)})
            state["status"] = "failed_closed"
            state["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
            atomic_json(state_path, state)
            if stop_on_error:
                raise
    if not state["failed"]:
        state["status"] = "complete"
    state["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    atomic_json(state_path, state)
    return state


def main() -> None:
    now = datetime.now(timezone.utc)
    current_quarter = (now.month - 1) // 3 + 1
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-year", type=int, default=now.year)
    parser.add_argument("--start-quarter", type=int, default=current_quarter)
    parser.add_argument("--end-year", type=int, default=now.year)
    parser.add_argument("--end-quarter", type=int, default=current_quarter)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--rebuild-completed", action="store_true")
    args = parser.parse_args()
    user_agent = require_user_agent(PROJECT_ROOT / ".env")
    quarters = quarter_range(args.start_year, args.start_quarter, args.end_year, args.end_quarter)
    summary = run(
        quarters, args.output_dir, user_agent,
        stop_on_error=not args.continue_on_error,
        rebuild_completed=args.rebuild_completed,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
