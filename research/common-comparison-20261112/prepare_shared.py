"""Fit-only nested information matrices. No April snapshot or label parsing."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json,hashlib,runpy,time,warnings
import numpy as np,pandas as pd,joblib
from scipy import sparse
from sklearn.preprocessing import StandardScaler,OneHotEncoder
from sklearn.model_selection import train_test_split
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parent;DEST=ROOT/'shared';PR=DEST/'private'
OLD=Path('E:/app-data/codex/outputs/is6400-validation-20261111')
KEY=['customer_unique_id','snapshot_date'];BASE=['R','F','M','average_item_rows','freight_share','recent30_orders','recent30_spend','state']
SPLITS=[20261111,20261112,20261113,20261114,20261115]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def read(p,**kw):return pd.read_csv(p,float_precision='round_trip',**kw)

def main():
 begin=time.perf_counter();PR.mkdir(parents=True,exist_ok=True)
 source=OLD/'features';spec=json.loads((source/'feature-views.json').read_text());fields=spec['views']['full-structure'];cats=spec['categorical_columns'];views=spec['logical_views']
 assert len(fields)==141 and set(fields)==set(sum(views.values(),[])) and len(sum(views.values(),[]))==141
 sources=[source/'private/october-features.csv',source/'private/january-features.csv',source/'feature-views.json',ROOT/'task_plan.md']
 helper=Path('E:/app-data/codex/outputs/is6400-rfm-weighted-2x2-20261110/run_rfm_2x2.py');code=runpy.run_path(str(helper));htr,hja=code['read_dev']();sources +=[helper,code['TEAM']/'H02_candidate_v2.zip']
 inputs={str(p):sha(p) for p in sources}
 frames=[]
 for tag,p,reference,group in [('oct',sources[0],htr,Path('E:/app-data/codex/outputs/is6400-local-round2-20261110/role-04/train_clusters.csv')),('jan',sources[1],hja,Path('E:/app-data/codex/outputs/is6400-h05-january-handoff-20261110/validation_clusters.csv'))]:
  f=read(p,usecols=KEY+['y']+fields,dtype={c:'string' for c in cats+KEY});assert not f.duplicated(KEY).any()
  z=reference[KEY+BASE+['y']].merge(f,on=KEY,how='left',sort=False,validate='one_to_one',suffixes=('_h02',''))
  assert len(z)==len(reference) and not z.y.isna().any() and z.y.eq(z.y_h02).all()
  for c in BASE:
   if c=='state':assert z[c].astype(str).eq(z[c+'_h02'].astype(str)).all()
   else:assert np.allclose(z[c],z[c+'_h02'],rtol=0,atol=1e-12),c
  f=z[KEY+['y']+fields].copy();g=read(group,dtype={KEY[0]:'string',KEY[1]:'string'});inputs[str(group)]=sha(group)
  f=f.merge(g[KEY+['cluster_id']],on=KEY,how='left',sort=False,validate='one_to_one');assert not f.cluster_id.isna().any()
  f.cluster_id=f.cluster_id.astype(int);f.y=f.y.astype(int)
  f.to_csv(PR/f'{tag}-raw.csv',index=False,lineterminator='\n');frames.append(f)
 tr,ja=frames;assert (len(tr),tr.y.sum(),len(ja),ja.y.sum())==(21160,211,29368,230)
 assert (ja.cluster_id.eq(1).sum(),ja.loc[ja.cluster_id.eq(1),'y'].sum())==(12330,90)
 summary={};source_raw_hashes={tag:sha(PR/f'{tag}-raw.csv') for tag in ['oct','jan']}
 for split_id in SPLITS:
  tick=time.perf_counter();sd=PR/f'split-{split_id}';sd.mkdir(exist_ok=True)
  fit,cal=train_test_split(np.arange(len(tr)),test_size=.2,random_state=split_id,stratify=tr.y);fit=np.sort(fit);cal=np.sort(cal)
  assert len(set(fit)&set(cal))==0 and (len(fit),int(tr.y.iloc[fit].sum()),len(cal),int(tr.y.iloc[cal].sum()))==(16928,169,4232,42)
  np.savez_compressed(sd/'indices.npz',fit=fit,cal=cal)
  matrices=[[],[],[]];lineage=[];transformers={};dims=[];base_mask=[]
  for view,columns in views.items():
   numeric=[c for c in columns if c not in cats];categorical=[c for c in columns if c in cats]
   a=tr[numeric].to_numpy(float);b=ja[numeric].to_numpy(float)
   with warnings.catch_warnings():warnings.simplefilter('ignore',RuntimeWarning);med=np.nanmedian(a[fit],axis=0)
   med=np.nan_to_num(med,nan=0.);raw_idx=[i for i,c in enumerate(numeric) if c.endswith('_lat') or c.endswith('_lng')]
   flag_idx=[i for i,c in enumerate(numeric) if c not in BASE]
   def num(v):
    missing=np.isnan(v);filled=np.where(missing,med,v);x=np.where(filled>=0,np.log1p(np.maximum(filled,0)),filled)
    x[:,raw_idx]=filled[:,raw_idx]
    return x,missing[:,flag_idx].astype(float)
   tx,tm=num(a);jx,jm=num(b);scaler=StandardScaler().fit(tx[fit]);scaled=scaler.transform(tx);js=scaler.transform(jx)
   parts=[sparse.csr_matrix(np.hstack([scaled[fit],tm[fit]])),sparse.csr_matrix(np.hstack([scaled[cal],tm[cal]])),sparse.csr_matrix(np.hstack([js,jm]))]
   names=[dict(view=view,field=c,kind='numeric',original8=c in BASE) for c in numeric]+[dict(view=view,field=numeric[i],kind='missing',original8=False) for i in flag_idx]
   encoders={}
   for category_block,rare in [([c for c in categorical if c=='state'],None),([c for c in categorical if c!='state'],20)]:
    if not category_block:continue
    at=tr[category_block].fillna('__MISSING__').astype(str);bt=ja[category_block].fillna('__MISSING__').astype(str)
    enc=OneHotEncoder(handle_unknown='ignore' if rare is None else 'infrequent_if_exist',min_frequency=rare,sparse_output=True,dtype=np.float64).fit(at.iloc[fit]);encoders['state' if rare is None else 'extra']=dict(fields=category_block,encoder=enc)
    for i,x in enumerate([at.iloc[fit],at.iloc[cal],bt]):parts[i]=sparse.hstack([parts[i],enc.transform(x)],format='csr')
    for field,count in zip(category_block,enc._n_features_outs):
     names.extend(dict(view=view,field=field,kind='onehot',original8=field=='state') for _ in range(count))
   assert len(names)==parts[0].shape[1]
   for target,arr in zip(matrices,parts):target.append(arr)
   dims.append(parts[0].shape[1]);lineage+=names;base_mask += [n['original8'] for n in names]
   transformers[view]=dict(numeric=numeric,median=med,raw_indices=raw_idx,flag_indices=flag_idx,scaler=scaler,encoders=encoders)
  base_mask=np.asarray(base_mask,dtype=bool)
  for label,blocks in zip(['fit','cal','jan'],matrices):
   x=sparse.hstack(blocks,format='csr');assert x.shape[1]==sum(dims) and np.isfinite(x.data).all();sparse.save_npz(sd/f'{label}.npz',x)
  np.save(sd/'base8-mask.npy',base_mask);joblib.dump(transformers,sd/'transformers.joblib',compress=3);dump(sd/'lineage.json',lineage)
  # Independent original8 transformer check, including all Jan unknown categories.
  numeric=BASE[:-1];bsc=StandardScaler().fit(np.log1p(tr[numeric].iloc[fit]));bohe=OneHotEncoder(handle_unknown='ignore',sparse_output=False).fit(tr[['state']].iloc[fit].astype(str));maxdiff=0.
  for label,fr in [('fit',tr.iloc[fit]),('cal',tr.iloc[cal]),('jan',ja)]:
   expected=np.hstack([bsc.transform(np.log1p(fr[numeric])),bohe.transform(fr[['state']].astype(str))]);actual=sparse.load_npz(sd/f'{label}.npz')[:,base_mask].toarray();assert expected.shape==actual.shape
   diff=float(np.max(np.abs(expected-actual)));assert diff<1e-11;maxdiff=max(maxdiff,diff)
  fitkey='\n'.join(sorted(tr.customer_unique_id.iloc[fit].astype(str)))+'\n'
  summary[str(split_id)]={'dims':dims,'dimension':sum(dims),'base8_encoded':int(base_mask.sum()),'fit_n':len(fit),'fit_positive':int(tr.y.iloc[fit].sum()),'cal_n':len(cal),'cal_positive':int(tr.y.iloc[cal].sum()),'fit_key_sha256':hashlib.sha256(fitkey.encode()).hexdigest(),'original8_transform_max_abs_diff':maxdiff,'seconds':time.perf_counter()-tick,'files':{p.name:sha(p) for p in sorted(sd.iterdir()) if p.is_file()}}
  print('PREPARED',split_id,summary[str(split_id)]['dimension'],maxdiff,flush=True)
 config={'schema_version':1,'status':'frozen_shared_data_ready','split_ids':SPLITS,'model_seeds':[2026,2027,2028],'information':['base8','full141'],'families':['weightedLR','unweightedLR','encodedCatBoost','mean','column-gate','AE','nativeCatBoost'],'view_order':list(views),'raw_fields':fields,'categorical_fields':cats,'base_fields':BASE,'sources':inputs,'raw_data_sha256':source_raw_hashes,'splits':summary,'Jan_n':29368,'Jan_positive':230,'H05_long_group':1,'long_n':12330,'long_positive':90,'global_K':2937,'long_K':79,'April_snapshot_rows_parsed':0,'new_April_scores':0,'elapsed_seconds':time.perf_counter()-begin}
 dump(DEST/'data-manifest.json',config)
 for p,h in inputs.items():assert sha(p)==h
 print('SHARED_READY',config['elapsed_seconds'],flush=True)

if __name__=='__main__':
 with threadpool_limits(2):main()
