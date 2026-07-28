"""Build a complete prior-session contextual-options payload for paper trading."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import lightgbm as lgb

from contextual_options_shadow_adapter import build_payload
from evaluate_matched_winner_full_universe import build_matrix


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def keyed(rows: Iterable[Mapping[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    output: dict[tuple[str, str], dict[str, Any]] = {}
    for source in rows:
        row = dict(source)
        key = (str(row.get("symbol") or "").upper(), str(row.get("market_date") or ""))
        if not all(key) or key in output:
            raise ValueError("panel contains a missing or duplicate symbol/date key")
        output[key] = row
    return output


def matched_rows(
    technical_rows: Iterable[Mapping[str, Any]],
    option_rows: Iterable[Mapping[str, Any]],
    minimum_rows: int = 400,
) -> list[dict[str, Any]]:
    technical, options = keyed(technical_rows), keyed(option_rows)
    common = sorted(set(technical) & set(options))
    if len(common) < minimum_rows:
        raise ValueError(f"incomplete common universe: need {minimum_rows}, got {len(common)}")
    dates = {key[1] for key in common}
    if len(dates) != 1:
        raise ValueError("matched input must contain exactly one market date")
    return [{**technical[key], **options[key]} for key in common]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a complete current contextual-options paper payload.")
    parser.add_argument("--technical-panel", type=Path, required=True)
    parser.add_argument("--option-panel", type=Path, required=True)
    parser.add_argument("--technical-model", type=Path, required=True)
    parser.add_argument("--scored-output", type=Path, required=True)
    parser.add_argument("--payload-output", type=Path, required=True)
    parser.add_argument("--minimum-universe-rows", type=int, default=400)
    args = parser.parse_args()
    rows = matched_rows(
        read_jsonl(args.technical_panel), read_jsonl(args.option_panel),
        args.minimum_universe_rows,
    )
    model = lgb.Booster(model_file=str(args.technical_model))
    scores = model.predict(build_matrix(rows, model.feature_name()))
    scored = [
        {**row, "technical_context_score": float(score)}
        for row, score in zip(rows, scores)
    ]
    payload = build_payload(scored, minimum_universe_rows=args.minimum_universe_rows)
    payload["input_artifacts"] = {
        "technical_panel_sha256": sha256(args.technical_panel),
        "option_panel_sha256": sha256(args.option_panel),
        "technical_model_sha256": sha256(args.technical_model),
    }
    args.scored_output.parent.mkdir(parents=True, exist_ok=True)
    with args.scored_output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in scored:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    args.payload_output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "market_date": payload["market_date"],
                      "universe_rows": payload["universe_rows"],
                      "candidates": len(payload["candidates"])}, indent=2))


if __name__ == "__main__":
    main()
