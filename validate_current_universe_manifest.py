from __future__ import annotations

"""Fail-closed validator for a dated, externally sourced research universe.

This tool deliberately does not infer current index membership from an old
symbol list. A supplied manifest must name a source, preserve its retrieval
date, and include a dated constituent snapshot before it can become an input
to a future small-cap research design.
"""

import argparse
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-/]*$")
REQUIRED_FIELDS = ("schema_version", "universe_name", "as_of_date", "retrieved_at_utc", "source_name", "source_url", "symbols")


def load_symbols(path: Path) -> set[str]:
    return {
        line.strip().upper()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def parse_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("universe manifest must be a JSON object")
    return payload


def validate_manifest(payload: dict[str, Any], *, excluded_symbols: set[str] | None = None) -> dict[str, Any]:
    missing_fields = [field for field in REQUIRED_FIELDS if not payload.get(field)]
    errors: list[str] = []
    if missing_fields:
        errors.append("missing required fields: " + ", ".join(missing_fields))
    try:
        date.fromisoformat(str(payload.get("as_of_date") or ""))
    except ValueError:
        errors.append("as_of_date must be ISO YYYY-MM-DD")
    try:
        datetime.fromisoformat(str(payload.get("retrieved_at_utc") or "").replace("Z", "+00:00"))
    except ValueError:
        errors.append("retrieved_at_utc must be ISO-8601")
    source_url = str(payload.get("source_url") or "")
    parsed_url = urlparse(source_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        errors.append("source_url must be an absolute http(s) URL")

    raw_symbols = payload.get("symbols")
    if not isinstance(raw_symbols, list):
        raw_symbols = []
    normalized = [str(symbol).strip().upper() for symbol in raw_symbols]
    invalid = sorted({symbol for symbol in normalized if not SYMBOL_RE.fullmatch(symbol)})
    symbols = sorted({symbol for symbol in normalized if SYMBOL_RE.fullmatch(symbol)})
    if not symbols:
        errors.append("symbols must include at least one valid ticker")
    if invalid:
        errors.append("symbols contains invalid ticker values")

    excluded = excluded_symbols or set()
    overlap = sorted(set(symbols) & excluded)
    return {
        "status": "valid" if not errors else "invalid",
        "research_only": True,
        "errors": errors,
        "universe_name": str(payload.get("universe_name") or ""),
        "as_of_date": str(payload.get("as_of_date") or ""),
        "retrieved_at_utc": str(payload.get("retrieved_at_utc") or ""),
        "source_name": str(payload.get("source_name") or ""),
        "source_url": source_url,
        "valid_symbol_count": len(symbols),
        "duplicate_symbol_count": len(normalized) - len(set(normalized)),
        "invalid_symbols": invalid,
        "symbols": symbols,
        "excluded_symbol_overlap": overlap,
        "limitations": [
            "A valid manifest records a current snapshot; it does not reconstruct historical index membership.",
            "This validation does not establish price history, liquidity, corporate-action correctness, tradability, or predictive value.",
            "A future model must use dated membership snapshots and point-in-time eligibility for every historical decision date.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a dated research-universe manifest without downloading or training.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--exclude-symbols", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    excluded = load_symbols(args.exclude_symbols) if args.exclude_symbols else set()
    report = validate_manifest(parse_manifest(args.manifest), excluded_symbols=excluded)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "valid_symbol_count", "duplicate_symbol_count", "excluded_symbol_overlap", "errors")}, indent=2))
    if report["status"] != "valid":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
