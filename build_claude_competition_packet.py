from __future__ import annotations

"""Build a point-in-time, score-free briefing packet for a Claude competitor."""

import argparse
import hashlib
import json
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def load_universe(path: Path) -> list[str]:
    symbols = [
        line.strip().upper()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not symbols or len(symbols) != len(set(symbols)):
        raise ValueError("universe must contain unique nonblank symbols")
    return symbols


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number} is not a JSON object")
        rows.append(row)
    return rows


def exact_symbol_index(
    rows: Iterable[dict[str, Any]],
    universe: list[str],
    family: str,
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        if not symbol:
            raise ValueError(f"{family} contains a blank symbol")
        if symbol in index:
            raise ValueError(f"{family} contains duplicate symbol {symbol}")
        index[symbol] = row
    expected = set(universe)
    actual = set(index)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(
            f"{family} symbol coverage mismatch; missing={missing}, extra={extra}"
        )
    return index


def single_market_date(
    rows: Iterable[dict[str, Any]],
    family: str,
) -> date:
    values = {str(row.get("market_date", "")).strip() for row in rows}
    if len(values) != 1 or not next(iter(values), ""):
        raise ValueError(f"{family} must contain one nonblank market_date")
    return date.fromisoformat(next(iter(values)))


def technical_fields(row: dict[str, Any]) -> dict[str, Any]:
    allowed = {"close", "market_date", "source"}
    return {
        key: value
        for key, value in sorted(row.items())
        if key in allowed or key.startswith("technical_")
    }


def premarket_fields(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in sorted(row.items())
        if key == "market_date" or key.startswith("premarket_")
    }


def call_fields(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in sorted(row.items())
        if key == "market_date" or key.startswith("call_")
    }


def validate_premarket(
    rows: list[dict[str, Any]],
    decision_date: date,
) -> None:
    if single_market_date(rows, "premarket") != decision_date:
        raise ValueError("premarket market_date must equal decision date")
    for row in rows:
        if row.get("premarket_available") is not True:
            raise ValueError("premarket packet requires every symbol to be available")
        if str(row.get("premarket_cutoff_et", "")) != "09:25":
            raise ValueError("premarket cutoff must be exactly 09:25 ET")
        expected = f"{decision_date.isoformat()} 09:25:00"
        if str(row.get("premarket_last_timestamp_et", "")) != expected:
            raise ValueError("premarket data must end exactly at 09:25 ET")


def packet_readme(manifest: dict[str, Any]) -> str:
    families = ", ".join(manifest["included_feature_families"])
    return f"""# Claude prospective pick-competition packet

This packet is research-only. It cannot create a paper or live order.

## Frozen facts

- Decision date: {manifest["decision_date"]}
- Universe: {manifest["universe_size"]} symbols
- Information cutoff: {manifest["information_cutoff"]}
- Included evidence: {families}
- Prior technical session: {manifest["technical_market_date"]}
- Model predictions, scores, ranks, probabilities, labels, and future outcomes:
  **excluded**

## Claude's task

Use only `claude_competition_data.json`. Do not browse the web or add facts
that are not in the packet. Select zero through five unique tickers from the
provided universe. Abstain when the evidence is insufficient. Rank selected
tickers from strongest to weakest and give a concise, evidence-based reason
for each.

Return exactly one JSON object:

```json
{{
  "participant": "Claude",
  "decision_date": "{manifest["decision_date"]}",
  "picks": ["TICKER"],
  "ranked_reasons": [
    {{"rank": 1, "symbol": "TICKER", "reason": "Brief packet-grounded reason"}}
  ],
  "abstained": false
}}
```

If selecting no stocks, return an empty `picks` and `ranked_reasons` array and
set `abstained` to true. Do not provide more than five picks.

## Frozen evaluation

- Submission deadline: 09:25 Eastern
- Entry reference: 09:30 Eastern regular-session open
- Horizons: 20 minutes, 60 minutes, 2, 5, 10, and 20 trading sessions
- Round-trip cost: 0.25%
- Basket weighting: equal weight
- Tracks: unmanaged fixed horizon and separately measured -5% stop-managed

One round cannot prove an edge. Claude's immutable submissions will be
evaluated over repeated future rounds under the same rules.
"""


def build_packet(
    *,
    decision_date_text: str,
    universe_file: Path,
    technical_panel: Path,
    output_dir: Path,
    premarket_panel: Path | None = None,
    call_panel: Path | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Path]:
    decision_date = date.fromisoformat(decision_date_text)
    universe = load_universe(universe_file)

    technical_rows = load_jsonl(technical_panel)
    technical = exact_symbol_index(technical_rows, universe, "technical")
    technical_date = single_market_date(technical_rows, "technical")
    if technical_date >= decision_date:
        raise ValueError("technical features must precede the decision date")

    premarket: dict[str, dict[str, Any]] | None = None
    if premarket_panel is not None:
        premarket_rows = load_jsonl(premarket_panel)
        premarket = exact_symbol_index(premarket_rows, universe, "premarket")
        validate_premarket(premarket_rows, decision_date)

    calls: dict[str, dict[str, Any]] | None = None
    if call_panel is not None:
        call_rows = load_jsonl(call_panel)
        calls = exact_symbol_index(call_rows, universe, "calls")
        if single_market_date(call_rows, "calls") != technical_date:
            raise ValueError("call features must match the prior technical session")

    created = generated_at or datetime.now(timezone.utc)
    families = ["prior_close_technical"]
    if premarket is not None:
        families.append("current_premarket_through_09_25_et")
    if calls is not None:
        families.append("prior_session_call_activity")

    records: list[dict[str, Any]] = []
    for symbol in universe:
        record: dict[str, Any] = {
            "symbol": symbol,
            "technical": technical_fields(technical[symbol]),
        }
        if premarket is not None:
            record["premarket"] = premarket_fields(premarket[symbol])
        if calls is not None:
            record["call_activity"] = call_fields(calls[symbol])
        records.append(record)

    manifest: dict[str, Any] = {
        "schema_version": 1,
        "research_only": True,
        "execution_enabled": False,
        "participant": "Claude",
        "decision_date": decision_date.isoformat(),
        "generated_at_utc": created.astimezone(timezone.utc).isoformat(),
        "information_cutoff": (
            f"{decision_date.isoformat()} 09:25:00 America/New_York"
            if premarket is not None
            else f"{technical_date.isoformat()} regular-session close"
        ),
        "technical_market_date": technical_date.isoformat(),
        "universe_size": len(universe),
        "included_feature_families": families,
        "model_outputs_excluded": True,
        "future_information_excluded": True,
        "source_files": {
            "universe_sha256": hashlib.sha256(universe_file.read_bytes()).hexdigest(),
            "technical_sha256": hashlib.sha256(
                technical_panel.read_bytes()
            ).hexdigest(),
            "premarket_sha256": (
                hashlib.sha256(premarket_panel.read_bytes()).hexdigest()
                if premarket_panel is not None
                else None
            ),
            "calls_sha256": (
                hashlib.sha256(call_panel.read_bytes()).hexdigest()
                if call_panel is not None
                else None
            ),
        },
    }
    payload = {"manifest": manifest, "records": records}

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"claude_competition_packet_{decision_date.isoformat()}"
    json_path = output_dir / f"{stem}.json"
    readme_path = output_dir / f"{stem}_README.md"
    zip_path = output_dir / f"{stem}.zip"

    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    readme_path.write_text(packet_readme(manifest), encoding="utf-8")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(json_path, arcname="claude_competition_data.json")
        archive.write(readme_path, arcname="README.md")

    return {"json": json_path, "readme": readme_path, "zip": zip_path}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision-date", required=True)
    parser.add_argument(
        "--universe-file",
        type=Path,
        default=Path("nasdaq100_2026-06_symbols.txt"),
    )
    parser.add_argument("--technical-panel", type=Path, required=True)
    parser.add_argument("--premarket-panel", type=Path)
    parser.add_argument("--call-panel", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data_v2/rcef_research/claude_competition_packets"),
    )
    args = parser.parse_args()

    outputs = build_packet(
        decision_date_text=args.decision_date,
        universe_file=args.universe_file,
        technical_panel=args.technical_panel,
        premarket_panel=args.premarket_panel,
        call_panel=args.call_panel,
        output_dir=args.output_dir,
    )
    print(
        json.dumps(
            {
                "status": "complete",
                "research_only": True,
                "execution_enabled": False,
                "outputs": {key: str(value) for key, value in outputs.items()},
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
