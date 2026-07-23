"""Normalize official FINRA files with conservative point-in-time availability."""
from __future__ import annotations
import argparse,csv,json,re
from datetime import datetime,timezone
from pathlib import Path
from finra_short_interest_calendar import publication_date
from import_finra_short_interest import normalize,number
PATTERN=re.compile(r"^shrt(\d{8})\.csv$",re.I)
def main()->None:
 p=argparse.ArgumentParser();p.add_argument("--input-dir",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 out=[]; files=[]
 for path in sorted(a.input_dir.glob("shrt*.csv")):
  m=PATTERN.match(path.name)
  if not m: continue
  settlement=datetime.strptime(m.group(1),"%Y%m%d").date(); published=publication_date(settlement)
  available=f"{published.isoformat()}T23:59:59Z" # conservative when intraday publication time is unavailable
  with path.open(newline="",encoding="utf-8-sig") as h:
   for raw in csv.DictReader(h,delimiter="|"):
    row=normalize(raw,symbol_column="symbolCode",shares_column="currentShortPositionQuantity",settlement_date=settlement.isoformat(),publication_timestamp_utc=available)
    if row:
     row.update({'short_interest_previous_shares':number(raw.get('previousShortPositionQuantity')),'short_interest_average_daily_volume':number(raw.get('averageDailyVolumeQuantity')),'short_interest_days_to_cover':number(raw.get('daysToCoverQuantity')),'short_interest_change_percent':number(raw.get('changePercent'))})
     out.append(row)
  files.append({"file":path.name,"settlement_date":settlement.isoformat(),"available_at_utc":available})
 if not files: raise ValueError("no FINRA short-interest files found")
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text("".join(json.dumps(x,sort_keys=True)+"\n" for x in out),encoding="utf-8")
 print(json.dumps({"status":"complete","research_only":True,"execution_enabled":False,"files":len(files),"rows":len(out),"availability_policy":"publication date at 23:59:59Z when intraday time is unavailable"},indent=2))
if __name__=="__main__":main()
