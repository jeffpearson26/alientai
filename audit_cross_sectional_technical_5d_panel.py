from __future__ import annotations

"""Audit every row of the cross-sectional five-session research panel."""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from alientai_v2.research.cross_sectional_technical_5d import (
    RANK_FEATURES,
    TRANSPARENT_WEIGHTS,
)
from train_cross_sectional_technical_5d import sha256


def audit_panel(
    panel: Path, manifest: Mapping[str, Any]
) -> dict[str, Any]:
    expected_candidates = set(manifest["candidates"])
    expected_minimum = int(
        manifest["minimum_cross_sectional_coverage_count"]
    )
    seen = set()
    date_symbols: dict[str, set[str]] = defaultdict(set)
    date_claimed_counts: dict[str, set[int]] = defaultdict(set)
    date_target_ranks: dict[str, list[float]] = defaultdict(list)
    errors = []
    rows = 0
    eligible = 0
    with_all_features = 0
    required_rank_names = [f"rank_{name}" for name in RANK_FEATURES]
    with panel.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                errors.append(f"line {line_number}: invalid JSON: {error}")
                continue
            rows += 1
            symbol = str(row.get("symbol") or "")
            market_date = str(row.get("market_date") or "")
            key = (symbol, market_date)
            if key in seen:
                errors.append(f"line {line_number}: duplicate key {key}")
            seen.add(key)
            if symbol not in expected_candidates:
                errors.append(f"line {line_number}: unknown symbol {symbol}")
            date_symbols[market_date].add(symbol)
            claimed = int(row.get("x5_cross_sectional_coverage_count", -1))
            date_claimed_counts[market_date].add(claimed)
            if claimed < expected_minimum:
                errors.append(
                    f"line {line_number}: coverage below minimum"
                )
            entry_date = str(row.get("label_entry_market_date") or "")
            exit_date = str(row.get("label_5d_exit_market_date") or "")
            if not market_date < entry_date < exit_date:
                errors.append(f"line {line_number}: invalid label dates")
            path = row.get("label_5d_mark_to_market_path")
            if not isinstance(path, list) or len(path) != 5:
                errors.append(f"line {line_number}: path is not five rows")
            else:
                path_dates = [str(point["market_date"]) for point in path]
                if (
                    path_dates != sorted(path_dates)
                    or len(set(path_dates)) != 5
                    or path_dates[0] != entry_date
                    or path_dates[-1] != exit_date
                ):
                    errors.append(
                        f"line {line_number}: path dates mismatch"
                    )
                if not np.isclose(
                    float(path[-1]["gross_return_from_entry_pct"]),
                    float(row["label_5d_gross_return_pct"]),
                    rtol=0.0,
                    atol=1e-7,
                ):
                    errors.append(
                        f"line {line_number}: terminal path return mismatch"
                    )
            if not np.isclose(
                float(row["label_5d_net_return_pct"]),
                float(row["label_5d_gross_return_pct"])
                - float(row["round_trip_cost_pct"]),
                rtol=0.0,
                atol=1e-7,
            ):
                errors.append(f"line {line_number}: cost arithmetic mismatch")
            ranks = [row.get(name) for name in required_rank_names]
            if all(value is not None for value in ranks):
                with_all_features += 1
            for name, value in zip(required_rank_names, ranks):
                if value is not None and not 0.0 <= float(value) <= 1.0:
                    errors.append(
                        f"line {line_number}: rank out of bounds: {name}"
                    )
            target_rank = float(row["label_5d_cross_sectional_return_rank"])
            date_target_ranks[market_date].append(target_rank)
            if not 0.0 <= target_rank <= 1.0:
                errors.append(f"line {line_number}: target rank out of bounds")
            components = [
                (row.get(name), weight)
                for name, weight in TRANSPARENT_WEIGHTS.items()
            ]
            if any(value is None for value, _ in components):
                if row.get("x5_transparent_composite_score") is not None:
                    errors.append(
                        f"line {line_number}: incomplete transparent score"
                    )
                if row.get("x5_eligible") is True:
                    errors.append(
                        f"line {line_number}: eligible row lacks score inputs"
                    )
            else:
                expected_score = sum(
                    float(value) * weight
                    for value, weight in components
                )
                if not np.isclose(
                    float(row["x5_transparent_composite_score"]),
                    expected_score,
                    rtol=0.0,
                    atol=1e-10,
                ):
                    errors.append(
                        f"line {line_number}: transparent score mismatch"
                    )
            if row.get("x5_eligible") is True:
                eligible += 1
            if len(errors) >= 100:
                break

    for market_date, symbols in date_symbols.items():
        claims = date_claimed_counts[market_date]
        if claims != {len(symbols)}:
            errors.append(
                f"{market_date}: claimed coverage {claims} != {len(symbols)}"
            )
        ranks = date_target_ranks[market_date]
        if len(ranks) > 1 and (
            not np.isclose(min(ranks), 0.0, atol=1e-12)
            or not np.isclose(max(ranks), 1.0, atol=1e-12)
        ):
            errors.append(f"{market_date}: target ranks do not span 0..1")
        if len(errors) >= 100:
            break
    expected_rows = int(manifest["rows"])
    expected_dates = int(manifest["dates"])
    if rows != expected_rows:
        errors.append(f"row count {rows} != manifest {expected_rows}")
    if len(date_symbols) != expected_dates:
        errors.append(
            f"date count {len(date_symbols)} != manifest {expected_dates}"
        )
    return {
        "status": "PASS" if not errors else "FAIL",
        "research_only": True,
        "execution_enabled": False,
        "rows": rows,
        "dates": len(date_symbols),
        "unique_keys": len(seen),
        "eligible_rows": eligible,
        "rows_with_all_rank_features": with_all_features,
        "minimum_observed_cross_sectional_coverage": min(
            (len(value) for value in date_symbols.values()), default=0
        ),
        "maximum_observed_cross_sectional_coverage": max(
            (len(value) for value in date_symbols.values()), default=0
        ),
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if (
        manifest.get("status") != "complete"
        or manifest.get("panel_sha256") != sha256(args.panel)
    ):
        raise ValueError("panel manifest/hash mismatch")
    report = audit_panel(args.panel, manifest)
    report.update(
        {
            "panel": str(args.panel),
            "panel_sha256": sha256(args.panel),
            "manifest": str(args.manifest),
            "manifest_sha256": sha256(args.manifest),
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
