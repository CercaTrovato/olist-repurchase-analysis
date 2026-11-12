"""Frozen value layer. Read data/probability READY manifests; never load April.
All individual rows and fitted objects remain under value/private/.
"""
from pathlib import Path
import argparse, hashlib, json, math, warnings
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import GammaRegressor
import joblib

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'value'
KEY=['customer_unique_id','snapshot_date']
DATES=['2017-11-01','2017-12-01','2018-01-01']
FEATURES=['F','M','average_order_value','max_order_value']
PKEYS=['p_wlr','p_ulr','p_catboost']
RULES=['p','repeat_Fminus1_M','purchase_F_M','historical_M','historical_AOV','expected_G']
CAPS=[.01,.02,.05,.10,.20,.50,1.0]

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def read_csv(path): return pd.read_csv(path,dtype={k:str for k in KEY},float_precision='round_trip')
def rank_order(score,frame):
    assert np.isfinite(score).all()
    return np.lexsort((frame[KEY[1]].to_numpy(),frame[KEY[0]].to_numpy(),-np.asarray(score)))
def score_hash(frame,score):
    z=frame[KEY].copy(); z['score']=score
    return hashlib.sha256(z.to_csv(index=False,float_format='%.17g',lineterminator='\n').encode()).hexdigest()
def rank_values(order):
    a=np.empty(len(order),dtype=int); a[order]=np.arange(1,len(order)+1); return a

def fit_amount(train,ev,private):
    pos=train.loc[train.future_gmv>0].copy()
    assert len(pos)>0
    g=pos.future_gmv.to_numpy(float); mean=float(g.mean()); maximum=float(g.max())
    info={'fit_rows':len(train),'fit_unique_customers':int(train.customer_unique_id.nunique()),
          'positive_rows':len(pos),'positive_unique_customers':int(pos.customer_unique_id.nunique()),
          'positive_G_mean':mean,'positive_G_max':maximum,'features':FEATURES,
          'equal_weight_unit':'snapshot customer prediction opportunity; repeated source orders are not independent new transactions',
          'config':{'alpha':1,'max_iter':2000,'tol':1e-8},'fallback':False}
    try:
        x=pos[FEATURES].to_numpy(float); e=ev[FEATURES].to_numpy(float)
        assert np.isfinite(x).all() and np.isfinite(e).all() and (x>=0).all() and (e>=0).all()
        scaler=StandardScaler().fit(np.log1p(x))
        model=GammaRegressor(alpha=1,max_iter=2000,tol=1e-8)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always'); model.fit(scaler.transform(np.log1p(x)),g/mean)
            uncapped=model.predict(scaler.transform(np.log1p(e)))*mean
        info['warnings']=[str(w.message) for w in caught]
        info['n_iter']=int(model.n_iter_)
        if not np.isfinite(uncapped).all(): raise ValueError('non-finite Gamma predictions')
        joblib.dump({'scaler':scaler,'model':model,'target_scale':mean,'cap':maximum},private/'amount-model.joblib')
    except Exception as exc:
        info['fallback']=True; info['failure']=f'{type(exc).__name__}: {exc}'
        uncapped=np.full(len(ev),mean)
    pred=np.clip(uncapped,0,maximum)
    info.update({'prediction_min_uncapped':float(uncapped.min()),'prediction_max_uncapped':float(uncapped.max()),
                 'clip_low_count':int((uncapped<0).sum()),'clip_high_count':int((uncapped>maximum).sum()),
                 'clip_total_absolute_change':float(np.abs(pred-uncapped).sum())})
    write_json(private/'amount-fit.json',info)
    return pred,uncapped,info

def list_metrics(ev,score,k,subset=None):
    z=ev if subset is None else ev.loc[subset].reset_index(drop=True)
    s=np.asarray(score) if subset is None else np.asarray(score)[np.asarray(subset)]
    order=rank_order(s,z); k=min(k,len(z)); take=order[:k]
    y=z.y.to_numpy(float); g=z.future_gmv.to_numpy(float); n=z.future_orders.to_numpy(float); long=z.cluster.to_numpy()==1
    hits=float(y[take].sum()); amount=float(g[take].sum()); boundary=float(s[order[k-1]]) if k else None
    tied=s==boundary if k else np.zeros(len(z),bool)
    return {'pool_N':len(z),'K':k,'hits':hits,'precision':hits/k if k else 0,
        'recall':hits/y.sum() if y.sum() else 0,'captured_G':amount,'G_share':amount/g.sum() if g.sum() else 0,
        'captured_orders':float(n[take].sum()),'long_seats':int(long[take].sum()),
        'long_hits':float(y[take][long[take]].sum()),'long_G':float(g[take][long[take]].sum()),
        'zero_score_count':int((s==0).sum()),'zero_score_long_count':int(((s==0)&long).sum()),
        'boundary_score':boundary,'boundary_tie_pool_count':int(tied.sum()),
        'boundary_tie_selected_count':int(tied[take].sum()),'boundary_tie_unselected_count':int(tied[order[k:]].sum())}

