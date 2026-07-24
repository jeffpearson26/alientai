"""Evaluate a reviewed contextual-options payload from local daily candles only."""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path
from typing import Any

def observed_session_returns(path: Path, as_of: str, maximum_horizon: int = 5) -> dict[int, float]:
    if not path.exists(): return {}
    with path.open(newline="",encoding="utf-8-sig") as f: rows=list(csv.DictReader(f))
    dates=[str(r.get("date") or "") for r in rows]
    if as_of not in dates: return {}
    i=dates.index(as_of)
    entry=float(rows[i].get("close") or 0)
    if entry <= 0: return {}
    observed = {}
    for horizon in range(1, maximum_horizon + 1):
        if i + horizon >= len(rows):
            break
        exit_price=float(rows[i+horizon].get("close") or 0)
        if exit_price > 0:
            observed[horizon] = ((exit_price / entry) - 1) * 100
    return observed


def five_day_return(path: Path, as_of: str) -> float | None:
    observed = observed_session_returns(path, as_of)
    return observed.get(5) if observed else None

def evaluate(payload: dict[str,Any], daily_dir: Path) -> dict[str,Any]:
    if payload.get("execution_enabled") is not False or not payload.get("research_only"):
        raise ValueError("payload must be explicitly research-only and execution-disabled")
    done=[]; pending=[]
    for item in payload.get("candidates") or []:
        observed=observed_session_returns(daily_dir/f"{item['symbol']}_schwab_1d_max.csv",str(item["market_date"])) or {}
        value=observed.get(5)
        record={**item, "observed_future_sessions":len(observed)}
        if observed:
            record["interim_session_returns_pct"]={str(key): round(value, 6) for key, value in observed.items()}
        if value is None:
            record["outcome_status"]="PENDING_CANDLE_COVERAGE"
            pending.append(record)
        else:
            record.update({"outcome_status":"COMPLETE", "realized_return_pct":value})
            done.append(record)
    return {"status":"complete","research_only":True,"execution_enabled":False,"source":"schwab_local_daily_csv","completed":len(done),"pending":len(pending),"mean_realized_return_pct":sum(x["realized_return_pct"] for x in done)/len(done) if done else None,"records":done,"pending_records":pending}
def main()->None:
 p=argparse.ArgumentParser();p.add_argument("--payload",type=Path,required=True);p.add_argument("--daily-dir",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 r=evaluate(json.loads(a.payload.read_text(encoding="utf-8")),a.daily_dir);a.output.write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8");print(json.dumps({k:v for k,v in r.items() if k not in {"records","pending_records"}},indent=2))
if __name__=="__main__":main()
