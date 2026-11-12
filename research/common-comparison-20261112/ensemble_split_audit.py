"""Supplement: score the same frozen mean-calibrated-probability ensemble in all 5 splits.

No fit/new bootstrap. Resolves mean(metric) versus metric(mean probability) when
describing training/calibration perturbation stability. Original summaries stay intact.
"""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json,hashlib,itertools
import numpy as np,pandas as pd
from sklearn.metrics import log_loss,brier_score_loss,average_precision_score,roc_auc_score
import eval_harness as common
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 paths=[p for stage in ['classical','neural'] for p in (ROOT/stage).glob('*-record.json')];assert len(paths)==155
 records=[json.loads(p.read_text()) for p in paths];frame=common.load_frames(20261111)['jan'];y=frame.y.to_numpy(int);g=frame.cluster_id.to_numpy(int);key=frame.customer_unique_id.to_numpy(str)
 grouped={}
 for r in records:grouped.setdefault((r['split_id'],r['information'],r['family']),[]).append(r)
 rows=[];lists={};sources={}
 for (split,info,family),rr in sorted(grouped.items()):
  rr=sorted(rr,key=lambda r:-1 if r['seed'] is None else r['seed']);expected=1 if family in ['weightedLR','unweightedLR'] else 3;assert len(rr)==expected
  arrays=[]
  for r in rr:
   p=ROOT/r['score_file'];assert sha(p)==r['score_sha256'];arrays.append(np.load(p)['jan_calibrated']);sources[str(p.relative_to(ROOT))]=sha(p)
  p=np.mean(np.stack(arrays),axis=0);rank=np.lexsort((key,-p))
  for scope,mask,k in [('all',np.ones(len(y),bool),2937),('long',g==1,79)]:
   selected=rank[mask[rank]][:k];lists[(split,info,family,scope)]=set(map(int,selected));yy=y[mask];pp=p[mask]
   rows.append(dict(split_id=split,information=info,family=family,model=info+'::'+family,scope=scope,n_models=len(rr),n=len(yy),events=int(yy.sum()),logloss=log_loss(yy,pp),brier=brier_score_loss(yy,pp),AP=average_precision_score(yy,pp),AUC=roc_auc_score(yy,pp),k=k,hits=int(y[selected].sum()),long_seats=int((g[selected]==1).sum()),long_hits=int(y[selected][g[selected]==1].sum())))
 df=pd.DataFrame(rows);assert len(df)==130
 # The supplementary computation must reproduce the canonical statistical module.
 point=pd.read_csv(ROOT/'statistics/canonical-ensemble-metrics.csv');cap=pd.read_csv(ROOT/'statistics/canonical-ensemble-capacities.csv')
 for r in df[df.split_id.eq(20261111)].to_dict('records'):
  sc='all' if r['scope']=='all' else 'cluster_1_long';old=point[(point.model==r['model'])&(point.scope==sc)].iloc[0]
  for metric in ['logloss','brier','AP','AUC']:assert np.isclose(r[metric],old[metric],atol=1e-12,rtol=1e-12)
  policy='global2937' if r['scope']=='all' else 'long79';oldc=cap[(cap.model==r['model'])&(cap.policy==policy)].iloc[0];assert r['hits']==oldc.hits
 df.to_csv(ROOT/'ensemble-five-split-results.csv',index=False)
 comparisons=[]
 for (info,family,scope),v in df.groupby(['information','family','scope']):
  baseline=df[(df.family=='weightedLR')&(df.information=='base8')&(df.scope==scope)].set_index('split_id')
  v=v.set_index('split_id');assert len(v)==5
  for metric in ['hits','logloss','brier','AP','AUC']:
   delta=v[metric]-baseline[metric];benefit=-delta if metric in ['logloss','brier'] else delta;tol=0 if metric=='hits' else 1e-12
   comparisons.append(dict(information=info,family=family,scope=scope,metric=metric,reference='base8::weightedLR',n_overlapping_splits=5,differences=';'.join(f'{x:.12g}' for x in delta),mean_difference=float(delta.mean()),min_difference=float(delta.min()),max_difference=float(delta.max()),wins=int((benefit>tol).sum()),ties=int((benefit.abs()<=tol).sum()),losses=int((benefit < -tol).sum()),mean_metric=float(v[metric].mean()),interpretation='same mean(calibrated p) system across overlapping training/calibration splits; not new periods'))
 pd.DataFrame(comparisons).to_csv(ROOT/'ensemble-five-split-directions.csv',index=False)
 stability=[]
 for info,family,scope in sorted({(i,f,s) for _,i,f,s in lists}):
  for a,b in itertools.combinations(common.manifest()['split_ids'],2):
   u=lists[(a,info,family,scope)];v=lists[(b,info,family,scope)];stability.append(dict(information=info,family=family,scope=scope,split_a=a,split_b=b,jaccard=len(u&v)/len(u|v),replacements=len(u-v)))
 pd.DataFrame(stability).to_csv(ROOT/'ensemble-five-split-selection-stability.csv',index=False)
 record={'status':'PASS','supplement_scope':'same frozen ensemble rule in five splits; after full results to distinguish metric(mean p) from mean(metric); no fit or new bootstrap','canonical_rows_reproduced':26,'ensemble_metric_rows':130,'direction_rows':len(comparisons),'selection_pair_rows':len(stability),'source_sha256':sources,'code_sha256':sha(Path(__file__))}
 common.dump(ROOT/'ensemble-split-audit-verification.json',record)
 print(pd.DataFrame(comparisons).query("information=='full141' and metric=='hits'")[['family','scope','differences','wins','ties','losses','mean_metric']].to_string(index=False))
if __name__=='__main__':main()
