from __future__ import annotations

"""Run one fail-closed future-only Alpha Vantage LambdaRank attempt."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence
from zoneinfo import ZoneInfo

import psutil
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
MODEL_ID = "external_lambdarank_120_h20_alpha_vantage_v2_20260806"
FROZEN_THROUGH_SESSION = date(2026, 8, 6)
EASTERN = ZoneInfo("America/New_York")
MARKET_DATA_READY_TIME = time(16, 15)
PRE_ENTRY_DEADLINE = time(9, 25)
MINIMUM_D_FREE_BYTES = 20 * 1024**3

DEFAULT_ALL_SYMBOLS = (
    ROOT
    / "research_universes"
    / "external_lambdarank_120_plus_spy_20260806.txt"
)
DEFAULT_CANDIDATES = (
    ROOT / "research_universes" / "external_lambdarank_120_20260806.txt"
)
DEFAULT_MODEL_ROOT = Path(
    r"D:\AlientAI\Models"
    r"\external_lambdarank_120_h20_alpha_vantage_v2_20260806"
)
DEFAULT_ARCHIVE_BASE = Path(r"D:\AlientAI\Data\AlphaVantage_2026")
DEFAULT_PROSPECTIVE_BASE = Path(r"D:\AlientAI\Data\Prospective")
DEFAULT_JOURNAL = (
    ROOT
    / "data_v2"
    / "rcef_research"
    / "external_lambdarank_alpha_vantage_20d_prospective_journal.jsonl"
)


def next_weekday(value: date) -> date:
    candidate = value + timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate


def assess_timing(
    decision_date: date, now_utc: datetime
) -> dict[str, Any]:
    """Return a conservative future-only decision-window assessment.

    The archive itself proves that ``decision_date`` was a completed provider
    session.  The weekday deadline is deliberately conservative around market
    holidays: it may refuse a late attempt, but it can never authorize a
    backfill after a normal next-session entry.
    """
    if now_utc.tzinfo is None:
        raise ValueError("now_utc must be timezone-aware")
    if decision_date <= FROZEN_THROUGH_SESSION:
        return {
            "status": "BLOCKED_FROZEN_CUTOFF",
            "reason": (
                f"{decision_date.isoformat()} is not later than immutable "
                f"cutoff {FROZEN_THROUGH_SESSION.isoformat()}"
            ),
        }
    if decision_date.weekday() >= 5:
        return {
            "status": "BLOCKED_NON_WEEKDAY",
            "reason": f"{decision_date.isoformat()} is not a weekday",
        }
    eastern_now = now_utc.astimezone(EASTERN)
    completed_after = datetime.combine(
        decision_date, MARKET_DATA_READY_TIME, tzinfo=EASTERN
    )
    if eastern_now < completed_after:
        return {
            "status": "NOT_SCHEDULED_YET",
            "reason": (
                "the requested decision session has not reached the "
                "post-close data window"
            ),
            "eligible_after_eastern": completed_after.isoformat(),
        }
    deadline = datetime.combine(
        next_weekday(decision_date), PRE_ENTRY_DEADLINE, tzinfo=EASTERN
    )
    if eastern_now >= deadline:
        return {
            "status": "BLOCKED_MISSED_ENTRY_WINDOW",
            "reason": (
                "the conservative pre-entry deadline has passed; "
                "backfilling is forbidden"
            ),
            "deadline_eastern": deadline.isoformat(),
        }
    return {
        "status": "READY",
        "reason": "completed post-close session before next-entry deadline",
        "eligible_after_eastern": completed_after.isoformat(),
        "deadline_eastern": deadline.isoformat(),
    }


def conflicting_alpha_collectors(
    processes: Sequence[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Return other Python Alpha Vantage download/queue processes."""
    if processes is None:
        processes = []
        for process in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                processes.append(process.info)
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
    conflicts = []
    current_pid = os.getpid()
    for process in processes:
        pid = int(process.get("pid") or -1)
        name = str(process.get("name") or "").casefold()
        command = " ".join(
            str(part) for part in (process.get("cmdline") or [])
        ).casefold()
        if pid == current_pid or "python" not in name:
            continue
        if "alpha_vantage" not in command:
            continue
        if not any(
            marker in command
            for marker in ("download", "collector", "collect_", "queue")
        ):
            continue
        conflicts.append(
            {
                "pid": pid,
                "name": str(process.get("name") or ""),
                "command_class": "alpha_vantage_collector_or_queue",
            }
        )
    return conflicts


