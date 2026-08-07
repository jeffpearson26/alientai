from __future__ import annotations

"""Complete both frozen technical horizons after the two data audits pass."""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_checked(arguments: list[str]) -> None:
    print(f"RUN {' '.join(arguments)}", flush=True)
    result = subprocess.run(arguments, cwd=ROOT, check=False)
    if result.returncode:
        raise RuntimeError(
            f"command failed with exit {result.returncode}: "
            f"{' '.join(arguments)}"
        )


def conflicting_model_jobs() -> list[dict[str, Any]]:
    patterns = (
        "compile_rolling_twenty_minute_panel.py",
        "train_rolling_twenty_minute_lightgbm.py",
        "build_full_archive_multiresolution_technical_panel.py",
        "train_full_archive_multiresolution_technical.py",
    )
    own_pid = os.getpid()
    output: list[dict[str, Any]] = []
    for process in psutil.process_iter(["pid", "cmdline"]):
        try:
            if process.info["pid"] == own_pid:
                continue
            command = " ".join(process.info.get("cmdline") or [])
            if any(pattern in command for pattern in patterns):
                output.append(
                    {
                        "pid": process.info["pid"],
                        "command": command[:240],
                    }
                )
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    return output


def wait_for_model_capacity(poll_seconds: float) -> None:
    announced = False
    while True:
        jobs = conflicting_model_jobs()
        if not jobs:
            return
        if not announced:
            print(
                f"WAITING for existing compiler/trainer job(s): {jobs}",
                flush=True,
            )
            announced = True
        time.sleep(poll_seconds)


def require_audit(path: Path) -> None:
    payload = read_json(path)
    if not payload.get("integrity_pass"):
        raise ValueError(f"required content audit did not pass: {path}")


def empty_or_absent(path: Path) -> bool:
    return not path.exists() or not any(path.iterdir())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", type=Path, required=True)
    parser.add_argument("--daily-archive", type=Path, required=True)
    parser.add_argument("--intraday-archive", type=Path, required=True)
    parser.add_argument("--spy-daily-file", type=Path, required=True)
    parser.add_argument("--panel-root", type=Path, required=True)
    parser.add_argument("--models-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--poll-seconds", type=float, default=60.0)
    args = parser.parse_args()
    for path in (args.panel_root, args.models_root, args.output):
        if path.resolve().drive.upper() != "D:":
            raise ValueError(f"large model pipeline output must use D: {path}")
    require_audit(args.daily_archive / "content_audit.json")
    require_audit(args.intraday_archive / "content_audit.json")
    wait_for_model_capacity(args.poll_seconds)
    panel_manifest = args.panel_root / "manifest.json"
    panel_audit = args.panel_root / "content_audit.json"
    if not panel_manifest.exists():
        if not empty_or_absent(args.panel_root):
            raise ValueError("partial panel root exists without manifest")
        run_checked(
            [
                sys.executable,
                str(ROOT / "build_full_archive_multiresolution_technical_panel.py"),
                "--symbols",
                str(args.symbols),
                "--daily-archive",
                str(args.daily_archive),
                "--intraday-archive",
                str(args.intraday_archive),
                "--spy-daily-file",
                str(args.spy_daily_file),
                "--output-root",
                str(args.panel_root),
                "--start-month",
                "2016-08",
                "--end-month",
                "2026-07",
            ]
        )
    if not panel_audit.exists():
        run_checked(
            [
                sys.executable,
                str(ROOT / "audit_full_archive_multiresolution_technical_panel.py"),
                "--panel-root",
                str(args.panel_root),
            ]
        )
    require_audit(panel_audit)
    model_roots = {
        5: args.models_root
        / "full_archive_multiresolution_nasdaq101_h05_v1_20260807",
        20: args.models_root
        / "full_archive_multiresolution_nasdaq101_h20_v1_20260807",
    }
    for horizon, model_root in model_roots.items():
        report_path = model_root / "training_report.json"
        if not report_path.exists():
            if not empty_or_absent(model_root):
                raise ValueError(
                    f"partial model root exists without report: {model_root}"
                )
            wait_for_model_capacity(args.poll_seconds)
            run_checked(
                [
                    sys.executable,
                    str(ROOT / "train_full_archive_multiresolution_technical.py"),
                    "--panel-root",
                    str(args.panel_root),
                    "--horizon",
                    str(horizon),
                    "--output-root",
                    str(model_root),
                ]
            )
    models_audit = args.models_root / (
        "full_archive_multiresolution_nasdaq101_v1_20260807_model_audit.json"
    )
    run_checked(
        [
            sys.executable,
            str(
                ROOT
                / "audit_full_archive_multiresolution_technical_models.py"
            ),
            "--h05-root",
            str(model_roots[5]),
            "--h20-root",
            str(model_roots[20]),
            "--output",
            str(models_audit),
        ]
    )
    require_audit(models_audit)
    result = {
        "status": "COMPLETE",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_family": "full_archive_multiresolution_technical_ranker",
        "panel_manifest": str(panel_manifest.resolve()),
        "panel_manifest_sha256": sha256(panel_manifest),
        "panel_audit": str(panel_audit.resolve()),
        "panel_audit_sha256": sha256(panel_audit),
        "model_audit": str(models_audit.resolve()),
        "model_audit_sha256": sha256(models_audit),
        "model_roots": {
            str(horizon): str(path.resolve())
            for horizon, path in model_roots.items()
        },
        "research_only": True,
        "execution_decision": "AVOID",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    run_checked(
        [
            sys.executable,
            str(ROOT / "update_promising_model_data_inventory.py"),
        ]
    )
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
