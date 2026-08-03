from __future__ import annotations

"""Record one immutable, research-only competition submission before 09:25 ET."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from alientai_v2.research.pick_competition import (
    append_submission,
    build_submission,
    competition_manifest,
    load_universe,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--participant", required=True)
    parser.add_argument("--decision-date", required=True)
    parser.add_argument("--round-id", required=True)
    parser.add_argument("--ticker", action="append", default=[])
    parser.add_argument("--universe-file", type=Path, default=Path("nasdaq100_2026-06_symbols.txt"))
    parser.add_argument(
        "--journal",
        type=Path,
        default=Path("data_v2/rcef_research/pick_competition_journal.jsonl"),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data_v2/rcef_research/pick_competition_manifest.json"),
    )
    args = parser.parse_args()

    requested_manifest = competition_manifest(args.universe_file)
    if args.manifest.exists():
        if json.loads(args.manifest.read_text(encoding="utf-8")) != requested_manifest:
            raise ValueError("existing competition manifest does not match frozen rules")
    else:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            json.dumps(requested_manifest, indent=2) + "\n",
            encoding="utf-8",
        )

    submission = build_submission(
        participant=args.participant,
        decision_date=args.decision_date,
        picks=args.ticker,
        universe=load_universe(args.universe_file),
        submitted_at=datetime.now(timezone.utc),
        round_id=args.round_id,
    )
    append_submission(args.journal, submission)
    print(json.dumps({
        "status": "frozen",
        "research_only": True,
        "execution_enabled": False,
        "participant": submission["participant"],
        "decision_date": submission["decision_date"],
        "picks": submission["picks"],
        "abstained": submission["abstained"],
        "journal": str(args.journal),
    }, indent=2))


if __name__ == "__main__":
    main()

