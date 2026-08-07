from __future__ import annotations

"""Independently audit the frozen full-archive technical panel and shards."""

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from alientai_v2.research.multiresolution_cross_sectional import (
    CONTEXT_FEATURES,
    DAILY_FEATURES,
    FIVE_MINUTE_FEATURES,
)
from build_full_archive_multiresolution_technical_panel import (
    HORIZONS,
    MIN_COVERAGE_FRACTION,
    MODEL_FAMILY,
    ROUND_TRIP_COST_PCT,
    read_symbols,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _artifact_ok(artifact: dict[str, Any]) -> tuple[bool, pd.DataFrame]:
    path = Path(str(artifact["path"]))
    if not path.is_file() or sha256(path) != artifact.get("sha256"):
        return False, pd.DataFrame()
    frame = pd.read_csv(path)
    return (
        len(frame) == int(artifact["rows"])
        and frame["market_date"].nunique() == int(artifact["dates"]),
        frame,
    )


def audit(panel_root: Path) -> dict[str, Any]:
    manifest_path = panel_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    panel_artifact = manifest["artifacts"]["panel"]
    panel_ok, frame = _artifact_ok(panel_artifact)
    if not panel_ok:
        errors.append("full panel artifact/hash/count mismatch")
    if (
        manifest.get("status") != "complete"
        or manifest.get("model_family") != MODEL_FAMILY
        or manifest.get("candidate_count") != 101
        or manifest.get("context_only") != ["QQQ", "SPY"]
        or manifest.get("feature_sets")
        != ["daily_only", "daily_plus_5minute"]
        or float(manifest.get("round_trip_cost_pct", -1))
        != ROUND_TRIP_COST_PCT
        or manifest.get("daily_volume_policy") != "raw point-in-time volume"
        or manifest.get("research_only") is not True
        or manifest.get("execution_decision") != "AVOID"
    ):
        errors.append("manifest frozen contract mismatch")
    daily_audit = Path(str(manifest["sources"]["daily_audit_path"]))
    intraday_audit = Path(str(manifest["sources"]["intraday"]["audit_path"]))
    for label, path, expected_hash in (
        (
            "daily audit",
            daily_audit,
            manifest["sources"]["daily_audit_sha256"],
        ),
        (
            "intraday audit",
            intraday_audit,
            manifest["sources"]["intraday"]["audit_sha256"],
        ),
    ):
        if (
            not path.is_file()
            or sha256(path) != expected_hash
            or not json.loads(path.read_text(encoding="utf-8")).get(
                "integrity_pass"
            )
        ):
            errors.append(f"{label} identity/pass mismatch")
    spy_audit = Path(str(manifest["sources"]["spy_daily_audit_path"]))
    if (
        not spy_audit.is_file()
        or sha256(spy_audit)
        != manifest["sources"]["spy_daily_audit_sha256"]
        or json.loads(spy_audit.read_text(encoding="utf-8")).get("status")
        != "PASS"
    ):
        errors.append("SPY daily audit identity/pass mismatch")
    required = {
        "symbol",
        "market_date",
        "decision_available_at_et",
        "round_trip_cost_pct",
        *DAILY_FEATURES,
        *FIVE_MINUTE_FEATURES,
        *CONTEXT_FEATURES,
        *(f"rank_{name}" for name in [*DAILY_FEATURES, *FIVE_MINUTE_FEATURES]),
    }
    if not required.issubset(frame.columns):
        errors.append(f"panel missing columns: {sorted(required - set(frame.columns))}")
    excluded_tokens = ("option", "news", "headline", "fundamental", "premarket")
    excluded = [
        column
        for column in frame.columns
        if any(token in column.casefold() for token in excluded_tokens)
    ]
    if excluded:
        errors.append(f"excluded feature columns present: {excluded}")
    if frame.duplicated(["market_date", "symbol"]).any():
        errors.append("duplicate panel keys")
    if set(frame["symbol"]) & {"QQQ", "SPY"}:
        errors.append("context ETF entered candidate rows")
    if set(frame["symbol"]) != set(
        read_symbols(Path(manifest["sources"]["symbols_path"]))
    ):
        errors.append("panel candidate universe mismatch")
    if not np.allclose(
        pd.to_numeric(frame["round_trip_cost_pct"], errors="coerce"),
        ROUND_TRIP_COST_PCT,
    ):
        errors.append("cost is not exactly 0.25%")
    availability = pd.to_datetime(
        frame["decision_available_at_et"],
        utc=True,
        errors="coerce",
    )
    eastern = availability.dt.tz_convert("America/New_York")
    if (
        availability.isna().any()
        or (eastern.dt.strftime("%Y-%m-%d") != frame["market_date"]).any()
        or (eastern.dt.hour != 20).any()
        or (eastern.dt.minute != 0).any()
    ):
        errors.append("decision timestamp contract mismatch")
    numeric_features = [
        *DAILY_FEATURES,
        *FIVE_MINUTE_FEATURES,
        *CONTEXT_FEATURES,
    ]
    if (
        frame[numeric_features]
        .apply(pd.to_numeric, errors="coerce")
        .isna()
        .any()
        .any()
    ):
        errors.append("core technical/context feature is missing")
    rank_columns = [
        f"rank_{name}" for name in [*DAILY_FEATURES, *FIVE_MINUTE_FEATURES]
    ]
    ranks = frame[rank_columns].apply(pd.to_numeric, errors="coerce")
    if ranks.isna().any().any() or ((ranks < 0) | (ranks > 1)).any().any():
        errors.append("feature rank is missing or outside 0-1")
    counts = frame.groupby("market_date")["symbol"].nunique()
    minimum = int(math.ceil(101 * MIN_COVERAGE_FRACTION))
    if counts.empty or (counts < minimum).any():
        errors.append("cross-sectional coverage is below 95%")
    for horizon in HORIZONS:
        prefix = f"label_{horizon}d"
        entry = pd.to_numeric(frame[f"{prefix}_entry_open"], errors="coerce")
        exit_price = pd.to_numeric(
            frame[f"{prefix}_exit_close"],
            errors="coerce",
        )
        gross = pd.to_numeric(
            frame[f"{prefix}_gross_return_pct"],
            errors="coerce",
        )
        net = pd.to_numeric(frame[f"{prefix}_net_return_pct"], errors="coerce")
        recomputed = (exit_price / entry - 1.0) * 100.0
        if (
            entry.isna().any()
            or exit_price.isna().any()
            or (entry <= 0).any()
            or (exit_price <= 0).any()
            or not np.allclose(gross, recomputed, atol=1e-10, rtol=1e-10)
            or not np.allclose(
                net,
                recomputed - ROUND_TRIP_COST_PCT,
                atol=1e-10,
                rtol=1e-10,
            )
        ):
            errors.append(f"{horizon}-session return label mismatch")
        decision = frame["market_date"].astype(str)
        entry_date = frame[f"{prefix}_entry_date"].astype(str)
        exit_date = frame[f"{prefix}_exit_date"].astype(str)
        if ((entry_date <= decision) | (exit_date < entry_date)).any():
            errors.append(f"{horizon}-session label chronology mismatch")
        expected_rank = frame.groupby("market_date")[
            f"{prefix}_net_return_pct"
        ].rank(method="average", pct=True)
        actual_rank = pd.to_numeric(
            frame[f"{prefix}_cross_sectional_rank"],
            errors="coerce",
        )
        if not np.allclose(expected_rank, actual_rank, atol=1e-12, rtol=1e-12):
            errors.append(f"{horizon}-session target-rank mismatch")
        partition = manifest["artifacts"]["partitions"][str(horizon)]
        development_ok, development = _artifact_ok(partition["development"])
        test_ok, test = _artifact_ok(partition["sealed_test"])
        split = partition["split_dates"]
        if (
            not development_ok
            or not test_ok
            or set(development["market_date"].astype(str))
            != set(split["development"])
            or set(test["market_date"].astype(str)) != set(split["sealed_test"])
            or set(split["development"]) & set(split["pre_test_embargo"])
            or set(split["development"]) & set(split["sealed_test"])
            or set(split["pre_test_embargo"]) & set(split["sealed_test"])
            or len(split["pre_test_embargo"]) != horizon
        ):
            errors.append(f"{horizon}-session sealed partition mismatch")
    return {
        "status": "PASS" if not errors else "FAIL",
        "integrity_pass": not errors,
        "errors": errors,
        "model_family": MODEL_FAMILY,
        "panel_path": panel_artifact["path"],
        "panel_sha256": panel_artifact["sha256"],
        "rows": len(frame),
        "dates": int(frame["market_date"].nunique()),
        "symbols": int(frame["symbol"].nunique()),
        "minimum_symbols_per_date": int(counts.min()) if not counts.empty else 0,
        "maximum_symbols_per_date": int(counts.max()) if not counts.empty else 0,
        "manifest_sha256": sha256(manifest_path),
        "research_only": True,
        "execution_decision": "AVOID",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-root", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.panel_root)
    output = args.panel_root / "content_audit.json"
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2), flush=True)
    if not result["integrity_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