def read_journal(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_attempt(
    attempts_root: Path,
    decision_date: date,
    status: str,
    details: dict[str, Any],
) -> Path:
    attempts_root.mkdir(parents=True, exist_ok=True)
    observed = datetime.now(timezone.utc)
    token = observed.strftime("%Y%m%dT%H%M%S%fZ")
    path = attempts_root / (
        f"{decision_date.strftime('%Y%m%d')}_{token}_{status.casefold()}.json"
    )
    record = {
        "model_id": MODEL_ID,
        "decision_date": decision_date.isoformat(),
        "observed_at_utc": observed.isoformat(),
        "status": status,
        "details": details,
        "research_only": True,
        "execution_decision": "AVOID",
    }
    path.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _run(arguments: list[str], env: dict[str, str]) -> None:
    subprocess.run(
        [sys.executable, *arguments],
        cwd=ROOT,
        env=env,
        check=True,
    )


def _runtime_environment() -> dict[str, str]:
    runtime_root = Path(r"D:\AlientAI")
    if not runtime_root.is_dir():
        raise RuntimeError(f"D-drive runtime is unavailable: {runtime_root}")
    free_bytes = shutil.disk_usage(runtime_root).free
    if free_bytes < MINIMUM_D_FREE_BYTES:
        raise RuntimeError(
            "D-drive free-space gate failed: "
            f"{free_bytes / 1024**3:.2f} GiB available; 20 GiB required"
        )
    paths = {
        "ALIENTAI_RUNTIME_ROOT": runtime_root,
        "ALIENTAI_DATA_ROOT": runtime_root / "Data",
        "ALIENTAI_MODEL_ROOT": runtime_root / "Models",
        "ALIENTAI_LOG_ROOT": runtime_root / "Logs",
        "TEMP": runtime_root / "Temp",
        "TMP": runtime_root / "Temp",
        "JOBLIB_TEMP_FOLDER": runtime_root / "Temp" / "joblib",
        "PYTHONPYCACHEPREFIX": runtime_root / "Temp" / "pycache",
    }
    for path in paths.values():
        Path(path).mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update({key: str(value) for key, value in paths.items()})
    return env


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision-date", type=date.fromisoformat, required=True)
    parser.add_argument("--all-symbols", type=Path, default=DEFAULT_ALL_SYMBOLS)
    parser.add_argument(
        "--candidate-symbols", type=Path, default=DEFAULT_CANDIDATES
    )
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument(
        "--archive-base", type=Path, default=DEFAULT_ARCHIVE_BASE
    )
    parser.add_argument(
        "--prospective-base", type=Path, default=DEFAULT_PROSPECTIVE_BASE
    )
    parser.add_argument("--journal", type=Path, default=DEFAULT_JOURNAL)
    parser.add_argument("--delay-seconds", type=float, default=0.75)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    timing = assess_timing(args.decision_date, datetime.now(timezone.utc))
    if timing["status"] != "READY":
        print(json.dumps(timing, indent=2))
        if timing["status"].startswith("BLOCKED_"):
            raise SystemExit(1)
        return

    token = args.decision_date.strftime("%Y%m%d")
    archive = args.archive_base / (
        "external_lambdarank_120_plus_spy_adjusted_daily_compact_" + token
    )
    snapshot_root = args.prospective_base / (
        "external_lambdarank_120_h20_alpha_vantage_v2_" + token
    )
    score_root = args.prospective_base / (
        "external_lambdarank_120_h20_alpha_vantage_v2_scored_" + token
    )
    attempts_root = args.prospective_base / (
        "external_lambdarank_120_h20_alpha_vantage_v2_attempts"
    )
    existing = read_journal(args.journal)
    if any(
        row.get("model_id") == MODEL_ID
        and row.get("decision_date") == args.decision_date.isoformat()
        for row in existing
    ):
        print(
            json.dumps(
                {
                    "status": "ALREADY_JOURNALED",
                    "decision_date": args.decision_date.isoformat(),
                },
                indent=2,
            )
        )
        return

    conflicts = conflicting_alpha_collectors()
    if conflicts:
        attempt = _write_attempt(
            attempts_root,
            args.decision_date,
            "BLOCKED_DUPLICATE_COLLECTOR",
            {
                "conflicts": conflicts,
                "recovery": "wait for the singular existing collector to finish",
            },
        )
        print(
            json.dumps(
                {
                    "status": "BLOCKED_DUPLICATE_COLLECTOR",
                    "conflicts": conflicts,
                    "attempt": str(attempt),
                },
                indent=2,
            )
        )
        raise SystemExit(1)

    try:
        env = _runtime_environment()
        load_dotenv(ROOT / ".env")
        if not str(os.getenv("ALPHA_VANTAGE_API_KEY") or "").strip():
            raise RuntimeError("Alpha Vantage credential is unavailable")
        readiness = {
            "status": "READY" if not args.check_only else "CHECK_ONLY_READY",
            "decision_date": args.decision_date.isoformat(),
            "archive": str(archive),
            "snapshot_root": str(snapshot_root),
            "score_root": str(score_root),
            "journal": str(args.journal),
            "timing": timing,
            "execution_decision": "AVOID",
        }
        if args.check_only:
            print(json.dumps(readiness, indent=2))
            return

        _run(
            [
                "download_alpha_vantage_daily_panel.py",
                "--symbols-file",
                str(args.all_symbols),
                "--output",
                str(archive),
                "--delay-seconds",
                str(args.delay_seconds),
                "--outputsize",
                "compact",
                "--function",
                "TIME_SERIES_DAILY_ADJUSTED",
            ],
            env,
        )
        _run(
            [
                "audit_alpha_vantage_adjusted_daily_archive.py",
                "--archive",
                str(archive),
                "--symbols-file",
                str(args.all_symbols),
                "--required-latest-date",
                args.decision_date.isoformat(),
                "--required-outputsize",
                "compact",
            ],
            env,
        )
        if not (snapshot_root / "snapshot_manifest.json").exists():
            _run(
                [
                    "build_external_lambdarank_alpha_vantage_20d_snapshot.py",
                    "--symbols",
                    str(args.candidate_symbols),
                    "--archive",
                    str(archive),
                    "--model-root",
                    str(args.model_root),
                    "--decision-date",
                    args.decision_date.isoformat(),
                    "--output-root",
                    str(snapshot_root),
                ],
                env,
            )
        _run(
            [
                "score_external_lambdarank_alpha_vantage_20d.py",
                "--snapshot-root",
                str(snapshot_root),
                "--model-root",
                str(args.model_root),
                "--decision-date",
                args.decision_date.isoformat(),
                "--output-root",
                str(score_root),
                "--journal",
                str(args.journal),
            ],
            env,
        )
        _run(["update_promising_model_data_inventory.py"], env)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        attempt = _write_attempt(
            attempts_root,
            args.decision_date,
            "BLOCKED",
            {
                "error_type": type(exc).__name__,
                "error": str(exc)[:1000],
                "recovery": (
                    "inspect the dated source manifest and audit; retry only "
                    "inside the same pre-entry window without changing source"
                ),
            },
        )
        print(
            json.dumps(
                {
                    "status": "BLOCKED",
                    "attempt": str(attempt),
                    "recovery": (
                        "inspect the dated source manifest and audit before retry"
                    ),
                },
                indent=2,
            )
        )
        raise SystemExit(1) from None

    attempt = _write_attempt(
        attempts_root,
        args.decision_date,
        "NEW_OBSERVATION",
        {
            "archive": str(archive),
            "snapshot_manifest": str(
                snapshot_root / "snapshot_manifest.json"
            ),
            "observation": str(score_root / "observation.json"),
            "journal": str(args.journal),
        },
    )
    print(
        json.dumps(
            {
                "status": "NEW_OBSERVATION",
                "decision_date": args.decision_date.isoformat(),
                "attempt": str(attempt),
                "outcome": "PENDING_20_SESSIONS",
                "execution_decision": "AVOID",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
