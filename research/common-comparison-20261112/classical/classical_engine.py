"""CPU2 training primitives; shared-data adapter lives in run_classical.py.
No split, feature engineering, calibration, threshold selection, or April input.
"""
import sys
sys.dont_write_bytecode=True
import os
os.environ.setdefault('OMP_NUM_THREADS','2');os.environ.setdefault('MKL_NUM_THREADS','2')
import json,time,hashlib,warnings
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
import joblib
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from sklearn.linear_model import _logistic
from catboost import CatBoostClassifier
from threadpoolctl import threadpool_limits

LR_PARAMS=dict(C=1.,class_weight='balanced',solver='lbfgs',tol=1e-10,max_iter=5000,random_state=2026)
CB_PARAMS=dict(depth=3,iterations=300,learning_rate=.03,l2_leaf_reg=10,loss_function='Logloss',thread_count=2,verbose=False,allow_writing_files=False,task_type='CPU',use_best_model=False)
PERIODS=('fit','cal','jan')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(x,p):Path(p).write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
def validate(parts,y):
    assert set(parts)==set(PERIODS) and parts['fit'].shape[0]==16928 and parts['cal'].shape[0]==4232 and parts['jan'].shape[0]==29368
    assert y.shape==(16928,) and y.sum()==169 and set(np.unique(y))=={0,1}
    for a in parts.values():assert a.ndim==2 and a.dtype==np.float64 and np.isfinite(a).all()
    assert len({a.shape[1] for a in parts.values()})==1

def loss_gradient(model,x,y,C=1.,weighted=True):
    y=np.asarray(y,dtype=np.float64);n=len(y);npos=y.sum();pw=n/(2*npos) if weighted else 1.;nw=n/(2*(n-npos)) if weighted else 1.;weight=np.where(y==1,pw,nw);z=model.decision_function(x);coef=model.coef_.ravel().astype(np.float64)
    bce=np.logaddexp(0,z)-y*z;data=float(np.sum(weight*bce));penalty=float(coef@coef/(2*C));residual=weight*(expit(z)-y);gradient=np.r_[x.T@residual+coef/C,residual.sum()];normalized=gradient/weight.sum()
    return gradient,dict(sum_weighted_BCE=data,L2_penalty=penalty,sum_objective=data+penalty,weight_sum=float(weight.sum()),positive_weight=float(pw),negative_weight=float(nw),gradient_sum_inf=float(np.max(np.abs(gradient))),gradient_sum_l2=float(np.linalg.norm(gradient)),gradient_weighted_mean_inf=float(np.max(np.abs(normalized))),gradient_weighted_mean_l2=float(np.linalg.norm(normalized)),weighted_mean_gradient_at_or_below_tol=bool(np.max(np.abs(normalized))<=LR_PARAMS['tol']),objective_definition='sum weighted BCE + 0.5*||coef||^2/C; intercept unpenalized; weights=1 for ULR',gradient_note='Solver uses weighted-mean loss and penalty/(sum weights); divide complete sum-objective gradient by weight_sum to compare its gtol scale')

def train_wlr(parts,y,directory,source,weighted=True):
    validate(parts,y);directory=Path(directory);directory.mkdir(exist_ok=True,parents=True);captured=[];original_minimize=_logistic.optimize.minimize
    def record_minimize(*args,**kwargs):
        result=original_minimize(*args,**kwargs)
        captured.append(dict(success=bool(result.success),status=int(result.status),message=str(result.message),nit=int(result.nit),nfev=int(result.nfev),njev=int(result.njev),fun=float(result.fun),jac_inf=float(np.max(np.abs(result.jac))),options={k:float(v) if isinstance(v,np.floating) else v for k,v in kwargs.get('options',{}).items()}))
        return result
    tick=time.perf_counter();params=LR_PARAMS|dict(class_weight='balanced' if weighted else None)
    with threadpool_limits(limits=2),warnings.catch_warnings(record=True) as ws,patch.object(_logistic.optimize,'minimize',record_minimize):
        warnings.simplefilter('always');model=LogisticRegression(**params).fit(parts['fit'],y)
    seconds=time.perf_counter()-tick;gradient,diagnostic=loss_gradient(model,parts['fit'],y,weighted=weighted)
    np.save(directory/'gradient-sum.npy',gradient);joblib.dump(model,directory/'model.joblib',compress=3)
    logits={period:np.asarray(model.decision_function(a),dtype=np.float64) for period,a in parts.items()};np.savez_compressed(directory/'logits.npz',**logits)
    meta=dict(family='weightedLR' if weighted else 'unweightedLR',parameters=params,input_columns=int(parts['fit'].shape[1]),fit_rows=len(y),training_seconds=seconds,n_iter=model.n_iter_.tolist(),warnings=[str(w.message) for w in ws],optimizer=captured,training_objective=diagnostic,source=source,engine_sha256=sha(Path(__file__)),logit_dtype='float64')
    dump(meta,directory/'metadata.json');return meta

