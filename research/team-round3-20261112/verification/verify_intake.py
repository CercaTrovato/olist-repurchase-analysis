from pathlib import Path
from zipfile import ZipFile
import json,hashlib,math,re
import pandas as pd
import numpy as np
from sklearn.metrics import average_precision_score,roc_auc_score
from sklearn.model_selection import StratifiedKFold
from scipy.stats import norm
O=Path('E:/app-data/codex/outputs/is6400-round3-team-intake-20261112');E=O/'private/extracted'
D={r:next((E/r).iterdir()) for r in ['role01','role02','role03','role04']}
A=O/'audit';A.mkdir(exist_ok=True)
KEY=['customer_unique_id','snapshot_date']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def csv(p,**kw):return pd.read_csv(p,encoding='utf-8-sig',**kw)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def savej(v,n): (A/n).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
checks=[]
for role,p in D.items():
 name='ROUND3_CHECKSUMS.sha256' if role=='role03' else 'CHECKSUMS.sha256'
 for line in (p/name).read_text(encoding='utf-8-sig').splitlines():
  if not line.strip():continue
  h,n=line.split(None,1);n=n.strip().lstrip('*');q=p/n
  checks.append({'role':role,'file':n,'exists':q.is_file(),'sha256_match':q.is_file() and sha(q)==h,'expected':h,'actual':sha(q) if q.is_file() else None})
pd.DataFrame(checks).to_csv(A/'package-checksums.csv',index=False)
source=Path('E:/app-data/codex/outputs/is6400-team-intake-20261110/H02_candidate_v2.zip')
assert sha(source)=='3b58f4e493e825a76ccc569f205cfa0db5d27e22b13389c3c00ff958a316419a'
with ZipFile(source) as z:
 def zcsv(n):
  path=next(v for v in z.namelist() if v.endswith('/'+n) or v==n)
  with z.open(path) as f:return pd.read_csv(f,dtype={'customer_unique_id':'string'})
 f=zcsv('snapshot_features.csv');l=zcsv('snapshot_labels.csv')
assert not f.duplicated(KEY).any() and not l.duplicated(KEY).any()
base=f.merge(l[KEY+['y']],on=KEY,validate='one_to_one')
asof=csv(D['role01']/'snapshot-asof-features.csv',dtype={'customer_unique_id':'string'})
assert not asof.duplicated(KEY).any()
joined=base.merge(asof,on=KEY,how='outer',validate='one_to_one',indicator=True)
assert joined['_merge'].eq('both').all()
source_checks={'H02_archive_sha256':sha(source),'h02_rows':len(base),'asof_rows':len(asof),'asof_duplicate_keys':int(asof.duplicated(KEY).sum()),'source_date_counts':base.groupby('snapshot_date').agg(n=('y','size'),positives=('y','sum')).reset_index().to_dict('records'),'external_role01_csv_matches':{n:sha(O/'private/incoming'/n)==sha(D['role01']/n) for n in ['field-time-audit.csv','time-window-audit.csv']}}
savej(source_checks,'source-alignment.json')
gtrain=csv(D['role03']/'training_clusters.csv',dtype={'customer_unique_id':'string'});gval=csv(D['role03']/'validation_clusters.csv',dtype={'customer_unique_id':'string'})
oldtrain=csv(Path('E:/app-data/codex/outputs/is6400-local-round2-20261110/role-04/train_clusters.csv'),dtype={'customer_unique_id':'string'})
oldval=csv(Path('E:/app-data/codex/outputs/is6400-h05-january-handoff-20261110/validation_clusters.csv'),dtype={'customer_unique_id':'string'})
group_checks=[]
for date,new,old in [('2017-10-01',gtrain,oldtrain),('2018-01-01',gval,oldval)]:
 old=old.rename(columns={'cluster':'cluster_id'})
 j=new.merge(old[KEY+['cluster_id']],on=KEY,how='outer',validate='one_to_one',suffixes=('_new','_old'),indicator=True)
 group_checks.append({'date':date,'rows':len(new),'duplicates':int(new.duplicated(KEY).sum()),'unmatched':int(j['_merge'].ne('both').sum()),'mismatched_labels':int(j.cluster_id_new.ne(j.cluster_id_old).sum())})
