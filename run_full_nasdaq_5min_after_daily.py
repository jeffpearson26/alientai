from __future__ import annotations

"""Wait for the daily Nasdaq archive, audit it, then build/audit five-minute data."""

import argparse
import json
import msvcrt
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import IO, Any

import psutil


ROOT = Path(__file__).resolve().parent


def acquire_lock(path: Path) -> IO[str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+", encoding="utf-8")
    handle.seek(0)
    if not handle.read(1):
        handle.seek(0)
        handle.write("0")
        handle.flush()
    handle.seek(0)
    try:
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError as exc:
        handle.close()
        raise RuntimeError(f"another queue runner holds {path}") from exc
    handle.seek(0)
    handle.truncate()
    handle.write(str(os.getpid()))
    handle.flush()
    return handle


def release_lock(handle: IO[str]) -> None:
    try:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    finally:
        handle.close()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def active_alpha_collectors() -> list[dict[str, Any]]:
    active: list[dict[str, Any]] = []
    own_pid = os.getpid()
    for process in psutil.process_iter(["pid", "cmdline"]):
        try:
            if process.info["pid"] == own_pid:
                continue
            command = " ".join(process.info.get("cmdline") or [])
            lowered = command.casefold()
            if (
                "download_alpha_vantage" in lowered
                and "run_full_nasdaq_5min_after_daily.py" not in lowered
            ):
                active.append(
                    {
                        "pid": process.info["pid"],
                        "command": command[:240],
                    }
                )
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    return active


def run_checked(arguments: list[str], *, cwd: Path) -> None:
    print(f"RUN {' '.join(arguments)}", flush=True)
    completed = subprocess.run(arguments, cwd=cwd, check=False)
    if completed.returncode:
        raise RuntimeError(
            f"command failed with exit code {completed.returncode}: "
            f"{' '.join(arguments)}"
        )


def wait_for_daily(
    daily_archive: Path,
    *,
    poll_seconds: float,
) -> dict[str, Any]:
    manifest_path = daily_archive / "manifest.json"
    last_reported = ""
    while True:
        manifest = read_json(manifest_path)
        status = str(manifest.get("status") or "")
        completed = len(manifest.get("completed") or {})
        unavailable = len(manifest.get("unavailable") or {})
        failed = len(manifest.get("failed") or {})
        marker = f"{status}|{completed}|{unavailable}|{failed}"
        if marker != last_reported:
            print(
                f"DAILY {status}: completed={completed}, "
                f"unavailable={unavailable}, failed={failed}",
                flush=True,
            )
            last_reported = marker
        if status == "complete":
            while active_alpha_collectors():
                time.sleep(poll_seconds)
            return manifest
        if status == "failed_closed" or failed:
            raise RuntimeError(
                f"daily archive failed closed with {failed} failed symbols"
            )
        time.sleep(poll_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--daily-archive", type=Path, required=True)
    parser.add_argument("--listing-status", type=Path, required=True)
    parser.add_argument("--intraday-output", type=Path, required=True)
    parser.add_argument("--seed-archive", type=Path, required=True)
    parser.add_argument("--start-month", default="2016-08")
    parser.add_argument("--end-month", default="2026-07")
    parser.add_argument("--delay-seconds", type=float, default=0.75)
    parser.add_argument("--minimum-free-gib", type=float, default=300.0)
    parser.add_argument("--poll-seconds", type=float, default=30.0)
    args = parser.parse_args()
    if args.poll_seconds <= 0:
        raise ValueError("poll seconds must be positive")
    lock = acquire_lock(args.intraday_output / "queue.lock")
    try:
        daily_manifest = wait_for_daily(
            args.daily_archive,
            poll_seconds=args.poll_seconds,
        )
        expected_latest = str(daily_manifest["expected_latest_date"])
        daily_audit = args.daily_archive / "content_audit.json"
        run_checked(
            [
                sys.executable,
                str(ROOT / "audit_alpha_vantage_full_nasdaq_daily.py"),
                "--archive",
                str(args.daily_archive),
                "--listing-status",
                str(args.listing_status),
                "--expected-latest-date",
                expected_latest,
                "--output",
                str(daily_audit),
            ],
            cwd=ROOT,
        )
        if not read_json(daily_audit).get("integrity_pass"):
            raise RuntimeError("daily archive content audit did not pass")
        active = active_alpha_collectors()
        if active:
            raise RuntimeError(
                f"refusing to start beside Alpha collector(s): {active}"
            )
        universe_path = args.daily_archive / "universe.json"
        run_checked(
            [
                sys.executable,
                str(ROOT / "download_alpha_vantage_full_nasdaq_5min.py"),
                "--universe",
                str(universe_path),
                "--output",
                str(args.intraday_output),
                "--start-month",
                args.start_month,
                "--end-month",
                args.end_month,
                "--seed-archive",
                str(args.seed_archive),
                "--delay-seconds",
                str(args.delay_seconds),
                "--minimum-free-gib",
                str(args.minimum_free_gib),
            ],
            cwd=ROOT,
        )
        intraday_audit = args.intraday_output / "content_audit.json"
        run_checked(
            [
                sys.executable,
                str(ROOT / "audit_alpha_vantage_full_nasdaq_5min.py"),
                "--archive",
                str(args.intraday_output),
                "--universe",
                str(universe_path),
                "--output",
                str(intraday_audit),
            ],
            cwd=ROOT,
        )
        if not read_json(intraday_audit).get("integrity_pass"):
            raise RuntimeError("five-minute archive content audit did not pass")
        run_checked(
            [
                sys.executable,
                str(ROOT / "update_promising_model_data_inventory.py"),
            ],
            cwd=ROOT,
        )
        print("FULL NASDAQ DAILY + FIVE-MINUTE ARCHIVE: COMPLETE", flush=True)
    finally:
        release_lock(lock)


if __name__ == "__main__":
    main()