def random_metrics(ev,k,subset=None):
    z=ev if subset is None else ev.loc[subset]; k=min(k,len(z)); fraction=k/len(z)
    long=z.cluster==1; y=z.y.sum(); g=z.future_gmv.sum()
    return {'pool_N':len(z),'K':k,'hits':float(fraction*y),'precision':float(y/len(z)),
        'recall':float(fraction),'captured_G':float(fraction*g),'G_share':float(fraction),
        'captured_orders':float(fraction*z.future_orders.sum()),'long_seats':float(fraction*long.sum()),
        'long_hits':float(fraction*z.loc[long,'y'].sum()),'long_G':float(fraction*z.loc[long,'future_gmv'].sum()),
        'reference':'uniform size-K sample expectation; fractional hits are expected counts'}

def bootstrap_one(ev,scores,k,reps=2000,seed=20261112):
    """Paired row resampling; fixed scores; rerank sampled copies and keep ceil(frac*N).
    Integer multiplicities avoid repeated sorting. Duplicate last row partially fills K.
    """
    n=len(ev); rng=np.random.default_rng(seed)
    ys=ev.y.to_numpy(float); gs=ev.future_gmv.to_numpy(float); ns=ev.future_orders.to_numpy(float)
    long=(ev.cluster.to_numpy()==1).astype(float)
    outcomes=np.column_stack([gs,ys,ns,gs*long,ys*long,long])
    metrics=['captured_G','hits','captured_orders','long_G','long_hits','long_seats','G_share']
    orders={r:rank_order(s,ev) for r,s in scores.items()}
    sorted_outcomes={r:outcomes[order] for r,order in orders.items()}
    point={r:list_metrics(ev,s,k) for r,s in scores.items()}
    values={r:np.empty((reps,len(metrics))) for r in scores}
    for rep in range(reps):
        counts=np.bincount(rng.integers(0,n,size=n),minlength=n)
        for rule,order in orders.items():
            c=counts[order]; before=np.cumsum(c)-c
            used=np.minimum(c,np.maximum(k-before,0))
            sums=(used[:,None]*sorted_outcomes[rule]).sum(axis=0)
            total_G=float((counts*gs).sum())
            values[rule][rep]=np.r_[sums,sums[0]/total_G if total_G else np.nan]
    results=[]
    for rule in RULES:
        for baseline in ['p','purchase_F_M']:
            if baseline==rule: continue
            d=values[rule]-values[baseline]
            for j,metric in enumerate(metrics):
                point_rule=point[rule][metric]
                point_baseline=point[baseline][metric]
                valid=d[np.isfinite(d[:,j]),j]
                results.append({'rule':rule,'baseline':baseline,'metric':metric,'reps':reps,'seed':seed,
                    'point_delta':float(point_rule-point_baseline),
                    'valid_reps':len(valid),'undefined_zero_total_G_reps':int(reps-len(valid)),
                    'delta_bootstrap_mean':float(valid.mean()) if len(valid) else None,'ci025':float(np.quantile(valid,.025)) if len(valid) else None,
                    'ci975':float(np.quantile(valid,.975)) if len(valid) else None,'bootstrap_positive_fraction':float((valid>0).mean()) if len(valid) else None,
                    'interval_scope':'conditional on frozen Jan scores; paired customers; reranked resamples; no retraining or model-selection uncertainty'})
    return results

