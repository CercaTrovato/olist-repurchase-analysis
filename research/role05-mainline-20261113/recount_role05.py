"""Independently recount Role05 aggregates from previously verified R3 row inputs.
No fitting, model selection, April prediction or source-package script execution.
"""
from pathlib import Path
from zipfile import ZipFile
import json,math,hashlib
import pandas as pd,numpy as np
O=Path(__file__).resolve().parent;A=O/'audit';A.mkdir(exist_ok=True)
M=O/'private/extracted/Round3_role05_11.13';R3=Path('E:/app-data/codex/outputs/is6400-round3-team-intake-20261112/private/extracted/role03/Round3_role03_prediction_v1');K=['customer_unique_id','snapshot_date']
def rd(p):return pd.read_csv(p,encoding='utf-8-sig',dtype={'customer_unique_id':'string'})
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
f=rd(R3/'january-predictions.csv');g=rd(R3/'group-model-predictions.csv');v=rd(R3/'validation_clusters.csv')
with ZipFile('E:/app-data/codex/outputs/is6400-team-intake-20261110/H02_candidate_v2.zip') as z:
 n=next(n for n in z.namelist() if n.endswith('/snapshot_labels.csv'))
 with z.open(n) as fh:labels=pd.read_csv(fh,dtype={'customer_unique_id':'string'})
jan=labels[labels.snapshot_date.eq('2018-01-01')]
joins=[]
for name,d in [('Predictions',f),('Group predictions',g),('Clusters',v)]:
 assert not d.duplicated(K).any()
 j=jan[K+['y']].merge(d,on=K,how='outer',validate='one_to_one',indicator=True,suffixes=('_label','_prediction'))
 missing=int(j['_merge'].ne('both').sum());assert missing==0
 mismatches=int(j.y_label.ne(j.y_prediction).sum()) if 'y_prediction' in j else None
 assert mismatches is None or mismatches==0
 joins.append({'table':name,'rows':len(d),'duplicate_keys':int(d.duplicated(K).sum()),'unmatched_keys':missing,'label_mismatches':mismatches})
f=f.merge(v[K+['cluster_id']],on=K,validate='one_to_one')
methods={'F0 Weighted (Main)':(f,'F0_base_weighted_score'),'F0 Unweighted':(f,'F0_base_unweighted_score'),'B +Cluster_id':(g,'B_global_with_cluster_score'),'C Segmented Fallback':(g,'C_segmented_group2_global_fallback_score')}
def top(d,col,k):return d.iloc[np.lexsort((d.customer_unique_id.astype(str).to_numpy(),-d[col].to_numpy()))[:k]]
cap=[];grp=[];topids={}
for name,(d,col) in methods.items():
 for pct in [.05,.1,.2]:
  k=math.ceil(len(d)*pct);t=top(d,col,k);h=int(t.y.sum());cap.append({'Model':name,'Top_Fraction':pct,'Capacity':k,'Hits':h,'Precision':h/k,'Recall':h/230,'N':len(d),'Positives':int(d.y.sum())})
  if pct==.1:topids[name]=set(t.customer_unique_id)
 for group,pool in d.groupby('cluster_id'):
  ch=pool[pool.customer_unique_id.isin(topids[name])];n=len(ch);h=int(ch.y.sum());p=int(pool.y.sum())
  grp.append({'Model':name,'Cluster_ID':int(group),'Pool_Size':len(pool),'Positives':p,'Selected':n,'Hits':h,'Precision':h/n if n else None,'Recall':h/p if p else None})
pd.DataFrame(cap).to_csv(A/'capacity-all-models.csv',index=False);pd.DataFrame(grp).to_csv(A/'groups-all-models.csv',index=False);pd.DataFrame(joins).to_csv(A/'dynamic-join-audit.csv',index=False)
given=rd(M/'output/comparison-round3.csv');checks=[]
for _,r in given.iterrows():
 if r.Model=='H06 Legacy':
  checks.append({'table':'comparison','key':r.Model,'status':'INHERITED_NOT_NEW_REPLAY','note':'46 is historical reference; not a new H06 row-level replay.'});continue
 actual=next(v for v in cap if v['Model']==r.Model and v['Capacity']==int(r.Capacity))
 assert actual['Hits']==r.Hits and round(actual['Precision'],4)==r.Precision
 checks.append({'table':'comparison','key':r.Model,'status':'MATCH'})
given_groups=rd(M/'output/group-comparison.csv')
for _,r in given_groups.iterrows():
 actual=next(v for v in grp if v['Model']=='F0 Weighted (Main)' and v['Cluster_ID']==r.Cluster_ID)
 for n in ['Pool_Size','Positives','Selected','Hits']:assert actual[n]==r[n]
 for n in ['Precision','Recall']:assert round(actual[n],4)==r[n]
 checks.append({'table':'group','key':str(int(r.Cluster_ID)),'status':'MATCH'})
