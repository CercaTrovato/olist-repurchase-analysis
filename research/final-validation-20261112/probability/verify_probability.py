"""Independent saved-model and full metric replay. This file never fits."""
import sys,os
sys.dont_write_bytecode=True
os.environ.setdefault('OMP_NUM_THREADS','2')
os.environ.setdefault('MKL_NUM_THREADS','2')
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
import joblib
from scipy import sparse
from scipy.special import expit
from catboost import CatBoostClassifier
from sklearn.metrics import log_loss,brier_score_loss,average_precision_score,roc_auc_score

ROOT=Path(__file__).resolve().parent
KEY=['customer_unique_id','snapshot_date'];PARTS=['fit','cal','eval']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
def main():
    mf=ROOT/'probability-manifest.json';m=json.loads(mf.read_text());assert m['status'] in ['AWAITING_REPLAY','READY']
    freeze=json.loads((ROOT/'input-freeze.json').read_text())
    for p,h in freeze['source_files'].items():assert sha(p)==h,(p,'changed source')
    data=json.loads((ROOT.parent/'data/data-manifest.json').read_text());cats=data['categorical_fields'];fields=data['raw_fields'];base=data['base_fields']
    records=json.loads((ROOT/'model-records.json').read_text());modelchecks=[];recomputed=[];primarychecks=[];bindiffs=[]
    for cell,desc in m['cells'].items():
        cd=Path(desc['directory']);frames={p:pd.read_csv(ROOT.parent/f'data/private/cells/{cell}/{p}.csv',dtype={c:'string' for c in KEY+cats},float_precision='round_trip') for p in PARTS}
        prim={p:pd.read_csv(cd/f'primary-{p}-probabilities.csv',dtype={c:'string' for c in KEY},float_precision='round_trip') for p in PARTS}
        assert sha(desc['primary_eval_path'])==desc['primary_eval_sha256']
        values={};cb=[]
        for record in [r for r in records if r['cell']==cell]:
            d=cd/record['runid'];family=record['family'];saved=np.load(d/'scores.npz');cal=json.loads((d/'calibration.json').read_text())
            for p,h in record['files'].items():assert sha(p)==h
            if family in ['weightedLR','unweightedLR']:
                model=joblib.load(d/'model.joblib')
                if record['reuse']:x={p:sparse.load_npz(d/f'{p}-legacy-input.npz') for p in PARTS}
                else:
                    t=joblib.load(cd/'lr-transform.joblib');x={}
                    for p,f in frames.items():
                        x[p]=sparse.hstack([sparse.csr_matrix(t['scaler'].transform(np.log1p(f[t['numeric']].to_numpy(float)))),t['encoder'].transform(f[['state']].fillna('__MISSING__').astype(str))],format='csr')
                logits={p:np.asarray(model.decision_function(x[p]),float) for p in PARTS}
            else:
                model=CatBoostClassifier();model.load_model(str(d/'model.cbm'))
                t=json.loads((d/'transform.json' if record['reuse'] else cd/'cb-transform.json').read_text());nums=[c for c in fields if c not in cats];logits={}
                for p,f in frames.items():
                    a=f[fields].copy()
                    for c in cats:a[c]=a[c].fillna('__MISSING__').astype(str)
                    a[nums]=a[nums].astype(float).fillna(pd.Series(t['numeric_median']))
                    logits[p]=np.asarray(model.predict(a,prediction_type='RawFormulaVal',thread_count=2),float)
            calibrated={};raw={}
            for p,f in frames.items():
                z=logits[p];raw[p]=expit(z);calibrated[p]=expit(cal['a']*z+cal['b'])
                err=max(float(np.max(np.abs(z-saved[p+'_logit']))),float(np.max(np.abs(raw[p]-saved[p+'_raw']))),float(np.max(np.abs(calibrated[p]-saved[p+'_calibrated']))))
                assert err<1e-11,(cell,record['runid'],p,err)
                pcsv=pd.read_csv(d/f'{p}-predictions.csv',dtype={c:'string' for c in KEY},float_precision='round_trip');assert pcsv[KEY].equals(f[KEY])
                assert np.max(np.abs(pcsv.calibrated_p.to_numpy()-calibrated[p]))<1e-11
                modelchecks.append({'cell':cell,'runid':record['runid'],'part':p,'max_abs_error':err,'rows':len(f),'reuse':record['reuse']})
            for variant,pp in [('raw',raw),('calibrated',calibrated)]:values[(record['runid'],variant)]=pp
            if family=='nativeCatBoost':cb.append(calibrated)
            else:
                name='p_wlr' if family=='weightedLR' else 'p_ulr'
                for p in PARTS:assert np.max(np.abs(prim[p][name].to_numpy()-calibrated[p]))<1e-11
        mean={p:np.mean([v[p] for v in cb],axis=0) for p in PARTS};values[('nativeCatBoost-mean3','calibrated')]=mean
        for p,f in frames.items():
            assert not prim[p].duplicated(KEY).any() and prim[p][KEY].equals(f[KEY]) and len(prim[p])==len(f)
            assert not set(prim[p])&{'y','future_gmv','future_orders'}
            err=float(np.max(np.abs(prim[p].p_catboost.to_numpy()-mean[p])));assert err<1e-11
            primarychecks.append({'cell':cell,'part':p,'rows':len(f),'key_coverage':True,'catboost_mean_max_error':err})
        for (runid,variant),pp in values.items():
            for part,f in frames.items():
                scopes=[('all',np.ones(len(f),bool))]+[(f'cluster_{c}',f.cluster.to_numpy()==c) for c in sorted(f.cluster.unique())]
                for scope,mask in scopes:
                    y=f.y.to_numpy(int)[mask];p=pp[part][mask];n=len(y);e=int(y.sum())
                    recomputed.append({'cell':cell,'family':runid,'variant':variant,'part':part,'scope':scope,'n':n,'events':e,'sum_p':float(p.sum()),'mean_p':float(p.mean()),'event_rate':float(y.mean()),'logloss':float(log_loss(y,p,labels=[0,1])),'brier':float(brier_score_loss(y,p)),'AP':float(average_precision_score(y,p)) if e else np.nan,'AUC':float(roc_auc_score(y,p)) if 0<e<n else np.nan})
                if part in ['cal','eval'] and variant=='calibrated':
                    bounds=[0,.005,.01,.02,.05,.1,.2,.5,1.]
                    for i,(left,right) in enumerate(zip(bounds[:-1],bounds[1:])):
                        mask=(pp[part]>=left)&((pp[part]<right) if i<7 else (pp[part]<=right));y=f.y.to_numpy(int)[mask];p=pp[part][mask]
                        bindiffs.append({'cell':cell,'family':runid,'part':part,'left':left,'right':right,'n':len(y),'events':int(y.sum()),'sum_p':float(p.sum()),'mean_p':float(p.mean()) if len(p) else np.nan,'event_rate':float(y.mean()) if len(y) else np.nan})
    key=['cell','family','variant','part','scope'];calc=pd.DataFrame(recomputed).sort_values(key).reset_index(drop=True);source=pd.read_csv(ROOT/'proper-metrics.csv',float_precision='round_trip').sort_values(key).reset_index(drop=True)
    assert calc[key].equals(source[key]);errors={}
    for c in ['n','events','sum_p','mean_p','event_rate','logloss','brier','AP','AUC']:
        a=calc[c].to_numpy(float);b=source[c].to_numpy(float);assert np.allclose(a,b,rtol=0,atol=1e-10,equal_nan=True),c
        errors[c]=float(np.nanmax(np.abs(a-b)))
    bkey=['cell','family','part','left','right'];bc=pd.DataFrame(bindiffs).sort_values(bkey).reset_index(drop=True);bs=pd.read_csv(ROOT/'calibration-bins.csv',float_precision='round_trip').sort_values(bkey).reset_index(drop=True)
    assert bc[bkey].equals(bs[bkey])
    for c in ['n','events','sum_p','mean_p','event_rate']:assert np.allclose(bc[c],bs[c],rtol=0,atol=1e-10,equal_nan=True),c
    assert len(records)==30 and sum(not r['reuse'] for r in records)==25 and sum(r['reuse'] for r in records)==5
    pd.DataFrame(modelchecks).to_csv(ROOT/'model-replay.csv',index=False);pd.DataFrame(primarychecks).to_csv(ROOT/'primary-replay.csv',index=False);calc.to_csv(ROOT/'metric-replay.csv',index=False)
    receipt={'status':'PASS','model_part_replays':len(modelchecks),'primary_part_replays':len(primarychecks),'metric_rows':len(calc),'calibration_bin_rows':len(bc),'metric_max_abs_error':errors,'new_fits_in_replay':0,'verifier_sha256':sha(__file__),'data_manifest_sha256':sha(ROOT.parent/'data/data-manifest.json')}
    dump(ROOT/'replay-verification.json',receipt)
    m['status']='READY';m['replay_verification_sha256']=sha(ROOT/'replay-verification.json');m['format']='CSV';m['dtypes']={'customer_unique_id':'string','snapshot_date':'string','p_wlr':'float64','p_ulr':'float64','p_catboost':'float64','cluster':'integer','evaluation_date':'string','strategy':'string'};dump(mf,m)
    print(json.dumps(receipt),flush=True)
if __name__=='__main__':main()
