from __future__ import annotations

"""Build one research-only all-market screened snapshot for model-3 clone."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import lightgbm as lgb

from alientai_v2.research.us_smallcap_range_volume_clone import (
    active_stock_symbols,
    parse_utc,
    read_jsonl,
    score_candidates,
    screen_universe,
    sha256,
    validate_clone_contract,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--listing-status", type=Path, required=True)
    parser.add_argument("--technical-snapshot", type=Path, required=True)
    parser.add_argument("--market-cap-snapshot", type=Path, required=True)
    parser.add_argument("--decision-date", required=True)
    parser.add_argument("--decision-cutoff-utc", required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--training-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    validate_clone_contract(
        contract,
        model_path=args.model,
        report_path=args.training_report,
    )
    cutoff = parse_utc(args.decision_cutoff_utc)
    report = json.loads(args.training_report.read_text(encoding="utf-8"))
    listing = active_stock_symbols(
        args.listing_status,
        allowed_exchanges=contract["universe_screen"].get("allowed_exchanges"),
    )
    eligible, counts = screen_universe(
        listing,
        read_jsonl(args.technical_snapshot),
        read_jsonl(args.market_cap_snapshot),
        decision_date=args.decision_date,
        cutoff_utc=cutoff,
        provider=str(contract["source_provider"]),
        maximum_market_cap_usd=float(
            contract["universe_screen"]["maximum_market_cap_usd_exclusive"]
        ),
        maximum_price_usd=float(
            contract["universe_screen"]["maximum_close_usd_exclusive"]
        ),
        minimum_relative_volume_20=float(
            contract["universe_screen"]["minimum_relative_volume_20"]
        ),
        minimum_atr14_pct=float(
            contract["universe_screen"]["minimum_atr14_pct"]
        ),
    )
    model = lgb.Booster(model_file=str(args.model))
    scored, selected = score_candidates(
        eligible,
        model=model,
        feature_names=report["feature_names"],
        score_cutoff=float(contract["locked_score_cutoff"]),
        maximum_selections=int(contract["maximum_selections"]),
    )
    result = {
        "status": "NEW_OBSERVATION" if selected else "ABSTENTION",
        "model_id": contract["model_id"],
        "source_model_id": contract["source_model_id"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "decision_date": args.decision_date,
        "decision_cutoff_utc": cutoff.isoformat(),
        "horizon_sessions": 5,
        "screen_counts": counts,
        "eligible_universe": scored,
        "selections": selected,
        "artifacts": {
            "contract_sha256": sha256(args.contract),
            "listing_status_sha256": sha256(args.listing_status),
            "technical_snapshot_sha256": sha256(args.technical_snapshot),
            "market_cap_snapshot_sha256": sha256(args.market_cap_snapshot),
            "model_sha256": sha256(args.model),
            "training_report_sha256": sha256(args.training_report),
        },
        "research_only": True,
        "execution_decision": "AVOID",
        "evidence_inherited_from_source_model": False,
    }
    if args.output.resolve().drive.upper() != "D:":
        raise ValueError("snapshot output must be stored on D:")
    if args.output.exists():
        raise ValueError("snapshot output already exists; never overwrite")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
