"""Chronological research-only ablation: options/technical with versus without FINRA."""
from __future__ import annotations
import argparse,json
from datetime import date,timedelta
from pathlib import Path
import lightgbm as lgb
import numpy as np
BASE=["technical_rsi_2","technical_rsi_14","technical_atr14_pct","technical_adx14","technical_bollinger_width_pct","technical_relative_volume_10_vs_20","technical_macd_histogram_pct","option_call_volume","option_put_call_volume_ratio","option_call_open_interest","option_put_call_open_interest_ratio","option_volume_open_interest_ratio","option_near_money_call_iv"]
FINRA=["short_interest_shares","short_interest_age_calendar_days","short_interest_available"]
def read(p): return [json.loads(x) for x in Path(p).read_text(encoding='utf8').splitlines() if x]
def matrix(rows,names): return np.array([[float(r.get(n) or 0) for n in names] for r in rows],dtype=np.float32)
def score(rows,pred):
 by={}
 for r,s in zip(rows,pred): by.setdefault(r['market_date'],[]).append((float(s),r))
 picked=[max(v,key=lambda x:x[0])[1] for v in by.values()]
 net=np.array([float(x['label_forward_return_5d_pct'])-.25 for x in picked]);return {"signals":len(picked),"mean_net_return_pct":round(float(net.mean()),6),"median_net_return_pct":round(float(np.median(net)),6),"win_rate_after_cost":round(float((net>0).mean()),6)}
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True);a=p.parse_args(); rows=read(a.input);dates=sorted({r['market_date'] for r in rows});a1=dates[int(len(dates)*.6)];a2=dates[int(len(dates)*.8)]; e1=(date.fromisoformat(a1)+timedelta(days=7)).isoformat();e2=(date.fromisoformat(a2)+timedelta(days=7)).isoformat();train=[r for r in rows if r['market_date']<a1];val=[r for r in rows if e1<=r['market_date']<a2];test=[r for r in rows if r['market_date']>=e2]
 y=lambda x:np.array([float(r['label_forward_return_5d_pct'])>=10 for r in x],dtype=np.int32)
 report={"status":"complete","research_only":True,"execution_enabled":False,"split":{"train_before":a1,"validation_before":a2,"embargo_calendar_days":7,"test_rows":len(test)},"models":{}}
 for name,features in {"technical_options":BASE,"technical_options_finra":BASE+FINRA}.items():
  model=lgb.train({"objective":"binary","metric":"binary_logloss","verbosity":-1,"seed":42,"num_leaves":15,"learning_rate":.05},lgb.Dataset(matrix(train,features),label=y(train)),num_boost_round=100,valid_sets=[lgb.Dataset(matrix(val,features),label=y(val))],callbacks=[lgb.early_stopping(10,verbose=False)])
  report['models'][name]={"features":features,"test_daily_top_1":score(test,model.predict(matrix(test,features),num_iteration=model.best_iteration))}
 Path(a.output).write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