def native_parts(rawparts,categorical):
    """Only fit-median handling for native bridge; shared split rows are untouched."""
    fields=list(rawparts['fit'].columns);assert all(list(v.columns)==fields for v in rawparts.values());numeric=[c for c in fields if c not in categorical]
    med=rawparts['fit'][numeric].apply(pd.to_numeric,errors='raise').median().fillna(0.)
    prepared={}
    for p,raw in rawparts.items():
        a=raw.copy()
        for c in categorical:a[c]=a[c].astype('string').fillna('__MISSING__').astype(str)
        a[numeric]=a[numeric].apply(pd.to_numeric,errors='raise').astype(np.float64).fillna(med)
        assert np.isfinite(a[numeric].to_numpy(float)).all();prepared[p]=a
    return prepared,dict(fields=fields,categorical_fields=list(categorical),numeric_median=med.to_dict(),categorical_missing='__MISSING__',fit_only=True,no_log_or_scale=True)

def train_cb(parts,y,directory,source,seed,native=False,categorical=None,native_preprocess=None):
    directory=Path(directory);directory.mkdir(exist_ok=True,parents=True)
    if not native:validate(parts,y)
    else:assert [len(parts[k]) for k in PERIODS]==[16928,4232,29368] and len(y)==16928 and y.sum()==169
    params=CB_PARAMS|dict(random_seed=seed);tick=time.perf_counter();model=CatBoostClassifier(**params)
    with threadpool_limits(limits=2):model.fit(parts['fit'],y,cat_features=list(categorical) if native else None)
    seconds=time.perf_counter()-tick;model.save_model(str(directory/'model.cbm'));loss=model.get_evals_result()['learn']['Logloss'];assert len(loss)==300 and model.tree_count_==300
    pd.DataFrame({'iteration':np.arange(1,301),'fit_Logloss':loss}).to_csv(directory/'fit-loss.csv',index=False)
    logits={p:np.asarray(model.predict(a,prediction_type='RawFormulaVal',thread_count=2),dtype=np.float64) for p,a in parts.items()};np.savez_compressed(directory/'logits.npz',**logits)
    meta=dict(family='CatBoost-native' if native else 'CatBoost-encoded',parameters=params,actual_parameters=model.get_all_params(),input_columns=int(parts['fit'].shape[1]),fit_rows=len(y),training_seconds=seconds,tree_count=model.tree_count_,final_fit_Logloss=float(loss[-1]),fit_loss_definition='CatBoost reported unweighted learn Logloss; not the weighted-LR penalized sum objective',eval_set_used=False,early_stopping_used=False,class_weight_used=False,source=source,engine_sha256=sha(Path(__file__)),logit_dtype='float64')
    if native:meta['native_preprocess']=native_preprocess
    dump(meta,directory/'metadata.json');return meta

def verify_model(parts,directory,native=False):
    directory=Path(directory);saved=np.load(directory/'logits.npz');meta=json.loads((directory/'metadata.json').read_text());errors={}
    is_lr=meta['family'] in ['weightedLR','unweightedLR']
    if is_lr:model=joblib.load(directory/'model.joblib')
    else:model=CatBoostClassifier();model.load_model(str(directory/'model.cbm'))
    for p,a in parts.items():
        logits=model.decision_function(a) if is_lr else model.predict(a,prediction_type='RawFormulaVal',thread_count=2)
        error=float(np.max(np.abs(logits-saved[p])));assert error<1e-12 and saved[p].dtype==np.float64;errors[p]=error
    return errors