def fit_amount_stage():
    dpath=ROOT/'data/data-manifest.json'; dm=json.loads(dpath.read_text(encoding='utf-8-sig'))
    assert dm['status']=='READY'
    assert sha(dpath)=='0f7f16aed6f01b0b3d2ed83bf14f2eaf739cea88c393418449419b23b6bf37f6'
    assert sha(ROOT/'task_plan.md')=='c6d0ff58feed195bc4db1a803813faaedebb4fd7902874168d4139faeb24c1f4'
    assert not (OUT/'amount-stage-manifest.json').exists(),'amount models already fitted: do not refit'
    source=Path(__file__).read_bytes(); frozen=OUT/'frozen-amount-runner.py'; frozen.write_bytes(source)
    write_json(OUT/'amount-source-freeze.json',{'root_plan_sha256':sha(ROOT/'task_plan.md'),'data_manifest_sha256':sha(dpath),
        'runner_sha256':sha(frozen),'value_plan_sha256':sha(OUT/'value-plan.md'),'schema':{'keys':KEY,'features':FEATURES,
        'target':'future_gmv','positive_branch':'future_gmv>0','historical_F_M_window':'six calendar months; not lifetime'},
        'bootstrap_scopes':['Jan global10','Jan long79'],'bootstrap_reps':2000,'no_eval_based_selection':True})
    stage={'status':'RUNNING','data_manifest_sha256':sha(dpath),'new_amount_fits':0,'cells':{}}
    for date in DATES:
        for strategy in ['single','pooled']:
            cell=f'{date}__{strategy}'; private=OUT/'private/cells'/cell; private.mkdir(parents=True,exist_ok=True)
            entries=dm['cells'][cell]; tables={}
            for part in ['fit','cal','eval']:
                path=ROOT/'data'/entries[part]['path']; assert sha(path)==entries[part]['sha256']
                tables[part]=read_csv(path)
            train,cal,ev=[tables[p] for p in ['fit','cal','eval']]
            assert set(train.customer_unique_id).isdisjoint(cal.customer_unique_id)
            assert pd.to_datetime(train.label_end).max()<=pd.Timestamp(date) and pd.to_datetime(cal.label_end).max()<=pd.Timestamp(date)
            pred,raw,info=fit_amount(train,ev,private)
            info['source_target_support']={k:entries['fit'][k] for k in ['target_order_rows','unique_target_orders','repeated_target_order_rows','duplicate_customer_rows']}
            info['historical_F_M_window']='six calendar months; not lifetime'
            write_json(private/'amount-fit.json',info)
            saved=ev[KEY].copy(); saved['Ghat_conditional']=pred; saved['Ghat_conditional_uncapped']=raw
            path=private/'amount-eval-predictions.csv'; saved.to_csv(path,index=False,float_format='%.17g')
            stage['cells'][cell]={'amount_fit':info,'eval_prediction_path':str(path),'eval_prediction_sha256':sha(path),
                'model_sha256':sha(private/'amount-model.joblib') if (private/'amount-model.joblib').exists() else None,
                'inputs':{part:entries[part] for part in ['fit','cal','eval']}}
            stage['new_amount_fits']+=1; write_json(OUT/'amount-stage-manifest.json',stage)
            print(cell,'amount fit saved',info['positive_rows'],'positives; fallback',info['fallback'],flush=True)
    stage['status']='READY'; write_json(OUT/'amount-stage-manifest.json',stage)

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--bootstrap',action='store_true'); parser.add_argument('--fit-amounts',action='store_true'); args=parser.parse_args()
    if args.fit_amounts: fit_amount_stage(); return
    dpath=ROOT/'data/data-manifest.json'; ppath=ROOT/'probability/probability-manifest.json'
    dm=json.loads(dpath.read_text(encoding='utf-8-sig')); pm=json.loads(ppath.read_text(encoding='utf-8-sig'))
    assert dm['status']=='READY' and pm['status']=='READY','wait for both READY manifests'
    assert sha(ROOT/'task_plan.md')=='c6d0ff58feed195bc4db1a803813faaedebb4fd7902874168d4139faeb24c1f4','scientific plan drift'
    stage=json.loads((OUT/'amount-stage-manifest.json').read_text(encoding='utf-8'))
    assert stage['status']=='READY' and stage['new_amount_fits']==6 and stage['data_manifest_sha256']==sha(dpath)
    (OUT/'private/cells').mkdir(parents=True,exist_ok=True)
    manifest={'status':'RUNNING','data_manifest_sha256':sha(dpath),'probability_manifest_sha256':sha(ppath),
        'forbidden_april_rows_read':0,'amount_model_fit_count':0,'cells':{},'inputs':{},'score_hashes':{}}
    records=[]; amount_records=[]; tails=[]; zeros=[]; boot=[]
    for date in DATES:
        for strategy in ['single','pooled']:
            cell=f'{date}__{strategy}'; private=OUT/'private/cells'/cell; private.mkdir(parents=True,exist_ok=True)
            paths={part:ROOT/'data/private/cells'/cell/f'{part}.csv' for part in ['fit','cal','eval']}
            probpath=ROOT/'probability/private/cells'/cell/'primary-eval-probabilities.csv'
            for part,path in paths.items():
                entry=dm['cells'][cell][part]
                assert path.resolve()==(ROOT/'data'/entry['path']).resolve()
                assert sha(path)==entry['sha256'],f'data SHA mismatch: {cell}/{part}'
            pe=pm['cells'][cell]
            assert probpath.resolve()==Path(pe['primary_eval_path']).resolve()
            assert sha(probpath)==pe['primary_eval_sha256'],f'probability SHA mismatch: {cell}'
            manifest['inputs'][cell]={**{part:{'path':str(p),'sha256':sha(p)} for part,p in paths.items()},
                                       'probability':{'path':str(probpath),'sha256':sha(probpath)}}
            train=read_csv(paths['fit']); cal=read_csv(paths['cal']); ev=read_csv(paths['eval']); probs=read_csv(probpath)
            assert not ev.duplicated(KEY).any() and not probs.duplicated(KEY).any()
            assert ev[KEY].equals(ev.sort_values(KEY).reset_index(drop=True)[KEY]),'eval must use canonical key order for shared bootstrap counts'
            assert set(train.customer_unique_id).isdisjoint(cal.customer_unique_id),'fit/cal customer leakage'
            assert pd.to_datetime(train.label_end).max()<=pd.Timestamp(date),'immature train label'
            assert pd.to_datetime(cal.label_end).max()<=pd.Timestamp(date),'immature cal label'
            assert (ev.F>=1).all() and (ev.M>=0).all() and np.isfinite(ev[FEATURES].to_numpy(float)).all()
            assert ((ev.future_gmv>0).astype(int)==ev.y).all() and ((ev.future_orders>0).astype(int)==ev.y).all()
            merged=ev[KEY].merge(probs[KEY+PKEYS],on=KEY,how='left',validate='one_to_one',indicator=True)
            assert (merged._merge=='both').all() and len(merged)==len(probs)==len(ev)
            assert np.isfinite(merged[PKEYS].to_numpy()).all() and ((merged[PKEYS]>=0)&(merged[PKEYS]<=1)).all().all()
            ae=stage['cells'][cell]; ap=Path(ae['eval_prediction_path']); assert sha(ap)==ae['eval_prediction_sha256']
            saved=read_csv(ap); assert saved[KEY].equals(ev[KEY]); fitinfo=ae['amount_fit']
            cond=saved.Ghat_conditional.to_numpy(); uncapped=saved.Ghat_conditional_uncapped.to_numpy(); manifest['amount_model_fit_count']+=1
            truth=ev[KEY+['y','future_gmv','future_orders','cluster']].copy(); truth.to_csv(private/'evaluation-truth.csv',index=False)
            g=ev.future_gmv.to_numpy(); long=ev.cluster==1; n=len(ev)
            tails.append({'evaluation_date':date,'strategy':strategy,'N':n,'positives':int(ev.y.sum()),'G':float(g.sum()),
                'orders':int(ev.future_orders.sum()),'max_customer_G':float(g.max()),'max_customer_G_share':float(g.max()/g.sum()),
                'top1pct_K':math.ceil(n*.01),'top1pct_G_share':float(np.sort(g)[-math.ceil(n*.01):].sum()/g.sum()),
                'long_N':int(long.sum()),'long_positives':int(ev.loc[long,'y'].sum()),'long_G':float(ev.loc[long,'future_gmv'].sum())})
            for family in PKEYS:
                p=merged[family].to_numpy(); f=ev.F.to_numpy(); m=ev.M.to_numpy()
                scores=dict(zip(RULES,[p,p*np.maximum(f-1,0)*m,p*f*m,p*m,p*(m/f),p*cond]))
                allscores={**scores,'M_only':m,'recency':-ev.R.to_numpy()}
                manager=ev[KEY+['F','M','R','average_order_value','max_order_value','cluster']].copy()
                manager['p']=p; manager['Ghat_conditional']=cond; manager['Ghat_conditional_uncapped']=uncapped
                manager['expected_future_90d_G']=p*cond; manager['constant_positive_G_baseline']=p*fitinfo['positive_G_mean']
                manifest['score_hashes'][cell+'__'+family]={}
                for rule,score in allscores.items():
                    manager['score_'+rule]=score; manager['rank_'+rule]=rank_values(rank_order(score,ev))
                    manifest['score_hashes'][cell+'__'+family][rule]=score_hash(ev,score)
                assert not any(c in manager for c in ['y','future_gmv','future_orders','label_end'])
                manager.to_csv(private/f'manager-{family}.csv',index=False,float_format='%.17g')
                meta={'evaluation_date':date,'strategy':strategy,'family':family}
                for rule,score in allscores.items():
                    for cap in CAPS:
                        records.append({**meta,'scope':'global','capacity':cap,'rule':rule,**list_metrics(ev,score,math.ceil(n*cap))})
                    assert long.sum()>=79
                    records.append({**meta,'scope':'long79','capacity':None,'rule':rule,**list_metrics(ev,score,79,long)})
                for cap in CAPS:
                    records.append({**meta,'scope':'global','capacity':cap,'rule':'random_expectation',**random_metrics(ev,math.ceil(n*cap))})
                records.append({**meta,'scope':'long79','capacity':None,'rule':'random_expectation',**random_metrics(ev,79,long)})
                for label,pred in [('learned_expected_G',p*cond),('constant_positive_G_times_p',p*fitinfo['positive_G_mean'])]:
                    amount_records.append({**meta,'prediction':label,'MAE':float(np.abs(pred-g).mean()),
                        'RMSE':float(np.sqrt(np.square(pred-g).mean())),'predicted_G_total':float(pred.sum()),
                        'actual_G_total':float(g.sum()),'predicted_actual_total_ratio':float(pred.sum()/g.sum())})
                zeros.append({**meta,'F1_N':int((f==1).sum()),'F1_long_N':int(((f==1)&long).sum()),
                    'original_zero_N':int((scores['repeat_Fminus1_M']==0).sum()),
                    'original_zero_actual_hits':int(ev.loc[scores['repeat_Fminus1_M']==0,'y'].sum()),
                    'original_zero_actual_G':float(ev.loc[scores['repeat_Fminus1_M']==0,'future_gmv'].sum()),
                    'original_zero_long_N':int(((scores['repeat_Fminus1_M']==0)&long).sum()),
                    'original_zero_long_hits':int(ev.loc[(scores['repeat_Fminus1_M']==0)&long,'y'].sum()),
                    'original_zero_long_G':float(ev.loc[(scores['repeat_Fminus1_M']==0)&long,'future_gmv'].sum())})
                if args.bootstrap and date=='2018-01-01':
                    for scope,mask,k in [('global10',None,math.ceil(n*.1)),('long79',long,79)]:
                        be=ev if mask is None else ev.loc[mask].reset_index(drop=True)
                        bs=scores if mask is None else {r:s[np.asarray(mask)] for r,s in scores.items()}
                        for b in bootstrap_one(be,bs,k): boot.append({**meta,'scope':scope,'K':k,**b})
                print(cell,family,'complete',flush=True)
            manifest['cells'][cell]={'amount_fit':fitinfo,'manager_paths':[str(private/f'manager-{f}.csv') for f in PKEYS],
                                    'truth_path':str(private/'evaluation-truth.csv')}
            write_json(OUT/'value-manifest.json',manifest)
    pd.DataFrame(records).to_csv(OUT/'capacity-results.csv',index=False)
    pd.DataFrame(amount_records).to_csv(OUT/'amount-prediction-metrics.csv',index=False)
    pd.DataFrame(tails).to_csv(OUT/'amount-tail-concentration.csv',index=False)
    pd.DataFrame(zeros).to_csv(OUT/'original-formula-zero-analysis.csv',index=False)
    if boot: pd.DataFrame(boot).to_csv(OUT/'jan-paired-bootstrap.csv',index=False)
    frame=pd.DataFrame(records); full=frame[(frame.scope=='global')&(frame.capacity==1)]
    for _,r in full.iterrows():
        t=next(t for t in tails if t['evaluation_date']==r.evaluation_date and t['strategy']==r.strategy)
        assert abs(r.captured_G-t['G'])<1e-7 and r.hits==t['positives'] and r.captured_orders==t['orders']
    manifest['status']='READY'; manifest['bootstrap_reps']=2000 if boot else 0
    manifest['artifacts']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='value-manifest.json'}
    write_json(OUT/'value-manifest.json',manifest)

if __name__=='__main__': main()
