"""Fixed final probability batch. No April, ranking, source mutation or tuning."""
import os, sys
sys.dont_write_bytecode = True
os.environ.setdefault('OMP_NUM_THREADS','2')
os.environ.setdefault('MKL_NUM_THREADS','2')
from pathlib import Path
import json, hashlib, time, warnings, importlib.util, shutil, traceback
from unittest.mock import patch
import numpy as np
import pandas as pd
import joblib
from scipy import sparse
from scipy.special import expit
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LogisticRegression, _logistic
from sklearn.metrics import log_loss, brier_score_loss, average_precision_score, roc_auc_score
from catboost import CatBoostClassifier
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parent
BATCH=ROOT.parent
OLD=Path('E:/app-data/codex/outputs/is6400-common-comparison-20261112')
DATA=BATCH/'data'
KEY=['customer_unique_id','snapshot_date']
PARTS=['fit','cal','eval']
SEEDS=[2026,2027,2028]
LR_PARAMS=dict(C=1.,solver='lbfgs',tol=1e-10,max_iter=5000,random_state=2026)
CB_PARAMS=dict(depth=3,iterations=300,learning_rate=.03,l2_leaf_reg=10,loss_function='Logloss',thread_count=2,verbose=False,allow_writing_files=False,task_type='CPU',use_best_model=False)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def clean(x):
    if isinstance(x,dict): return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(tuple,list)): return [clean(v) for v in x]
    if isinstance(x,np.ndarray): return clean(x.tolist())
    if isinstance(x,np.generic): return clean(x.item())
    if isinstance(x,Path): return str(x).replace('\\','/')
    if isinstance(x,float) and not np.isfinite(x): return None
    return x
