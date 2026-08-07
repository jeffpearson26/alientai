from __future__ import annotations

from datetime import date, datetime, timezone

from run_external_lambdarank_alpha_vantage_20d_future_attempt import (
    assess_timing,
    conflicting_alpha_collectors,
)


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def test_timing_rejects_frozen_session() -> None:
    result = assess_timing(date(2026, 8, 6), _utc("2026-08-06T21:00:00+00:00"))
    assert result["status"] == "BLOCKED_FROZEN_CUTOFF"


def test_timing_waits_until_post_close_window() -> None:
    result = assess_timing(date(2026, 8, 7), _utc("2026-08-07T19:59:00+00:00"))
    assert result["status"] == "NOT_SCHEDULED_YET"


def test_timing_allows_friday_after_close_before_monday_entry() -> None:
    result = assess_timing(date(2026, 8, 7), _utc("2026-08-08T03:00:00+00:00"))
    assert result["status"] == "READY"
    assert result["deadline_eastern"].startswith("2026-08-10T09:25:00")


def test_timing_rejects_backfill_after_next_entry_deadline() -> None:
    result = assess_timing(date(2026, 8, 7), _utc("2026-08-10T13:26:00+00:00"))
    assert result["status"] == "BLOCKED_MISSED_ENTRY_WINDOW"


def test_timing_rejects_weekend_decision_date() -> None:
    result = assess_timing(date(2026, 8, 8), _utc("2026-08-09T03:00:00+00:00"))
    assert result["status"] == "BLOCKED_NON_WEEKDAY"


def test_duplicate_detection_returns_only_other_python_collectors() -> None:
    processes = [
        {
            "pid": 987651,
            "name": "python.exe",
            "cmdline": [
                "python",
                "download_alpha_vantage_daily_panel.py",
            ],
        },
        {
            "pid": 987652,
            "name": "python.exe",
            "cmdline": ["python", "score_external_lambdarank_alpha.py"],
        },
        {
            "pid": 987653,
            "name": "powershell.exe",
            "cmdline": ["powershell", "download_alpha_vantage_queue.ps1"],
        },
    ]
    conflicts = conflicting_alpha_collectors(processes)
    assert conflicts == [
        {
            "pid": 987651,
            "name": "python.exe",
            "command_class": "alpha_vantage_collector_or_queue",
        }
    ]
