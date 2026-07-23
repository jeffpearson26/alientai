"""Create a non-executing, date-bounded shadow snapshot from a frozen LightGBM model."""
from __future__ import annotations
import argparse, json
from datetime import date, timedelta
from pathlib import Path
import lightgbm as lgb
import numpy as np
from audit_transformer_candidate_coverage import load_candles
from train_v2_lightgbm_5day_sp500_from_supabase import build_bar_features, summarize_sequence


def record(symbol: str, as_of_date: str, score: float) -> dict:
    return {"symbol": symbol, "as_of_date": as_of_date, "model_score": score,
            "horizon_trading_sessions": 5,
            "outcome_not_due_before": (date.fromisoformat(as_of_date) + timedelta(days=9)).isoformat(),
            "research_only": True, "execution_enabled": False, "decision": "SHADOW_JOURNAL_ONLY"}


def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument("--model",type=Path,required=True); p.add_argument("--daily-dir",type=Path,required=True)
    p.add_argument("--symbols-file",type=Path,required=True); p.add_argument("--as-of-date",required=True); p.add_argument("--minimum-score",type=float,required=True); p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if not 0 < a.minimum_score < 1: raise ValueError("minimum score must be in (0, 1)")
    model=lgb.Booster(model_file=str(a.model)); symbols=[x.strip().upper() for x in a.symbols_file.read_text().splitlines() if x.strip()]
    selected=[]; fresh=stale=0
    for symbol in symbols:
        path=a.daily_dir/f"{symbol}_schwab_1d_max.csv"
        if not path.exists(): stale+=1; continue
        candles=[c for c in load_candles(path) if str(c.get("date") or "") <= a.as_of_date]
        if not candles or str(candles[-1].get("date")) != a.as_of_date: stale+=1; continue
        # Latest features use at most a 200-session lookback plus the 60-session
        # summary window.  Avoid recomputing decades of irrelevant history.
        bars=build_bar_features(candles[-260:])
        if bars.shape[0] < 60: stale+=1; continue
        fresh+=1; score=float(model.predict(summarize_sequence(bars[-60:]).reshape(1,-1))[0])
        if score >= a.minimum_score: selected.append(record(symbol,a.as_of_date,score))
    if not fresh: raise ValueError("no fresh symbols for requested date")
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text("".join(json.dumps(x,sort_keys=True)+"\n" for x in selected),encoding="utf-8")
    print(json.dumps({"status":"complete","research_only":True,"execution_enabled":False,"fresh_symbols":fresh,"stale_or_missing":stale,"selected":len(selected)},indent=2))
if __name__ == "__main__": main()