ymap=dict(zip(f.customer_unique_id,f.y));base=topids['F0 Weighted (Main)'];paired=[]
for name,other in [('F0 vs Unweighted','F0 Unweighted'),('F0 vs B (+Cluster)','B +Cluster_id'),('F0 vs C (Segmented)','C Segmented Fallback')]:
 old=topids[other];common=base&old;added=base-old;dropped=old-base
 paired.append({'Comparison':name,'Common_Selected':len(common),'Common_Hits':int(sum(ymap[x] for x in common)),'Added':len(added),'Added_Hits':int(sum(ymap[x] for x in added)),'Dropped':len(dropped),'Dropped_Hits':int(sum(ymap[x] for x in dropped)),'Net_Gain':int(sum(ymap[x] for x in added)-sum(ymap[x] for x in dropped))})
pg=rd(M/'output/paired-list-changes.csv')
for r in paired:
 one=pg[pg.Comparison.eq(r['Comparison'])].iloc[0]
 for k,val in r.items():assert one[k]==val
 checks.append({'table':'paired','key':r['Comparison'],'status':'MATCH'})
pd.DataFrame(paired).to_csv(A/'paired-list-recomputed.csv',index=False)
decomp=[]
for group in range(3):
 a=next(r for r in grp if r['Model']=='F0 Weighted (Main)' and r['Cluster_ID']==group);b=next(r for r in grp if r['Model']=='F0 Unweighted' and r['Cluster_ID']==group)
 decomp.append({'Cluster_ID':group,'Unweighted_Selected':b['Selected'],'Weighted_Selected':a['Selected'],'Delta_Selected':a['Selected']-b['Selected'],'Unweighted_Hits':b['Hits'],'Weighted_Hits':a['Hits'],'Delta_Hits':a['Hits']-b['Hits']})
pd.DataFrame(decomp).to_csv(A/'weighting-group-decomposition.csv',index=False)
long=[]
for name,(d,col) in methods.items():
 pool=d[d.cluster_id.eq(1)];t=top(pool,col,79);long.append({'Model':name,'group_pool':len(pool),'K':len(t),'Hits':int(t.y.sum())})
pd.DataFrame(long).to_csv(A/'fixed-long79.csv',index=False)
unc=[]
for name in methods:
 h=next(v['Hits'] for v in cap if v['Model']==name and v['Capacity']==2937);n=2937
 unc.append({'Model':name,'Hits':h,'Source_errorbar_halfwidth':1.96*math.sqrt(h*(1-h/n)/n),'Independent_binomial_count_halfwidth_illustration':1.96*math.sqrt(h*(1-h/n)),'ratio_sqrt_n':math.sqrt(n),'Current_adopted_confidence_interval':False,'note':'Dimensional diagnostic only. No sampling model declared for fixed seen lists; do not replace with binomial illustration as endorsed CI.'})
pd.DataFrame(unc).to_csv(A/'uncertainty-formula-diagnostic.csv',index=False)
audit=rd(M/'output/join_audit.csv')
assert int(audit[audit.Table.eq('Labels')].Rows.iloc[0])==len(labels)
assert int(audit[audit.Table.eq('Predictions')].Rows.iloc[0])==len(f)
assert int(audit[audit.Table.eq('Clusters')].Rows.iloc[0])==len(v)
pd.DataFrame(checks).to_csv(A/'numerical-checks.csv',index=False)
receipt={'status':'CORE_TABLES_MATCH_WITH_METHODOLOGY_AND_PROVENANCE_CORRECTIONS','rows':len(f),'positive_count':int(f.y.sum()),'top10_comparison_rows_matched':4,'inherited_legacy_row':1,'group_rows_matched':3,'paired_rows_matched':3,'capacity_rows_derived_all_four_models':len(cap),'group_rows_derived_all_four_models':len(grp),'new_model_fits':0,'new_candidate_searches':0,'new_april_predictions':0,'new_uncertainty_estimates_adopted':0,'dynamic_join_checks':joins,'input_sources_sha256':{str(p):sha(p) for p in [R3/'january-predictions.csv',R3/'group-model-predictions.csv',R3/'validation_clusters.csv',M/'scripts/run.py']},'limits':['Role05 did not supply raw inputs/hash-run logs; current equality is independent recount using held verified R3 inputs.','Reproducible=True and Missing_Merge=0 in Role05 generator are constants, not executable pass criteria.','Original uncertainty image excluded.','Role05 F0 adoption recommendation is member opinion; user selected local research line for final report.']}
(A/'readback.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:receipt[k] for k in ['status','top10_comparison_rows_matched','group_rows_matched','paired_rows_matched','capacity_rows_derived_all_four_models','new_model_fits']},ensure_ascii=False))
