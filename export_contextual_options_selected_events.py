from __future__ import annotations

"""Export the frozen contextual-options candidates for payoff translation."""

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from evaluate_context_portfolio import capacity_limited, file_sha256, split_chronologically
from evaluate_unusual_call_contexts import score_rows
from evaluate_unusual_call_outcomes import join_option_outcomes, read_jsonl


def select_events(
    calibration: Sequence[Mapping[str, Any]],
    test: Sequence[Mapping[str, Any]],
    top_fraction: float,
    max_open_positions: int,
) -> tuple[float, list[Mapping[str, Any]]]:
    if not 0 < top_fraction <= 1:
        raise ValueError("top_fraction must be in (0, 1]")
    scores = np.asarray([float(row["technical_context_score"]) for row in calibration], dtype=float)
    cutoff = float(np.quantile(scores, 1.0 - top_fraction))
    candidates = [
        row for row in test
        if bool(row.get("call_volume_unusual"))
        and float(row["technical_context_score"]) >= cutoff
    ]
    return cutoff, capacity_limited(candidates, max_open_positions)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-rows", type=Path, required=True)
    parser.add_argument("--option-features", type=Path, required=True)
    parser.add_argument("--technical-model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--calibration-fraction", type=float, default=0.60)
    parser.add_argument("--embargo-calendar-days", type=int, default=7)
    parser.add_argument("--top-fraction", type=float, default=0.25)
    parser.add_argument("--max-open-positions", type=int, default=5)
    args = parser.parse_args()

    raw_rows = join_option_outcomes(read_jsonl(args.base_rows), read_jsonl(args.option_features))
    model = lgb.Booster(model_file=str(args.technical_model))
    rows = score_rows(raw_rows, model)
    calibration, test = split_chronologically(
        rows, args.calibration_fraction, args.embargo_calendar_days,
    )
    cutoff, selected = select_events(
        calibration, test, args.top_fraction, args.max_open_positions,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in selected:
            handle.write(json.dumps(dict(row), sort_keys=True) + "\n")
    report = {
        "status": "complete",
        "classification": "RETROSPECTIVE_PAYOFF_TRANSLATION_INPUT",
        "research_only": True,
        "execution_enabled": False,
        "calibration_fraction": args.calibration_fraction,
        "embargo_calendar_days": args.embargo_calendar_days,
        "top_fraction": args.top_fraction,
        "max_open_positions": args.max_open_positions,
        "technical_score_cutoff": cutoff,
        "selected_events": len(selected),
        "distinct_symbols": len({str(row["symbol"]) for row in selected}),
        "input_artifacts": {
            "base_rows_sha256": file_sha256(args.base_rows),
            "option_features_sha256": file_sha256(args.option_features),
            "technical_model_sha256": file_sha256(args.technical_model),
        },
        "output_sha256": file_sha256(args.output),
        "warning": (
            "Already-observed historical candidates for fixed-policy option payoff "
            "translation only; never prospective evidence or execution authorization."
        ),
    }
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
