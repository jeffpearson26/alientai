"""Evaluate a reviewed contextual-options payload from local daily candles only."""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path
from typing import Any

def five_day_return(path: Path, as_of: str) -> float | None:
    if not path.exists(): return None
    with path.open(newline="",encoding="utf-8-sig") as f: rows=list(csv.DictReader(f))
    dates=[str(r.get("date") or "") for r in rows]
    if as_of not in dates: return None
    i=dates.index(as_of)
    if i+5>=len(rows): return None
    a,b=float(rows[i].get("close") or 0),float(rows[i+5].get("close") or 0)
    return ((b/a)-1)*100 if a>0 and b>0 else None

def evaluate(payload: dict[str,Any], daily_dir: Path) -> dict[str,Any]:
    if payload.get("execution_enabled") is not False or not payload.get("research_only"):
        raise ValueError("payload must be explicitly research-only and execution-disabled")
    done=[]; pending=[]
    for item in payload.get("candidates") or []:
        value=five_day_return(daily_dir/f"{item['symbol']}_schwab_1d_max.csv",str(item["market_date"]))
        (pending if value is None else done).append({**item, "outcome_status":"PENDING_CANDLE_COVERAGE" if value is None else "COMPLETE", **({} if value is None else {"realized_return_pct":value})})
    return {"status":"complete","research_only":True,"execution_enabled":False,"completed":len(done),"pending":len(pending),"mean_realized_return_pct":sum(x["realized_return_pct"] for x in done)/len(done) if done else None,"records":done,"pending_records":pending}
def main()->None:
 p=argparse.ArgumentParser();p.add_argument("--payload",type=Path,required=True);p.add_argument("--daily-dir",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 r=evaluate(json.loads(a.payload.read_text(encoding="utf-8")),a.daily_dir);a.output.write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8");print(json.dumps({k:v for k,v in r.items() if k not in {"records","pending_records"}},indent=2))
if __name__=="__main__":main()
