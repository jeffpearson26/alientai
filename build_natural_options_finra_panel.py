"""Exact-key research join for base labels, options, and FINRA features."""
from __future__ import annotations
import argparse,json
from pathlib import Path
def read(p):
 with open(p,encoding='utf8') as f:
  for x in f:
   if x.strip(): yield json.loads(x)
def key(r): return str(r['symbol']).upper(),str(r['market_date'])
def main():
 p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--options',required=True);p.add_argument('--finra',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 opts={key(r):r for r in read(a.options)}; finra={key(r):r for r in read(a.finra)}
 if len(opts)!=len(finra): raise ValueError('options and FINRA tables do not have identical unique keys')
 out=[]
 for r in read(a.base):
  k=key(r)
  if k in opts: out.append({**r,**{x:y for x,y in opts[k].items() if x not in {'symbol','market_date'}},**{x:y for x,y in finra[k].items() if x not in {'symbol','market_date'}}})
 if len(out)!=len(opts): raise ValueError(f'row loss: joined {len(out)} of {len(opts)} option keys')
 Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in out),encoding='utf8');print(json.dumps({'status':'complete','research_only':True,'execution_enabled':False,'rows':len(out)},indent=2))
if __name__=='__main__':main()
