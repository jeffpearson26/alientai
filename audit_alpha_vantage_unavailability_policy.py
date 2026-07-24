from __future__ import annotations

"""Make completed Alpha Vantage archive unavailability explicit and join-safe."""

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"manifest must be an object: {path}")
    return payload


def transcript_policy(entries: list[str]) -> dict[str, Any]:
    return {
        "unavailable_count": len(entries),
        "requests": sorted(entries),
        "join_policy": "Preserve explicit missing transcript features; never substitute a later/current transcript or impute a non-event value.",
        "retry_policy": "Do not retry a completed unavailable request unless provider coverage is independently shown to have changed.",
    }


def premarket_policy(entries: list[str]) -> dict[str, Any]:
    symbols = [entry.split("|", 1)[0] for entry in entries]
    by_symbol = dict(sorted(Counter(symbols).items()))
    share_class = sorted({symbol for symbol in by_symbol if "." in symbol})
    other = sorted({symbol for symbol in by_symbol if "." not in symbol})
    return {
        "unavailable_count": len(entries),
        "unavailable_by_symbol": by_symbol,
        "share_class_symbols": share_class,
        "other_symbols": other,
        "join_policy": "Preserve explicit missing premarket features and labels for unavailable requests; exclude them only through a documented availability filter, never by filling from another symbol/month.",
        "retry_policy": "Retry only after a tested provider-symbol mapping or provider coverage change; do not rename archive keys in place.",
    }


def audit(transcript_manifest: dict[str, Any], premarket_manifest: dict[str, Any]) -> dict[str, Any]:
    transcript_entries = [str(value) for value in transcript_manifest.get("unavailable", [])]
    premarket_entries = [str(value) for value in premarket_manifest.get("unavailable", [])]
    return {
        "status": "complete",
        "research_only": True,
        "transcripts": transcript_policy(transcript_entries),
        "premarket": premarket_policy(premarket_entries),
        "global_policy": [
            "Unavailable is not negative, zero, or a substitute-current-data signal.",
            "Keep source request identity and reason category in any future compact feature table.",
            "No unavailable item may be silently backfilled from future data.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Write a read-only join policy for completed Alpha Vantage unavailabilities.")
    parser.add_argument("--transcript-manifest", type=Path, required=True)
    parser.add_argument("--premarket-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(load_manifest(args.transcript_manifest), load_manifest(args.premarket_manifest))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "transcript_unavailable": report["transcripts"]["unavailable_count"], "premarket_unavailable": report["premarket"]["unavailable_count"]}, indent=2))


if __name__ == "__main__":
    main()
