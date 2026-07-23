from __future__ import annotations

"""Build leakage-safe call-volume history from archived option chains."""
import argparse, json
from pathlib import Path
from alientai_v2.research.historical_call_evaluator import chain_path, load_chain
from alientai_v2.research.unusual_call_activity import unusual_call_features

def dates(root: Path, symbol: str) -> list[str]:
    return sorted(folder.name for folder in (root / "2026").glob("2026-*") if (folder / f"{symbol}.json.gz").exists())

def totals(chain):
    calls=[row for row in chain if str(row.get("type") or "").lower()=="call"]
    return sum(float(row.get("volume") or 0) for row in calls), sum(float(row.get("open_interest") or 0) for row in calls)

def main():
    p=argparse.ArgumentParser()
    target = p.add_mutually_exclusive_group(required=True)
    target.add_argument("--target")
    target.add_argument("--all-dates", action="store_true")
    p.add_argument("--symbols-jsonl",type=Path,required=True)
    p.add_argument("--chains",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    rows=[]
    for line in a.symbols_jsonl.read_text(encoding="utf-8").splitlines():
        symbol=json.loads(line)["symbol"]
        for day in dates(a.chains,symbol):
            if a.target and day>a.target: break
            path=chain_path(a.chains,symbol,day)
            if path.exists():
                volume, oi=totals(load_chain(path)); rows.append({"symbol":symbol,"market_date":day,"option_call_volume":volume,"option_call_open_interest":oi})
    features=unusual_call_features(rows)
    if a.target:
        features=[row for row in features if row["market_date"]==a.target]
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text("".join(json.dumps(row,sort_keys=True)+"\n" for row in features),encoding="utf-8")
    print(json.dumps({"status":"complete","target":a.target or "all_dates","rows":len(features),"unusual":sum(bool(r.get('call_volume_unusual')) for r in features)},indent=2))
if __name__=="__main__": main()