def dump(p,x):
    p=Path(p);p.parent.mkdir(exist_ok=True,parents=True)
    p.write_text(json.dumps(clean(x),ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def load_math():
    spec=importlib.util.spec_from_file_location('old_eval_math',OLD/'eval_harness.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.fit_monotone_platt,module.apply_calibration
fit_platt,apply_cal=load_math()

def load_csv(p,cats):
    return pd.read_csv(p,dtype={c:'string' for c in KEY+list(cats)},float_precision='round_trip')

def prepare_lr(frames,base,transform=None):
    numeric=[c for c in base if c!='state']
    assert len(numeric)==7 and len(base)==8
    if transform is None:
        a=frames['fit'][numeric].to_numpy(float)
        assert np.isfinite(a).all() and (a>=0).all()
        transform={'numeric':numeric,'scaler':StandardScaler().fit(np.log1p(a)),
                   'encoder':OneHotEncoder(handle_unknown='ignore',sparse_output=True,dtype=np.float64).fit(frames['fit'][['state']].fillna('__MISSING__').astype(str))}
    out={}
    for part,f in frames.items():
        a=f[numeric].to_numpy(float);assert np.isfinite(a).all() and (a>=0).all()
        out[part]=sparse.hstack([sparse.csr_matrix(transform['scaler'].transform(np.log1p(a))),transform['encoder'].transform(f[['state']].fillna('__MISSING__').astype(str))],format='csr')
    return out,transform

def prepare_cb(frames,fields,cats,transform=None):
    numeric=[c for c in fields if c not in cats]
    if transform is None:
        med=frames['fit'][numeric].median().fillna(0.)
        transform={'fields':fields,'categorical_fields':cats,'numeric_median':med.to_dict(),'fit_only':True,'categorical_missing':'__MISSING__'}
    out={}
    for part,f in frames.items():
        a=f[fields].copy()
        for c in cats:a[c]=a[c].astype('string').fillna('__MISSING__').astype(str)
        a[numeric]=a[numeric].astype(float).fillna(pd.Series(transform['numeric_median']))
        assert np.isfinite(a[numeric].to_numpy(float)).all();out[part]=a
    return out,transform

def lr_gradient(model,x,y,weighted):
    n=len(y);s=y.sum();w=np.where(y==1,n/(2*s),n/(2*(n-s))) if weighted else np.ones(n)
    z=model.decision_function(x);coef=model.coef_.ravel();r=w*(expit(z)-y)
    g=np.r_[np.asarray(x.T@r).ravel()+coef,r.sum()]
    return {'sum_objective':float(np.dot(w,np.logaddexp(0,z)-y*z)+coef@coef/2),
            'gradient_sum_inf':float(np.max(np.abs(g))),'gradient_weighted_mean_inf':float(np.max(np.abs(g))/w.sum()),
            'weighted_mean_gradient_at_or_below_tol':bool(np.max(np.abs(g))/w.sum()<=1e-10),
            'weight_sum':float(w.sum()),'definition':'sum weighted BCE + .5*coef squared; intercept unpenalized; divide whole gradient by weight_sum to compare solver gtol'}

def train_lr(x,y,d,weighted):
    captured=[];original=_logistic.optimize.minimize
    def capture(*args,**kwargs):
        r=original(*args,**kwargs)
        captured.append({'success':bool(r.success),'status':int(r.status),'message':str(r.message),'nit':int(r.nit),'fun':float(r.fun),'jac_inf':float(np.max(np.abs(r.jac))),'options':kwargs.get('options',{})});return r
    tick=time.perf_counter();params=LR_PARAMS|{'class_weight':'balanced' if weighted else None}
    with warnings.catch_warnings(record=True) as ws,patch.object(_logistic.optimize,'minimize',capture),threadpool_limits(2):
        warnings.simplefilter('always');model=LogisticRegression(**params).fit(x['fit'],y)
    joblib.dump(model,d/'model.joblib',compress=3)
    meta={'parameters':params,'optimizer':captured,'training_objective':lr_gradient(model,x['fit'],y,weighted),'warnings':[str(w.message) for w in ws],'training_seconds':time.perf_counter()-tick,'n_iter':model.n_iter_.tolist()}
    return model,{p:np.asarray(model.decision_function(x[p]),float) for p in PARTS},meta

def train_cb(x,y,d,seed,cats):
    tick=time.perf_counter();model=CatBoostClassifier(**CB_PARAMS,random_seed=seed)
    with threadpool_limits(2):model.fit(x['fit'],y,cat_features=cats)
    model.save_model(str(d/'model.cbm'));loss=model.get_evals_result()['learn']['Logloss']
    pd.DataFrame({'iteration':np.arange(1,len(loss)+1),'fit_Logloss':loss}).to_csv(d/'fit-loss.csv',index=False)
    assert model.tree_count_==300 and len(loss)==300
    return model,{p:np.asarray(model.predict(x[p],prediction_type='RawFormulaVal',thread_count=2),float) for p in PARTS},{'parameters':CB_PARAMS|{'random_seed':seed},'actual_parameters':model.get_all_params(),'tree_count':model.tree_count_,'training_seconds':time.perf_counter()-tick,'final_fit_Logloss':loss[-1],'eval_set_used':False,'early_stopping_used':False,'class_weight_used':False}

def align_old(frames,cats,fields):
    old={t:load_csv(OLD/f'shared/private/{t}-raw.csv',cats) for t in ['oct','jan']}
    idx=np.load(OLD/'shared/private/split-20261111/indices.npz')
    sources={'fit':old['oct'].iloc[idx['fit']].reset_index(drop=True),'cal':old['oct'].iloc[idx['cal']].reset_index(drop=True),'eval':old['jan']}
    reorder={};audit={}
    for p,f in frames.items():
        s=sources[p];k=s[KEY].copy();k['_oldrow']=np.arange(len(s))
        j=f[KEY].merge(k,on=KEY,how='left',sort=False,validate='one_to_one')
        assert len(f)==len(s) and j._oldrow.notna().all()
        ii=j._oldrow.to_numpy(int);other=s.iloc[ii].reset_index(drop=True)
        assert f[KEY].equals(other[KEY]) and np.array_equal(f.y,other.y)
        for c in fields:
            if c in cats:assert f[c].fillna('__MISSING__').equals(other[c].fillna('__MISSING__')),c
            else:assert np.allclose(f[c].to_numpy(float),other[c].to_numpy(float),rtol=0,atol=1e-10,equal_nan=True),c
        reorder[p]=ii;audit[p]={'rows':len(f),'positives':int(f.y.sum()),'keys_labels_141_fields_equal':True,'numeric_atol':1e-10}
    return reorder,audit

def reuse_run(frames,family,seed,cats,fields,reorder,d):
    rid=(f'{family}-base8-split20261111' if family in ['weightedLR','unweightedLR'] else f'nativeCatBoost-full141-split20261111-seed{seed}')
    source=OLD/'classical/private'/rid;meta=json.loads((source/'metadata.json').read_text())
    model_file=source/('model.joblib' if family in ['weightedLR','unweightedLR'] else 'model.cbm')
    cached=np.load(source/'logits.npz');scores=np.load(OLD/f'classical/private/{rid}-scores.npz')
    cal_path=OLD/f'classical/private/{rid}-calibration.json';cal=json.loads(cal_path.read_text())
    logits={};errors={};input_paths={}
    if family in ['weightedLR','unweightedLR']:
        model=joblib.load(model_file);mask=np.load(OLD/'shared/private/split-20261111/base8-mask.npy')
        for p in PARTS:
            op='jan' if p=='eval' else p;src=OLD/f'shared/private/split-20261111/{op}.npz'
            a=sparse.load_npz(src).multiply(mask).tocsr()[reorder[p]]
            actual=model.decision_function(a);sparse.save_npz(d/f'{p}-legacy-input.npz',a);input_paths[p]=str(d/f'{p}-legacy-input.npz')
            logits[p]=cached[op][reorder[p]];errors[p]=float(np.max(np.abs(actual-logits[p])))
    else:
        transform=meta['native_preprocess'];a,_=prepare_cb(frames,fields,cats,transform)
        dump(d/'transform.json',transform);model=CatBoostClassifier();model.load_model(str(model_file))
        for p in PARTS:
            op='jan' if p=='eval' else p;actual=model.predict(a[p],prediction_type='RawFormulaVal',thread_count=2)
            logits[p]=cached[op][reorder[p]];errors[p]=float(np.max(np.abs(actual-logits[p])))
    assert max(errors.values())<1e-11,(rid,errors)
    for p in PARTS:
        op='jan' if p=='eval' else p
        assert np.max(np.abs(apply_cal(logits[p],cal)-scores[op+'_calibrated'][reorder[p]]))<1e-12
    shutil.copy2(model_file,d/model_file.name)
    if family in ['weightedLR','unweightedLR']:
        shutil.copy2(OLD/'shared/private/split-20261111/transformers.joblib',d/'legacy-transformers.joblib')
        shutil.copy2(OLD/'shared/private/split-20261111/base8-mask.npy',d/'legacy-base8-mask.npy')
    sources=[model_file,source/'metadata.json',source/'logits.npz',cal_path,OLD/f'classical/private/{rid}-scores.npz',OLD/'shared/data-manifest.json',OLD/'shared/private/split-20261111/indices.npz',OLD/'shared/private/oct-raw.csv',OLD/'shared/private/jan-raw.csv']
    return logits,cal,{'reuse_existing':True,'source_run_id':rid,'source_files':{str(p):sha(p) for p in sources},'cached_model_logit_max_abs_error':errors,'legacy_inputs':input_paths,'original_metadata':meta}

def metric_rows(frames,probabilities,cell,family,variant):
    rows=[];bins=[]
    for part,f in frames.items():
        p=np.asarray(probabilities[part],float);assert len(p)==len(f) and np.isfinite(p).all() and ((p>=0)&(p<=1)).all()
        scopes=[('all',np.ones(len(f),bool))]+[(f'cluster_{c}',f.cluster.to_numpy()==c) for c in sorted(f.cluster.unique())]
        for scope,mask in scopes:
            y=f.y.to_numpy(int)[mask];q=p[mask];events=int(y.sum())
            rows.append({'cell':cell,'family':family,'variant':variant,'part':part,'scope':scope,'n':len(y),'events':events,'sum_p':float(q.sum()),'mean_p':float(q.mean()),'event_rate':float(y.mean()),'logloss':float(log_loss(y,q,labels=[0,1])),'brier':float(brier_score_loss(y,q)),'AP':float(average_precision_score(y,q)) if events else None,'AUC':float(roc_auc_score(y,q)) if 0<events<len(y) else None,'calibrated_cal_status':'calibrator resubstitution; not independent evaluation' if part=='cal' and variant=='calibrated' else ''})
        if part in ['cal','eval'] and variant=='calibrated':
            bounds=np.array([0,.005,.01,.02,.05,.1,.2,.5,1.]);ix=np.minimum(np.searchsorted(bounds,p,side='right')-1,len(bounds)-2)
            for b in range(len(bounds)-1):
                mask=ix==b;y=f.y.to_numpy(int)[mask];q=p[mask]
                bins.append({'cell':cell,'family':family,'part':part,'left':bounds[b],'right':bounds[b+1],'n':len(y),'events':int(y.sum()),'sum_p':float(q.sum()),'mean_p':float(q.mean()) if len(q) else None,'event_rate':float(y.mean()) if len(y) else None,'status':'calibrator resubstitution' if part=='cal' else 'rolling eval; overlapping customers/windows'})
    return rows,bins

def run():
    manifest_path=DATA/'data-manifest.json';manifest=json.loads(manifest_path.read_text());assert manifest['status']=='READY'
    auth=json.loads((ROOT/'root-authorization.json').read_text());assert auth['status']=='AUTHORIZED'
    for path in [BATCH/'task_plan.md',manifest_path,Path(__file__),ROOT/'plan.md',ROOT/'schema-contract.json']:
        assert auth['files'][str(path).replace('\\','/')]==sha(path),(path,'authorization hash changed')
    fields=manifest['raw_fields'];cats=manifest['categorical_fields'];base=manifest['base_fields']
    assert len(fields)==141 and set(base)<=set(fields) and not set(fields)&set(KEY+['y','cluster','future_gmv','future_orders','label_end'])
    input_paths=[DATA/f'private/cells/{v}__{s}/{p}.csv' for v in ['2017-11-01','2017-12-01','2018-01-01'] for s in ['single','pooled'] for p in PARTS]
    legacy_paths=[OLD/'shared/data-manifest.json',OLD/'shared/private/oct-raw.csv',OLD/'shared/private/jan-raw.csv']+list((OLD/'shared/private/split-20261111').glob('*'))
    for rid in ['weightedLR-base8-split20261111','unweightedLR-base8-split20261111']+[f'nativeCatBoost-full141-split20261111-seed{s}' for s in SEEDS]:
        legacy_paths+=list((OLD/'classical/private'/rid).glob('*'))+[OLD/f'classical/private/{rid}-scores.npz',OLD/f'classical/private/{rid}-calibration.json']
    freeze={'status':'FROZEN_BEFORE_FIRST_FIT','authorization':auth,'source_files':{str(p):sha(p) for p in [Path(__file__),ROOT/'plan.md',ROOT/'schema-contract.json',ROOT/'verify_probability.py',BATCH/'task_plan.md',manifest_path,OLD/'eval_harness.py']+input_paths+legacy_paths if p.is_file()},'started_utc':pd.Timestamp.now(tz='UTC').isoformat()}
    assert not (ROOT/'input-freeze.json').exists(),'Run is single use; inspect existing artifacts, do not retrain'
    dump(ROOT/'input-freeze.json',freeze)
    metrics=[];bins=[];records=[];cells={};new_count=0;reuse_count=0
    for v in ['2017-11-01','2017-12-01','2018-01-01']:
      for strategy in ['single','pooled']:
        cell=f'{v}__{strategy}';cd=ROOT/'private/cells'/cell;cd.mkdir(parents=True,exist_ok=True)
        paths={p:DATA/f'private/cells/{cell}/{p}.csv' for p in PARTS}
        for q in paths.values():assert sha(q)==freeze['source_files'][str(q)]
        frames={p:load_csv(paths[p],cats) for p in PARTS}
        assert not any(f.duplicated(KEY).any() for f in frames.values())
        assert not set(frames['fit'].customer_unique_id)&set(frames['cal'].customer_unique_id)
        assert (pd.to_datetime(frames['fit'].label_end)<=pd.Timestamp(v)).all()
        assert (pd.to_datetime(frames['cal'].label_end)<=pd.Timestamp(v)).all()
        assert frames['eval'].snapshot_date.eq(v).all()
        reuse=(v=='2018-01-01' and strategy=='single');reorder=audit=None
        if reuse:reorder,audit=align_old(frames,cats,fields);dump(cd/'legacy-identity-audit.json',audit)
        else:
            xlr,tlr=prepare_lr(frames,base);joblib.dump(tlr,cd/'lr-transform.joblib',compress=3)
            xcb,tcb=prepare_cb(frames,fields,cats);dump(cd/'cb-transform.json',tcb)
        primary={p:frames[p][KEY+['cluster']].copy() for p in PARTS};run_records=[];cbps=[]
        for family,seed in [('weightedLR',None),('unweightedLR',None)]+[('nativeCatBoost',s) for s in SEEDS]:
            runid=family+(f'-s{seed}' if seed else '');d=cd/runid;d.mkdir(exist_ok=True)
            if reuse:
                logits,cal,meta=reuse_run(frames,family,seed,cats,fields,reorder,d);reuse_count+=1
            else:
                if family in ['weightedLR','unweightedLR']:
                    model,logits,meta=train_lr(xlr,frames['fit'].y.to_numpy(int),d,family=='weightedLR')
                else:model,logits,meta=train_cb(xcb,frames['fit'].y.to_numpy(int),d,seed,cats)
                cal=fit_platt(logits['cal'],frames['cal'].y.to_numpy(int));new_count+=1
            pp={p:apply_cal(logits[p],cal) for p in PARTS};raw={p:expit(logits[p]) for p in PARTS}
            np.savez_compressed(d/'scores.npz',**{f'{p}_{kind}':value[p] for kind,value in [('logit',logits),('raw',raw),('calibrated',pp)] for p in PARTS})
            dump(d/'calibration.json',cal);dump(d/'metadata.json',meta)
            for p in PARTS:
                z=frames[p][KEY].copy();z['logit']=logits[p];z['raw_p']=raw[p];z['calibrated_p']=pp[p];z.to_csv(d/f'{p}-predictions.csv',index=False,lineterminator='\n')
            for variant,values in [('raw',raw),('calibrated',pp)]:
                r,b=metric_rows(frames,values,cell,runid,variant);metrics+=r;bins+=b
            if family=='nativeCatBoost':cbps.append(pp)
            else:
                col='p_wlr' if family=='weightedLR' else 'p_ulr'
                for p in PARTS:primary[p][col]=pp[p]
            record={'cell':cell,'family':family,'seed':seed,'runid':runid,'reuse':reuse,'cal_n':len(frames['cal']),'cal_events':int(frames['cal'].y.sum()),'calibration':cal,'metadata_path':str(d/'metadata.json'),'scores_path':str(d/'scores.npz'),'files':{str(q):sha(q) for q in sorted(d.iterdir()) if q.is_file()}}
            records.append(record);run_records.append(record)
            dump(ROOT/'execution-progress.json',{'completed_models':len(records),'new_fits':new_count,'reused_models':reuse_count,'last':cell+'/'+runid})
            print('COMPLETED',cell,runid,'reuse',reuse,'new',new_count,flush=True)
        mean={p:np.mean([x[p] for x in cbps],axis=0) for p in PARTS}
        r,b=metric_rows(frames,mean,cell,'nativeCatBoost-mean3','calibrated');metrics+=r;bins+=b
        for p in PARTS:
            primary[p]['p_catboost']=mean[p];primary[p]['evaluation_date']=v;primary[p]['strategy']=strategy
            primary[p].to_csv(cd/f'primary-{p}-probabilities.csv',index=False,lineterminator='\n')
        cells[cell]={'evaluation_date':v,'strategy':strategy,'primary_eval_path':str(cd/'primary-eval-probabilities.csv').replace('\\','/'),'primary_eval_sha256':sha(cd/'primary-eval-probabilities.csv'),'rows':{p:len(f) for p,f in frames.items()},'input_files':{str(paths[p]):sha(paths[p]) for p in PARTS},'runids':[r['runid'] for r in run_records],'directory':str(cd)}
    assert new_count==25 and reuse_count==5
    pd.DataFrame(metrics).to_csv(ROOT/'proper-metrics.csv',index=False,lineterminator='\n');pd.DataFrame(bins).to_csv(ROOT/'calibration-bins.csv',index=False,lineterminator='\n')
    dump(ROOT/'model-records.json',records)
    for p,h in freeze['source_files'].items():assert sha(p)==h,(p,'source changed')
    dump(ROOT/'probability-manifest.json',{'schema_version':'probability-v1','status':'AWAITING_REPLAY','new_supervised_fits':new_count,'reused_existing_models':reuse_count,'cells':cells,'primary_probability_columns':['p_wlr','p_ulr','p_catboost'],'input_freeze_sha256':sha(ROOT/'input-freeze.json'),'root_plan_sha256':sha(BATCH/'task_plan.md'),'metrics_path':str(ROOT/'proper-metrics.csv')})

if __name__=='__main__':
    try:run()
    except Exception as e:
        dump(ROOT/'failures.json',{'status':'FAILED_NO_AUTOMATIC_RETRAIN','error':repr(e),'traceback':traceback.format_exc()});raise