savej(group_checks,'group-label-alignment.json')
pred=csv(D['role03']/'january-predictions.csv',dtype={'customer_unique_id':'string'})
gp=csv(D['role03']/'group-model-predictions.csv',dtype={'customer_unique_id':'string'})
jan=base[base.snapshot_date.eq('2018-01-01')]
assert len(jan)==29368 and jan.y.sum()==230
for frame in [pred,gp]:
 assert not frame.duplicated(KEY).any()
 j=frame.merge(jan[KEY+['y']],on=KEY,how='outer',validate='one_to_one',suffixes=('_got','_ref'),indicator=True)
 assert j['_merge'].eq('both').all() and j.y_got.eq(j.y_ref).all()
pred=pred.merge(gval[KEY+['cluster_id']],on=KEY,validate='one_to_one')
rows=[];group_rows=[];replays=[]
for table,frame,summary,key in [('basic',pred,csv(D['role03']/'january-comparison.csv'),'method'),('group',gp,csv(D['role03']/'group-model-comparison.csv'),'method')]:
 for method in [c[:-6] for c in frame if c.endswith('_score')]:
  s=frame[method+'_score'].to_numpy();ids=frame.customer_unique_id.astype(str).to_numpy();y=frame.y.to_numpy(int)
  assert np.isfinite(s).all() and ((s>=0)&(s<=1)).all()
  ap=average_precision_score(y,s);auc=roc_auc_score(y,s)
  for frac in [.05,.1,.2]:
   k=math.ceil(frac*len(y));order=np.lexsort((ids,-s));selected=np.zeros(len(y),bool);selected[order[:k]]=True
   stored=frame[method+f'_selected_{int(frac*100)}'].to_numpy(bool)
   row={'table':table,'method':method,'top_fraction':frac,'N':len(y),'positive_count':int(y.sum()),'K':k,'hits':int(y[selected].sum()),'precision':float(y[selected].sum()/k),'recall':float(y[selected].sum()/y.sum()),'AP':float(ap),'ROC_AUC':float(auc)}
   given=summary[(summary[key]==method)&np.isclose(summary.top_fraction,frac)].iloc[0]
   maxerr=max(abs(float(given[n])-row[n]) for n in ['N','positive_count','K','hits','precision','recall','AP','ROC_AUC'])
   assert np.array_equal(selected,stored) and maxerr<1e-10,(method,frac,maxerr)
   rows.append(row);replays.append({'table':table,'method':method,'fraction':frac,'selection_mismatches':int((selected!=stored).sum()),'max_metric_diff':maxerr})
   for g in range(3):
    mask=frame.cluster_id.eq(g).to_numpy();v={'table':table,'method':method,'fraction':frac,'cluster_id':g,'N':int(mask.sum()),'positive_count':int(y[mask].sum()),'selected':int((selected&mask).sum()),'hits':int(y[selected&mask].sum())}
    if table=='group':
     for n,original in [('N',f'cluster_{g}_N'),('selected',f'cluster_{g}_selected'),('hits',f'cluster_{g}_hits')]:assert int(given[original])==v[n]
    group_rows.append(v)
   lm=frame.cluster_id.eq(1).to_numpy();lo=np.lexsort((ids[lm],-s[lm]));long_hits=int(y[lm][lo[:79]].sum())
   if frac==.1:row['long79_hits']=long_hits
pd.DataFrame(rows).to_csv(A/'january-recomputed.csv',index=False);pd.DataFrame(group_rows).to_csv(A/'january-groups-recomputed.csv',index=False);pd.DataFrame(replays).to_csv(A/'prediction-replay.csv',index=False)
baseline_replay=pred[KEY+['F0_base_weighted_score']].merge(gp[KEY+['F0_global_weighted_score']],on=KEY,validate='one_to_one')
savej({'max_abs_diff_two_F0_tables':float(abs(baseline_replay.F0_base_weighted_score-baseline_replay.F0_global_weighted_score).max()),'january_prediction_tables':2,'rows_each':len(pred),'summary_rows':len(rows),'future_labels_used_only_for_evaluation':True,'new_model_fits':0},'prediction-readback.json')
cv=csv(D['role03']/'cv-fold-results.csv');gcv=csv(D['role03']/'group-cv-fold-results.csv')
train=base[base.snapshot_date.eq('2017-10-01')].reset_index(drop=True)
foldmap={i:(len(vi),int(train.y.iloc[vi].sum())) for i,(_,vi) in enumerate(StratifiedKFold(5,shuffle=True,random_state=2026).split(train,train.y),1)}
cvchecks=[]
for name,tab,summary,keys in [('basic',cv,csv(D['role03']/'cv-summary.csv'),['variant','weighted']),('group',gcv,csv(D['role03']/'group-cv-summary.csv'),['method'])]:
 for _,v in tab.iterrows():assert int(v.N)==foldmap[int(v.fold)][0] and int(v.positive_count)==foldmap[int(v.fold)][1]
 for key,z in tab.groupby(keys):
  key=key if isinstance(key,tuple) else (key,);s=summary
  for col,val in zip(keys,key):s=s[s[col]==val]
  assert len(s)==1 and len(z)==5
  for dest,sourcecol,agg in [('cv_hits_mean','hits','mean'),('cv_hits_std','hits','std'),('cv_precision_mean','precision','mean'),('cv_recall_mean','recall','mean'),('cv_ap_mean','AP','mean'),('cv_ap_std','AP','std'),('cv_roc_auc_mean','ROC_AUC','mean')]:
   if dest not in s:continue
   val=float(getattr(z[sourcecol],agg)());diff=abs(val-float(s.iloc[0][dest]));assert diff<1e-10
  cvchecks.append({'table':name,'variant':str(key),'folds':len(z),'summary_matches':True})
