from __future__ import annotations

"""Create exact, deduplicated after-close news requests from an options panel."""

import argparse
import json
from pathlib import Path


def create_requests(rows: list[dict]) -> list[dict]:
    keys = {
        (str(row.get("symbol") or "").upper(), str(row.get("market_date") or "")[:10])
        for row in rows
    }
    if any(not symbol or len(day) != 10 for symbol, day in keys):
        raise ValueError("every input row requires symbol and market_date")
    return [
        {
            "symbol": symbol,
            "market_date": day,
            "as_of_utc": f"{day}T21:00:00+00:00",
            "study_role": "all",
            "research_only": True,
        }
        for symbol, day in sorted(keys, key=lambda item: (item[1], item[0]))
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    requests = create_requests(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in requests), encoding="utf-8")
    print(json.dumps({"status": "complete", "requests": len(requests)}))


if __name__ == "__main__":
    main()
