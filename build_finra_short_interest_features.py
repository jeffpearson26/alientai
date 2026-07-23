"""Join FINRA short-interest shares to a panel without future leakage."""
from __future__ import annotations
import argparse,json
from bisect import bisect_right
from collections import defaultdict
from pathlib import Path
from typing import Any
def read(path:Path):
 with path.open(encoding='utf8') as f:
  for line in f:
   if line.strip(): yield json.loads(line)
def build(panel, short):
 by=defaultdict(list)
 for r in short: by[str(r['symbol']).upper()].append((str(r['available_at_utc'])[:10],r))
 for v in by.values(): v.sort(key=lambda x:x[0])
 out=[]
 for r in panel:
  symbol=str(r['symbol']).upper(); d=str(r['market_date']); v=by.get(symbol,[]); i=bisect_right([x[0] for x in v],d)-1
  item={'symbol':symbol,'market_date':d,'short_interest_available':i>=0,'research_only':True}
  if i>=0:
   available,row=v[i]; item.update({'short_interest_shares':row['short_interest_shares'],'short_interest_settlement_date':row['settlement_date'],'short_interest_available_at_utc':row['available_at_utc'],'short_interest_age_calendar_days':( __import__('datetime').date.fromisoformat(d)-__import__('datetime').date.fromisoformat(available)).days,**{n:row.get(n) for n in ('short_interest_previous_shares','short_interest_average_daily_volume','short_interest_days_to_cover','short_interest_change_percent')},'short_interest_shares_to_average_volume_ratio':(row['short_interest_shares']/row['short_interest_average_daily_volume'] if row.get('short_interest_average_daily_volume') else None)})
  out.append(item)
 return out
def main():
 p=argparse.ArgumentParser();p.add_argument('--panel',type=Path,required=True);p.add_argument('--short-interest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 rows=build(read(a.panel),read(a.short_interest));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in rows),encoding='utf8');print(json.dumps({'status':'complete','research_only':True,'execution_enabled':False,'rows':len(rows),'available':sum(x['short_interest_available'] for x in rows)},indent=2))
if __name__=='__main__':main()
