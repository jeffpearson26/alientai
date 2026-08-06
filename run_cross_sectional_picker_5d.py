from __future__ import annotations

"""End-to-end command runner for the five-session cross-sectional picker."""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from train_cross_sectional_picker_5d import load_config


REPOSITORY = Path(__file__).resolve().parent


def run(arguments: list[str]) -> None:
    subprocess.run([sys.executable, *arguments], cwd=REPOSITORY, check=True)


def panel_paths(root: Path) -> tuple[Path, Path, Path]:
    return (
        root / "panel.jsonl",
        root / "panel.manifest.json",
        root / "content_audit.json",
    )


def build_panel(config: dict[str, Any], root: Path) -> None:
    panel, manifest, audit = panel_paths(root)
    if root.exists() and any(root.iterdir()):
        raise ValueError("panel root must be new and empty")
    data = config["data"]
    run(
        [
            "build_cross_sectional_technical_5d_panel.py",
            "--primary-daily-root",
            data["primary_daily_root"],
            "--ai-supplement-daily-root",
            data["ai_supplement_daily_root"],
            "--nasdaq-symbols",
            data["nasdaq_symbols"],
            "--ai-symbols",
            data["ai_symbols"],
            "--output",
            str(panel),
            "--minimum-cross-sectional-coverage",
            str(data["minimum_cross_sectional_coverage"]),
        ]
    )
    run(
        [
            "audit_cross_sectional_technical_5d_panel.py",
            "--panel",
            str(panel),
            "--manifest",
            str(manifest),
            "--output",
            str(audit),
        ]
    )


def train(
    config_path: Path, panel_root: Path, model_root: Path
) -> None:
    panel, manifest, audit = panel_paths(panel_root)
    audit_payload = json.loads(audit.read_text(encoding="utf-8"))
    if audit_payload.get("status") != "PASS":
        raise ValueError("panel content audit has not passed")
    run(
        [
            "train_cross_sectional_picker_5d.py",
            "--config",
            str(config_path),
            "--panel",
            str(panel),
            "--panel-manifest",
            str(manifest),
            "--output-root",
            str(model_root),
        ]
    )


def score(
    config_path: Path,
    model_root: Path,
    ranking_root: Path,
    *,
    as_of_date: str | None,
    research_preview: bool,
) -> None:
    arguments = [
        "score_cross_sectional_picker_5d.py",
        "--config",
        str(config_path),
        "--model-root",
        str(model_root),
        "--output-json",
        str(ranking_root / "daily_ranking.json"),
        "--output-csv",
        str(ranking_root / "daily_ranking.csv"),
    ]
    if as_of_date:
        arguments.extend(["--as-of-date", as_of_date])
    if research_preview:
        arguments.append("--research-preview")
    run(arguments)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=REPOSITORY / "cross_sectional_picker_5d_config.json",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--panel-root", type=Path, required=True)

    train_parser = subparsers.add_parser("train")
    train_parser.add_argument("--panel-root", type=Path, required=True)
    train_parser.add_argument("--model-root", type=Path, required=True)

    score_parser = subparsers.add_parser("score")
    score_parser.add_argument("--model-root", type=Path, required=True)
    score_parser.add_argument("--ranking-root", type=Path, required=True)
    score_parser.add_argument("--as-of-date")
    score_parser.add_argument("--research-preview", action="store_true")

    all_parser = subparsers.add_parser("all")
    all_parser.add_argument("--panel-root", type=Path, required=True)
    all_parser.add_argument("--model-root", type=Path, required=True)
    all_parser.add_argument("--ranking-root", type=Path, required=True)
    all_parser.add_argument("--as-of-date")
    all_parser.add_argument("--research-preview", action="store_true")
    all_parser.add_argument(
        "--reuse-audited-panel",
        action="store_true",
        help="Use an existing panel root only when its audit already passes.",
    )

    args = parser.parse_args()
    config = load_config(args.config)
    if args.command == "build":
        build_panel(config, args.panel_root)
    elif args.command == "train":
        train(args.config, args.panel_root, args.model_root)
    elif args.command == "score":
        score(
            args.config,
            args.model_root,
            args.ranking_root,
            as_of_date=args.as_of_date,
            research_preview=args.research_preview,
        )
    elif args.command == "all":
        if not args.reuse_audited_panel:
            build_panel(config, args.panel_root)
        train(args.config, args.panel_root, args.model_root)
        score(
            args.config,
            args.model_root,
            args.ranking_root,
            as_of_date=args.as_of_date,
            research_preview=args.research_preview,
        )


if __name__ == "__main__":
    main()
