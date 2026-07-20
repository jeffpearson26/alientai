from __future__ import annotations

import argparse
import gzip
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from alientai_v2.features.earnings_estimate_features import earnings_estimate_features
from alientai_v2.features.institutional_holding_features import institutional_holding_features
from alientai_v2.features.shares_outstanding_features import shares_outstanding_features


def load_document(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def compile_symbol(root: Path, symbol: str, as_of_utc: str) -> Dict[str, Any]:
    row: Dict[str, Any] = {"symbol": symbol, "as_of_utc": as_of_utc}
    sources = [
        ("earnings_estimates", earnings_estimate_features),
        ("shares_outstanding", shares_outstanding_features),
        ("institutional_holdings", institutional_holding_features),
    ]
    for directory, feature_function in sources:
        document = load_document(root / directory / f"{symbol}.json.gz")
        if document is not None:
            row.update(feature_function(document, as_of_utc))
    return row


def available_symbols(root: Path):
    symbols = set()
    for directory in ("earnings_estimates", "shares_outstanding", "institutional_holdings"):
        path = root / directory
        if path.exists():
            symbols.update(file.name[:-8] for file in path.glob("*.json.gz"))
    return sorted(symbols)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshots", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--as-of-utc", default=datetime.now(timezone.utc).isoformat())
    args = parser.parse_args()
    rows = [compile_symbol(args.snapshots, symbol, args.as_of_utc) for symbol in available_symbols(args.snapshots)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps({"status": "complete", "symbols": len(rows), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
