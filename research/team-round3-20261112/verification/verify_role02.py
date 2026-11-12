from pathlib import Path
from zipfile import ZipFile
import pandas as pd,numpy as np,json,math
from sklearn.metrics import roc_auc_score
O=Path('E:/app-data/codex/outputs/is6400-round3-team-intake-20261112');E=O/'private/extracted';D2=E/'role02/Round3_role02';D3=E/'role03/Round3_role03_prediction_v1';K=['customer_unique_id','snapshot_date']
with ZipFile('E:/app-data/codex/outputs/is6400-team-intake-20261110/H02_candidate_v2.zip') as z:
 def rd(n):
  p=next(p for p in z.namelist() if p.endswith('/'+n) or p==n)
  with z.open(p) as v:return pd.read_csv(v,dtype={'customer_unique_id':'string'})
 f=rd('snapshot_features.csv');l=rd('snapshot_labels.csv')
a=pd.read_csv(E/'role01/Round3_role01_time_v1/snapshot-asof-features.csv',dtype={'customer_unique_id':'string'})
g=pd.concat([pd.read_csv(D3/n,dtype={'customer_unique_id':'string'}) for n in ['training_clusters.csv','validation_clusters.csv']])
x=f.merge(a,on=K,validate='one_to_one').merge(l[K+['y']],on=K,validate='one_to_one').merge(g[K+['cluster_id']],on=K,validate='one_to_one')
v={'C01':x.delivered_known_n/x.F,'C02':x.F-x.delivered_known_n,'C03':np.log1p(x.delivery_days_mean.clip(lower=0)),'C04':x.delivery_days_mean.isna().astype(float),'C05':np.log1p(x.delivered_known_n),'C06':x.delivered_known_n.gt(0).astype(float),'C07':x.late_delivery_share,'C08':x.review_score_mean,'C09':x.review_score_mean.isna().astype(float),'C10':x.low_review_share,'C11':x.review_known_n/x.F,'C12':x.review_known_n/x.delivered_known_n.replace(0,np.nan),'C13':x.review_known_n.gt(0).astype(float),'C14':np.log1p(x.review_known_n)}
source=pd.read_csv(D2/'training-feature-evidence.csv',dtype={'scope':str});rows=[]
def stats(vals,y):
 m=np.isfinite(vals);u=vals[m];z=y[m];p=u[z==1];n=u[z==0];n1=len(p);n0=len(n)
 pooled=np.sqrt(((n1-1)*p.var(ddof=1)+(n0-1)*n.var(ddof=1))/(n1+n0-2));d=(p.mean()-n.mean())/pooled if pooled>0 else np.nan
 se=math.sqrt((n1+n0)/(n1*n0)+d*d/(2*(n1+n0-2))) if np.isfinite(d) and min(n1,n0)>=2 else np.nan
 return dict(cohens_d=d,auc=roc_auc_score(z,u),mean_pos=p.mean(),mean_neg=n.mean(),median_pos=np.median(p),median_neg=np.median(n),nonmissing=int(m.sum()),missing=int((~m).sum()),positives_nonmissing=n1,negatives_nonmissing=n0,corrected_d_se=se,corrected_d_ci_lo=d-1.96*se,corrected_d_ci_hi=d+1.96*se)
for _,r in source.iterrows():
 mask=x.snapshot_date.eq('2017-10-01')
 if r.scope!='ALL':mask&=x.cluster_id.eq(int(r.scope))
 z=x.loc[mask,'y'].to_numpy(int);values=v[r.candidate_id].loc[mask].to_numpy(float);s=stats(values,z)
 for field in ['cohens_d','auc','mean_pos','mean_neg','median_pos','median_neg','nonmissing','missing','positives_nonmissing','negatives_nonmissing']:
  assert np.isclose(float(r[field]),s[field],atol=1e-10,rtol=1e-10,equal_nan=True),(r.candidate_id,r.scope,field)
 out=r.to_dict();out.update(s);out['ci_sample_size_corrected']=not np.isclose(r.d_se,s['corrected_d_se'],equal_nan=True);out['d_ci_note']='same approximate d interval formula, finite positive/negative counts substituted; descriptive, not multiplicity-adjusted'
 rows.append(out)
out=pd.DataFrame(rows);out.to_csv(O/'audit/role02-evidence-recomputed-corrected.csv',index=False)
direction=pd.read_csv(D2/'tables/r3_january_direction.csv');dr=[]
for _,r in direction.iterrows():
 mask=x.snapshot_date.eq('2018-01-01');s=stats(v[r.candidate_id].loc[mask].to_numpy(float),x.loc[mask,'y'].to_numpy(int))
 assert np.isclose(r.january_d_all,s['cohens_d'],atol=1e-10,rtol=1e-10,equal_nan=True)
 dr.append({'candidate_id':r.candidate_id,'october_d':r.october_d_all,'january_d':r.january_d_all,'same_sign':bool(np.sign(r.october_d_all)==np.sign(r.january_d_all))})
pd.DataFrame(dr).to_csv(O/'audit/role02-direction-readback.csv',index=False)
receipt={'status':'POINT_ESTIMATES_PASS_CI_SUPPORT_COUNTS_CORRECTED_IN_DERIVATIVE','evidence_rows_point_recomputed':len(out),'ci_rows_using_larger_full_cohort_n':int(out.ci_sample_size_corrected.sum()),'january_direction_rows':len(dr),'sign_flips':int(sum(not v['same_sign'] for v in dr)),'source_files_unchanged':True,'original_private_candidate_table_not_supplied':True,'no_claim_original_private_sha_matched':True,'new_model_fits':0}
(O/'audit/role02-readback.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(receipt,ensure_ascii=False))
