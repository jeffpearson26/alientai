"""Join a complete technical/options day and score it as non-promotable backfill research."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import lightgbm as lgb
import numpy as np

from evaluate_matched_winner_full_universe import build_matrix


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def key(row: Mapping[str, Any]) -> tuple[str, str]:
    return str(row.get("symbol") or "").upper(), str(row.get("market_date") or "")


def index_unique(rows: Iterable[Mapping[str, Any]], name: str) -> dict[tuple[str, str], Mapping[str, Any]]:
    output = {}
    for row in rows:
        row_key = key(row)
        if not all(row_key) or row_key in output:
            raise ValueError(f"{name} has missing or duplicate symbol/date key")
        output[row_key] = row
    return output


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build(technical_rows: Iterable[Mapping[str, Any]], option_rows: Iterable[Mapping[str, Any]], model: lgb.Booster) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    technical, options = index_unique(technical_rows, "technical panel"), index_unique(option_rows, "option panel")
    if set(technical) != set(options):
        raise ValueError("technical and option panels must have identical complete symbol/date keys")
    rows = [{**technical[row_key], **options[row_key]} for row_key in sorted(technical)]
    dates = {row["market_date"] for row in rows}
    if len(dates) != 1:
        raise ValueError("backfill input must contain exactly one market date")
    scores = model.predict(build_matrix(rows, model.feature_name()))
    scored = [{**row, "technical_context_score": float(score), "backfill_only": True} for row, score in zip(rows, scores)]
    score_values = np.asarray(scores, dtype=float)
    cutoff = float(np.quantile(score_values, 0.75))
    unusual = [row for row in scored if row.get("call_volume_unusual")]
    return scored, {"rows": len(scored), "market_date": next(iter(dates)), "unusual_calls": len(unusual),
                    "top_quartile_cutoff": cutoff,
                    "top_quartile_unusual_calls": sum(bool(row.get("call_volume_unusual")) and row["technical_context_score"] >= cutoff for row in scored)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build non-promotable complete contextual-options backfill panel.")
    parser.add_argument("--technical-panel", type=Path, required=True)
    parser.add_argument("--option-panel", type=Path, required=True)
    parser.add_argument("--technical-model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    args = parser.parse_args()
    model = lgb.Booster(model_file=str(args.technical_model))
    rows, summary = build(read_jsonl(args.technical_panel), read_jsonl(args.option_panel), model)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    result = {"status": "complete", "research_only": True, "execution_enabled": False,
              "classification": "BACKFILL_RESEARCH_ONLY", "eligible_for_prospective_gate": False,
              "input_artifacts": {"technical_panel_sha256": file_sha256(args.technical_panel), "option_panel_sha256": file_sha256(args.option_panel), "technical_model_sha256": file_sha256(args.technical_model)},
              **summary,
              "warning": "This date was joined after its decision date and cannot count as prospective evidence."}
    args.summary_output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
