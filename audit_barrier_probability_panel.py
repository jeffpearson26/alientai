from __future__ import annotations

"""Independently audit the barrier-probability panel and its source paths."""

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from alientai_v2.research.barrier_probability_model import (
    FEATURE_LOOKBACK,
    FEATURE_NAMES,
    adjusted_daily_candles,
    resolve_barrier,
    technical_features,
)


STAGES = (
    "train",
    "fit_validation",
    "calibration",
    "policy_validation",
    "sealed_test",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}:{line_number}: invalid JSON"
                ) from exc


def close(left: Any, right: Any, tolerance: float = 1e-9) -> bool:
    return math.isclose(
        float(left),
        float(right),
        rel_tol=tolerance,
        abs_tol=tolerance,
    )


def audit(panel_dir: Path) -> dict[str, Any]:
    errors: list[str] = []
    manifest_path = panel_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "complete":
        errors.append("panel manifest is not complete")
    if not manifest.get("research_only") or manifest.get("execution_enabled"):
        errors.append("panel is not research-only")
    if tuple(manifest.get("feature_names") or []) != FEATURE_NAMES:
        errors.append("feature contract mismatch")
    if int(manifest.get("feature_lookback_sessions", -1)) != FEATURE_LOOKBACK:
        errors.append("feature lookback mismatch")

    source_candles: dict[str, list[dict[str, Any]]] = {}
    date_indices: dict[str, dict[str, int]] = {}
    source_symbol_aliases = {
        str(key).upper(): str(value).upper()
        for key, value in (manifest.get("source_symbol_aliases") or {}).items()
    }
    for symbol in manifest.get("symbols") or []:
        record = (manifest.get("source_files") or {}).get(symbol) or {}
        path = Path(str(record.get("path") or ""))
        if not path.is_file():
            errors.append(f"{symbol}: source file missing")
            continue
        if sha256(path) != record.get("sha256"):
            errors.append(f"{symbol}: source file hash mismatch")
            continue
        source_manifest = record.get("source_manifest_path")
        if source_manifest:
            source_manifest_path = Path(source_manifest)
            if (
                not source_manifest_path.is_file()
                or sha256(source_manifest_path)
                != record.get("source_manifest_sha256")
            ):
                errors.append(f"{symbol}: source manifest hash mismatch")
                continue
        try:
            candles = adjusted_daily_candles(
                path,
                source_symbol_aliases.get(symbol, symbol),
            )
        except Exception as exc:
            errors.append(f"{symbol}: source content invalid: {exc}")
            continue
        source_candles[symbol] = candles
        date_indices[symbol] = {
            str(row["market_date"]): index
            for index, row in enumerate(candles)
        }

    keys: set[tuple[str, str]] = set()
    stage_dates: dict[str, set[str]] = {stage: set() for stage in STAGES}
    stage_rows: Counter[str] = Counter()
    outcomes: Counter[str] = Counter()
    feature_samples = 0
    label_rows_verified = 0
    for stage in STAGES:
        partition = (manifest.get("partitions") or {}).get(stage) or {}
        path = Path(str(partition.get("path") or ""))
        if not path.is_file():
            errors.append(f"{stage}: partition missing")
            continue
        if sha256(path) != partition.get("sha256"):
            errors.append(f"{stage}: partition hash mismatch")
            continue
        stage_limit = str(partition.get("label_information_must_end_by") or "")
        for row_number, row in enumerate(read_jsonl(path), 1):
            stage_rows[stage] += 1
            symbol = str(row.get("symbol") or "")
            market_date = str(row.get("market_date") or "")
            key = (symbol, market_date)
            if key in keys:
                errors.append(f"duplicate row key {key}")
                continue
            keys.add(key)
            stage_dates[stage].add(market_date)
            if row.get("model_id") != manifest.get("model_id"):
                errors.append(f"{stage}:{row_number}: model ID mismatch")
            if (
                not row.get("research_only")
                or row.get("execution_decision") != "AVOID"
            ):
                errors.append(f"{stage}:{row_number}: execution guard mismatch")
            if str(row.get("label_information_end_date") or "") > stage_limit:
                errors.append(f"{stage}:{row_number}: label crosses stage")
            if not (
                market_date
                < str(row.get("entry_market_date") or "")
                <= str(row.get("label_information_end_date") or "")
            ):
                errors.append(f"{stage}:{row_number}: invalid date order")
            lower_label = row.get("label_lower_bound")
            upper_label = row.get("label_upper_bound")
            if (
                lower_label not in (0, 1)
                or upper_label not in (0, 1)
                or int(lower_label) > int(upper_label)
            ):
                errors.append(f"{stage}:{row_number}: invalid probability labels")
            values = [row.get(name) for name in FEATURE_NAMES]
            if any(
                value is None or not math.isfinite(float(value))
                for value in values
            ):
                errors.append(f"{stage}:{row_number}: invalid feature")

            candles = source_candles.get(symbol)
            index = date_indices.get(symbol, {}).get(market_date)
            if candles is None or index is None:
                errors.append(f"{stage}:{row_number}: source key missing")
                continue
            expected = resolve_barrier(
                candles,
                index,
                upper_pct=float(manifest["upper_barrier_pct"]) / 100.0,
                lower_pct=float(manifest["lower_barrier_pct"]) / 100.0,
                horizon_sessions=int(manifest["maximum_horizon_sessions"]),
            )
            for name in (
                "outcome_status",
                "entry_market_date",
                "label_information_end_date",
                "label_resolution_session",
                "label_lower_bound",
                "label_upper_bound",
                "label_conditional_unambiguous",
            ):
                if row.get(name) != expected.get(name):
                    errors.append(
                        f"{stage}:{row_number}: label mismatch for {name}"
                    )
                    break
            for name in (
                "entry_price",
                "upper_barrier_price",
                "lower_barrier_price",
            ):
                if not close(row.get(name), expected.get(name)):
                    errors.append(
                        f"{stage}:{row_number}: price mismatch for {name}"
                    )
                    break
            label_rows_verified += 1
            outcomes[str(row["outcome_status"])] += 1

            if row_number == 1 or row_number % 251 == 0:
                if index + 1 < FEATURE_LOOKBACK:
                    errors.append(
                        f"{stage}:{row_number}: insufficient feature history"
                    )
                    continue
                expected_features = technical_features(
                    candles[index + 1 - FEATURE_LOOKBACK : index + 1]
                )
                for name in FEATURE_NAMES:
                    if not close(
                        row.get(name),
                        expected_features[name],
                        tolerance=1e-8,
                    ):
                        errors.append(
                            f"{stage}:{row_number}: feature mismatch for {name}"
                        )
                        break
                feature_samples += 1

        if stage_rows[stage] != int(partition.get("rows", -1)):
            errors.append(f"{stage}: row count mismatch")
        if stage_dates[stage]:
            if min(stage_dates[stage]) < str(
                partition.get("first_decision_date")
            ):
                errors.append(f"{stage}: date begins before contract")
            if max(stage_dates[stage]) > str(
                partition.get("last_decision_date")
            ):
                errors.append(f"{stage}: date ends after contract")

    ordered_stages = [stage for stage in STAGES if stage_dates[stage]]
    for left, right in zip(ordered_stages, ordered_stages[1:]):
        if max(stage_dates[left]) >= min(stage_dates[right]):
            errors.append(f"stage chronology overlaps: {left} and {right}")

    result = {
        "status": "PASS" if not errors else "FAIL",
        "integrity_pass": not errors,
        "research_only": True,
        "execution_enabled": False,
        "model_id": manifest.get("model_id"),
        "manifest_path": str(manifest_path.resolve()),
        "manifest_sha256": sha256(manifest_path),
        "symbols_expected": int(manifest.get("symbol_count", 0)),
        "symbols_source_verified": len(source_candles),
        "rows_verified": label_rows_verified,
        "feature_samples_recomputed": feature_samples,
        "partition_rows": dict(stage_rows),
        "outcomes": dict(outcomes),
        "errors": errors[:100],
        "error_count": len(errors),
        "sealed_test_note": (
            "content integrity was audited without model scoring or policy "
            "selection; the trainer remains forbidden to load this partition "
            "unless policy validation passes"
        ),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.panel_dir)
    output = args.output or args.panel_dir / "content_audit.json"
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "rows_verified": result["rows_verified"],
                "feature_samples_recomputed": (
                    result["feature_samples_recomputed"]
                ),
                "errors": result["errors"],
                "output": str(output),
            },
            indent=2,
        )
    )
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