savej({'checks':cvchecks,'basic_rows':len(cv),'group_rows':len(gcv),'fold_pool_counts':foldmap,'new_model_fits':0,'not_claiming_cv_model_predictions_replayed':True},'cv-summary-readback.json')
prof=csv(D['role04']/'results/profile-summary.csv')
trueprof=jan.merge(gval[KEY+['cluster_id']],on=KEY,validate='one_to_one').groupby('cluster_id').agg(n=('y','size'),positives=('y','sum')).reset_index()
j=prof.merge(trueprof,on='cluster_id',suffixes=('_r4','_ref'))
assert j.n_r4.eq(j.n_ref).all() and j.positives_r4.eq(j.positives_ref).all()
baseline=next(r for r in rows if r['table']=='group' and r['method']=='F0_global_weighted' and r['top_fraction']==.1)
current=pd.DataFrame([r for r in group_rows if r['table']=='group' and r['method']=='F0_global_weighted' and r['fraction']==.1])
refreshed=prof.merge(current[['cluster_id','selected','hits']],on='cluster_id',validate='one_to_one').rename(columns={'selected':'r3_F0_selected','hits':'r3_F0_hits'})
refreshed['prediction_version']='Round3_role03_prediction_v1/F0_global_weighted'
refreshed.to_csv(A/'current-profile-summary.csv',index=False)
sample=csv(D['role04']/'results/sample-size-scenarios.csv');samplecheck=[]
for _,v in sample.iterrows():
 p0=v.baseline;p1=p0*(1+v.relative_lift);pm=(p0+p1)/2
 n=math.ceil((norm.ppf(.975)*math.sqrt(2*pm*(1-pm))+norm.ppf(.8)*math.sqrt(p0*(1-p0)+p1*(1-p1)))**2/(p1-p0)**2)
 assert n==int(v.n_per_arm)
 samplecheck.append({'relative_lift':float(v.relative_lift),'n_per_arm':n,'total':2*n,'matches':True})
savej({'group_profile_denominators_match':True,'legacy_selected_total':int(prof.legacy_selected.sum()),'legacy_hits_total':int(prof.legacy_hits.sum()),'new_selected_total':int(refreshed.r3_F0_selected.sum()),'new_hits_total':int(refreshed.r3_F0_hits.sum()),'sample_size':samplecheck,'trial_not_executed':True},'role04-readback.json')
role2spec=read(D['role02']/'feature-spec.json');r3meta=read(D['role03']/'run-metadata.json')
gap={'role02_groups':{g:[v['field'] for v in fields] for g,fields in role2spec['groups'].items()},'role02_retained_flags':role2spec['retained_flags'],'role03_variants':r3meta['variants'],'same_feature_sets':False,'role03_includes_conditional_late_delivery_share':'late_delivery_share' in r3meta['variants']['F1_delivery'],'role02_rejects_late_delivery_share':True,'not_evidence_role02_groups_failed':True}
savej(gap,'feature-handoff-gap.json')
summary={'status':'CORE_AGGREGATE_READBACK_PASS_WITH_EXPLICIT_SOURCE_GAPS','package_checks':len(checks),'checksum_mismatches':[c for c in checks if not c['sha256_match']],'h02_and_asof_rows':len(joined),'prediction_summary_rows_recomputed':len(rows),'group_slice_rows_recomputed':len(group_rows),'group_alignment':group_checks,'role02_group_integration_pending':True,'role04_stale_prediction_columns_replaced_in_derivative_only':True,'new_model_fits':0,'new_april_predictions':0}
savej(summary,'readback-summary.json')
print(json.dumps(summary,ensure_ascii=False,indent=2))
