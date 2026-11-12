"""Frozen one-split July -> seen October temporal diagnostic. --freeze never fits."""
import os,sys
sys.dont_write_bytecode=True
os.environ.setdefault('OMP_NUM_THREADS','2');os.environ.setdefault('MKL_NUM_THREADS','2')
import argparse,hashlib,importlib.util,json,time,warnings,traceback
from pathlib import Path
import numpy as np,pandas as pd,joblib
from scipy import sparse
from scipy.special import expit
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler,OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss,brier_score_loss,average_precision_score,roc_auc_score
from catboost import CatBoostClassifier
import torch
from threadpoolctl import threadpool_limits
OUT=Path(__file__).resolve().parent;ROOT=OUT.parent.parent;PR=OUT/'private'
SPEC=Path('E:/app-data/codex/outputs/is6400-validation-20261111/features/feature-views.json')
GROUP=Path('E:/app-data/codex/outputs/is6400-local-round2-20261110/role-04/train_clusters.csv')
KEY=['customer_unique_id','snapshot_date'];BASE=['R','F','M','average_item_rows','freight_share','recent30_orders','recent30_spend','state']
SEEDS=[2026,2027,2028];SPLIT=20261111
LR=dict(C=1.,class_weight='balanced',solver='lbfgs',tol=1e-10,max_iter=5000,random_state=2026)
CB=dict(depth=3,iterations=300,learning_rate=.03,l2_leaf_reg=10,loss_function='Logloss',thread_count=2,verbose=False,allow_writing_files=False,task_type='CPU',use_best_model=False)
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
old=module('temporal_original_neural',ROOT/'neural/neural_models.py')
parent=module('temporal_parent_calibration',ROOT/'eval_harness.py')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):parent.dump(OUT/p,x)
def load_inputs():
    s=json.loads(SPEC.read_text());fields=s['views']['full-structure'];cats=s['categorical_columns'];views=s['logical_views']
    assert len(fields)==141 and len(set(fields))==141 and set(fields)==set(sum(views.values(),[])) and not set(fields)&set(KEY+['y','cluster_id'])
    frames={}
    for tag,date,n,pos in [('july','2017-07-01',14012,120),('oct','2017-10-01',21160,211)]:
        p=OUT.parent/'time-audit/private'/('july-full141.csv' if tag=='july' else 'october-full141.csv')
        f=pd.read_csv(p,usecols=KEY+fields+['y'],dtype={c:'string' for c in KEY+cats},float_precision='round_trip')
        assert len(f)==n and f.y.sum()==pos and f.snapshot_date.eq(date).all() and not f.duplicated(KEY).any();frames[tag]=f
    g=pd.read_csv(GROUP,usecols=KEY+['cluster_id'],dtype={c:'string' for c in KEY})
    frames['oct']=frames['oct'].merge(g,on=KEY,how='left',validate='one_to_one',sort=False);assert frames['oct'].cluster_id.notna().all()
    frames['oct'].cluster_id=frames['oct'].cluster_id.astype(int)
    assert (frames['oct'].cluster_id.eq(1).sum(),frames['oct'].loc[frames['oct'].cluster_id.eq(1),'y'].sum())==(9121,78)
    fit,cal=train_test_split(np.arange(len(frames['july'])),test_size=.2,random_state=SPLIT,stratify=frames['july'].y);fit=np.sort(fit);cal=np.sort(cal)
    assert (len(fit),int(frames['july'].y.iloc[fit].sum()),len(cal),int(frames['july'].y.iloc[cal].sum()))==(11209,96,2803,24)
    return s,frames,fit,cal
def frozen_paths():
    return [Path(__file__),OUT/'verify_temporal.py',OUT/'time-validation-plan.md',SPEC,GROUP,ROOT/'prepare_shared.py',ROOT/'eval_harness.py',ROOT/'neural/neural_models.py',ROOT/'classical/classical_engine.py',OUT.parent/'time-audit/private/july-full141.csv',OUT.parent/'time-audit/private/october-full141.csv',OUT.parent/'time-audit/audit.json',OUT.parent/'time-audit/clarification/clarification-audit.json']
def freeze():
    assert not (OUT/'source-freeze.json').exists(),'Existing freeze is immutable'
    spec,f,fit,cal=load_inputs();PR.mkdir(exist_ok=True)
    np.savez_compressed(PR/'indices.npz',fit=fit,cal=cal)
    counts={k:dict(n=len(v),positive=int(v.y.sum())) for k,v in [('July_fit',f['july'].iloc[fit]),('July_cal',f['july'].iloc[cal]),('Oct',f['oct'])]}
    groupcounts=f['oct'].groupby('cluster_id').y.agg(['size','sum']).to_dict('index')
    record=dict(status='frozen_awaiting_root_READY_no_fit_performed',source_sha256={str(p):sha(p) for p in frozen_paths()},split_indices_sha256=sha(PR/'indices.npz'),counts=counts,Oct_groups=groupcounts,view_fields=spec['logical_views'],categorical_fields=spec['categorical_columns'],fields=spec['views']['full-structure'],seeds=SEEDS,models=13,AE_pretraining_runs=3,information=['base8','full141'],encoded_dims='computed after READY using July-fit only',LR=LR,CB=CB,NN=dict(supervised_epochs=50,pretrain_epochs=20,Adam_lr=.001,supervised_batch=512,pretrain_batch=256,view_latent=16),global_capacities=[2116,1058,4232],long79=79,models_fit=0,transformers_fit=0,April_rows=0)
    dump('source-freeze.json',record);print(json.dumps(record['counts']),flush=True)
def assert_freeze():
    d=json.loads((OUT/'source-freeze.json').read_text())
    for p,h in d['source_sha256'].items():assert sha(p)==h,('frozen source changed',p)
    assert sha(PR/'indices.npz')==d['split_indices_sha256'];return d
def encode(spec,frames,fit,cal):
    tr,ev=frames['july'],frames['oct'];cats=spec['categorical_columns'];mats=[[],[],[]];trans={};lineage=[];dims=[]
    for view,cols in spec['logical_views'].items():
        nums=[c for c in cols if c not in cats];categories=[c for c in cols if c in cats];a=tr[nums].to_numpy(float);b=ev[nums].to_numpy(float)
        with warnings.catch_warnings():warnings.simplefilter('ignore',RuntimeWarning);med=np.nanmedian(a[fit],axis=0)
        med=np.nan_to_num(med,nan=0.);raw=[i for i,c in enumerate(nums) if c.endswith('_lat') or c.endswith('_lng')];flags=[i for i,c in enumerate(nums) if c not in BASE]
        def numeric(v):
            missing=np.isnan(v);filled=np.where(missing,med,v);x=np.where(filled>=0,np.log1p(np.maximum(filled,0)),filled);x[:,raw]=filled[:,raw];return x,missing[:,flags].astype(float)
        x,xm=numeric(a);z,zm=numeric(b);sc=StandardScaler().fit(x[fit]);x=sc.transform(x);z=sc.transform(z)
        parts=[sparse.csr_matrix(np.hstack([x[fit],xm[fit]])),sparse.csr_matrix(np.hstack([x[cal],xm[cal]])),sparse.csr_matrix(np.hstack([z,zm]))]
        names=[dict(view=view,field=c,kind='numeric',original8=c in BASE) for c in nums]+[dict(view=view,field=nums[i],kind='missing',original8=False) for i in flags];encoders={}
        for block,rare in [([c for c in categories if c=='state'],None),([c for c in categories if c!='state'],20)]:
            if not block:continue
            aa=tr[block].fillna('__MISSING__').astype(str);bb=ev[block].fillna('__MISSING__').astype(str)
            en=OneHotEncoder(handle_unknown='ignore' if rare is None else 'infrequent_if_exist',min_frequency=rare,sparse_output=True,dtype=np.float64).fit(aa.iloc[fit]);encoders['state' if rare is None else 'extra']=dict(fields=block,encoder=en)
            for i,v in enumerate([aa.iloc[fit],aa.iloc[cal],bb]):parts[i]=sparse.hstack([parts[i],en.transform(v)],format='csr')
            for field,n in zip(block,en._n_features_outs):names.extend(dict(view=view,field=field,kind='onehot',original8=field=='state') for _ in range(n))
        assert len(names)==parts[0].shape[1]
        for target,part in zip(mats,parts):target.append(part)
        lineage+=names;dims.append(parts[0].shape[1]);trans[view]=dict(numeric=nums,median=med,raw_indices=raw,flag_indices=flags,scaler=sc,encoders=encoders)
    result={p:sparse.hstack(bs,format='csr') for p,bs in zip(['fit','cal','oct'],mats)};mask=np.array([n['original8'] for n in lineage],bool)
    for p,x in result.items():assert np.isfinite(x.data).all();sparse.save_npz(PR/(p+'-full141.npz'),x)
    joblib.dump(trans,PR/'transformers.joblib',compress=3);np.save(PR/'base8-mask.npy',mask);dump('private/lineage.json',lineage)
    # Independent original8 encoding equality, fitted strictly on identical July-fit rows.
    sc=StandardScaler().fit(np.log1p(tr[BASE[:-1]].iloc[fit]));en=OneHotEncoder(handle_unknown='ignore',sparse_output=False).fit(tr[['state']].iloc[fit].astype(str));diffs={}
    for p,f in [('fit',tr.iloc[fit]),('cal',tr.iloc[cal]),('oct',ev)]:
        independent=np.hstack([sc.transform(np.log1p(f[BASE[:-1]])),en.transform(f[['state']].astype(str))]);actual=result[p][:,mask].toarray();diffs[p]=float(np.max(np.abs(independent-actual)));assert diffs[p]<1e-11
    dump('encoding-audit.json',dict(dims=dims,total=sum(dims),base8_encoded=int(mask.sum()),original8_independent_max_abs_difference=diffs,fit_n=len(fit),Oct_used_for_fit=False,fields=spec['views']['full-structure'],views=list(spec['logical_views'])))
    return result,mask,dims
def native(raw,cats):
    nums=[c for c in raw['fit'] if c not in cats];med=raw['fit'][nums].median().fillna(0.);out={}
    for p,f in raw.items():
        x=f.copy()
        for c in cats:x[c]=x[c].astype('string').fillna('__MISSING__').astype(str)
        x[nums]=x[nums].astype(float).fillna(med);assert np.isfinite(x[nums].to_numpy(float)).all();out[p]=x
    dump('private/native-preprocess.json',dict(numeric_median=med.to_dict(),categorical=cats,fit_only=True));return out
def metrics(frame,p,system,variant='calibrated'):
    y=frame.y.to_numpy(int);out=[];masks=[('all',np.ones(len(frame),bool))]
    if 'cluster_id' in frame:masks +=[(f'group{g}',frame.cluster_id.eq(g).to_numpy()) for g in [0,1,2]]+[('long',frame.cluster_id.eq(1).to_numpy())]
    for scope,m in masks:
        yy=y[m];pp=np.asarray(p)[m];out.append(dict(system=system,variant=variant,scope=scope,n=len(yy),positives=int(yy.sum()),mean_probability=float(pp.mean()),logloss=float(log_loss(yy,pp,labels=[0,1])),brier=float(brier_score_loss(yy,pp)),AP=float(average_precision_score(yy,pp)),AUC=float(roc_auc_score(yy,pp)) if 0<yy.sum()<len(yy) else None))
    return out
def capacities(frame,p,system,variant='calibrated'):
    y=frame.y.to_numpy(int);g=frame.cluster_id.to_numpy(int);rank=np.lexsort((frame.snapshot_date.to_numpy(str),frame.customer_unique_id.to_numpy(str),-p));rows=[]
    for policy,k in [('global10',int(np.ceil(.1*len(frame)))),('global5',int(np.ceil(.05*len(frame)))),('global20',int(np.ceil(.2*len(frame)))),('long79',79)]:
        ix=rank[g[rank]==1][:k] if policy=='long79' else rank[:k];denom=int(y[g==1].sum()) if policy=='long79' else int(y.sum());r=dict(system=system,variant=variant,policy=policy,k=k,hits=int(y[ix].sum()),precision=float(y[ix].mean()),recall=float(y[ix].sum()/denom),positive_denominator=denom)
        for group in [0,1,2]:r[f'group{group}_selected']=int((g[ix]==group).sum());r[f'group{group}_hits']=int(y[ix][g[ix]==group].sum())
        rows.append(r)
    return rows
def main():
    frozen=assert_freeze();assert (OUT/'ROOT-READY.json').exists(),'Root READY receipt required before any fit'
    ready=json.loads((OUT/'ROOT-READY.json').read_text());assert ready['source_freeze_sha256']==sha(OUT/'source-freeze.json') and ready['ready'] is True
    assert not (OUT/'execution-started.json').exists(),'Never silently rerun or overwrite execution'
    dump('execution-started.json',dict(status='started',source_freeze_sha256=sha(OUT/'source-freeze.json'),ready_sha256=sha(OUT/'ROOT-READY.json')))
    started=time.perf_counter();spec,frames,fit,cal=load_inputs();mats,mask,dims=encode(spec,frames,fit,cal)
    parts={'fit':frames['july'].iloc[fit].reset_index(drop=True),'cal':frames['july'].iloc[cal].reset_index(drop=True),'oct':frames['oct'].reset_index(drop=True)}
    for p,f in parts.items():f[KEY+['y']+(['cluster_id'] if p=='oct' else [])].to_csv(PR/(p+'-rowkeys.csv'),index=False,lineterminator='\n')
    y=parts['fit'].y.to_numpy(int);dense={p:x.toarray().astype(np.float64) for p,x in mats.items()};base={p:x*mask for p,x in dense.items()};tensors={p:torch.from_numpy(x.astype(np.float32)) for p,x in dense.items()};yt=torch.tensor(y,dtype=torch.float32)
    nativeparts=native({p:f[spec['views']['full-structure']] for p,f in parts.items()},spec['categorical_columns'])
    modelrows=[];curves=[];precurves=[];cbcurves=[];met=[];caps=[];calmet=[];probabilities={};pairs={};calibrationrows=[]
    schedules=[('weightedLR','base8',2026)]+[(fam,'full141',seed) for fam in ['mean','AE','encodedCB','nativeCB'] for seed in SEEDS]
    for family,info,seed in schedules:
        rid=f'{family}__{info}__s{seed}';directory=PR/rid;directory.mkdir();tick=time.perf_counter();meta={};pre_seconds=0.;prehash=None
        if family=='weightedLR':
            with warnings.catch_warnings(record=True) as ws:
                warnings.simplefilter('always');model=LogisticRegression(**LR).fit(base['fit'],y)
            joblib.dump(model,directory/'model.joblib',compress=3);logits={p:np.asarray(model.decision_function(x),np.float64) for p,x in base.items()};meta=dict(parameters=LR,n_iter=model.n_iter_.tolist(),warnings=[str(w.message) for w in ws],input_columns=len(mask),active_columns=int(mask.sum()))
        elif family in ['encodedCB','nativeCB']:
            values=dense if family=='encodedCB' else nativeparts;model=CatBoostClassifier(**(CB|dict(random_seed=seed)));model.fit(values['fit'],y,cat_features=spec['categorical_columns'] if family=='nativeCB' else None);model.save_model(str(directory/'model.cbm'));logits={p:np.asarray(model.predict(x,prediction_type='RawFormulaVal',thread_count=2),np.float64) for p,x in values.items()};trace=model.get_evals_result()['learn']['Logloss'];assert len(trace)==300;cbcurves.extend(dict(run=rid,iteration=i+1,fit_Logloss=v) for i,v in enumerate(trace));meta=dict(parameters=CB|dict(random_seed=seed),actual_parameters=model.get_all_params(),tree_count=model.tree_count_,eval_set_used=False,early_stopping=False)
        else:
            old.seed_all(seed);model=old.Model(dims,family,decoder=family=='AE');init=old.shared_initialization_hash(model)
            if seed in pairs:assert pairs[seed]==init
            else:pairs[seed]=init
            if family=='AE':
                pre,pre_seconds,prehash,initial,final=old.pretrain_AE(model,tensors['fit'],20,seed);precurves.extend(dict(run=rid,seed=seed,**r) for r in pre);torch.save(dict(state_dict=model.state_dict(),dims=dims,kind='AE',decoder=True),directory/'pretrained.pt');model.dec=None
                meta.update(initial_reconstruction_MSE=initial,final_reconstruction_MSE=final)
            trace,sup_seconds,orderhash=old.supervised(model,tensors['fit'],yt,50,seed);curves.extend(dict(run=rid,seed=seed,family=family,**r) for r in trace);logits={p:old.infer(model,x) for p,x in tensors.items()};torch.save(dict(state_dict=model.state_dict(),dims=dims,kind=family,decoder=False),directory/'model.pt');meta.update(initialization_sha256=init,supervised_order_sha256=orderhash,pretrain_order_sha256=prehash,supervised_seconds=sup_seconds,pretrain_seconds=pre_seconds,supervised_epochs=50,pretrain_epochs=20 if family=='AE' else 0,supervised_batch=512,pretrain_batch=256 if family=='AE' else None,Adam_lr=.001,input_dtype='float32',saved_logits_dtype='float64')
        assert all(len(logits[p])==len(parts[p]) and np.isfinite(logits[p]).all() for p in parts)
        calibrator=parent.fit_monotone_platt(logits['cal'],parts['cal'].y.to_numpy());probs={p:parent.apply_calibration(z,calibrator) for p,z in logits.items()};raw={p:expit(z) for p,z in logits.items()}
        np.savez_compressed(directory/'scores.npz',**{p+'_logit':z for p,z in logits.items()},**{p+'_calibrated':v for p,v in probs.items()},**{p+'_raw':v for p,v in raw.items()});dump(f'private/{rid}/calibrator.json',calibrator);dump(f'private/{rid}/metadata.json',dict(run=rid,family=family,information=info,seed=seed,source_freeze_sha256=sha(OUT/'source-freeze.json'),metadata=meta))
        calibrationrows.append(dict(run=rid,family=family,seed=seed,**calibrator));met+=metrics(parts['oct'],probs['oct'],rid);caps+=capacities(parts['oct'],probs['oct'],rid);calmet+=metrics(parts['cal'],probs['cal'],rid)
        if family=='weightedLR':
            for label,pp in [('raw',raw['oct']),('prior',expit(logits['oct']-np.log((len(y)-y.sum())/y.sum())))]:met+=metrics(parts['oct'],pp,rid,label);caps+=capacities(parts['oct'],pp,rid,label)
        probabilities[(family,seed)]=probs
        modelrows.append(dict(run=rid,family=family,information=info,seed=seed,fit_n=len(y),fit_positives=int(y.sum()),cal_n=len(cal),cal_positives=int(parts['cal'].y.sum()),oct_n=len(parts['oct']),seconds=time.perf_counter()-tick,pretrain_seconds=pre_seconds,score_sha256=sha(directory/'scores.npz')))
        pd.DataFrame(modelrows).to_csv(OUT/'run-support.csv',index=False);pd.DataFrame(met).to_csv(OUT/'october-metrics.csv',index=False);pd.DataFrame(caps).to_csv(OUT/'october-capacity.csv',index=False);pd.DataFrame(calibrationrows).to_csv(OUT/'calibration-diagnostics.csv',index=False)
        print('DONE',rid,modelrows[-1]['seconds'],flush=True)
    for family in ['mean','AE','encodedCB','nativeCB']:
        system=family+'__full141__seedmean';pr={p:np.mean([probabilities[(family,s)][p] for s in SEEDS],axis=0) for p in parts};np.savez_compressed(PR/(system+'-probabilities.npz'),**pr);met+=metrics(parts['oct'],pr['oct'],system);caps+=capacities(parts['oct'],pr['oct'],system);calmet+=metrics(parts['cal'],pr['cal'],system)
    assert len(modelrows)==13 and len(precurves)==60 and len(curves)==300
    for rows,name in [(met,'october-metrics.csv'),(caps,'october-capacity.csv'),(calmet,'july-cal-resubstitution-metrics.csv'),(curves,'supervised-curves.csv'),(precurves,'pretrain-curves.csv'),(cbcurves,'catboost-curves.csv')]:pd.DataFrame(rows).to_csv(OUT/name,index=False,lineterminator='\n')
    dump('execution.json',dict(status='execution_complete_independent_readback_pending',models=13,AE_pretraining_runs=3,seconds=time.perf_counter()-started,April_snapshot_label_score_reads=0,Oct_used_for_fit=False,source_freeze_sha256=sha(OUT/'source-freeze.json'),plan_sha256=sha(OUT/'time-validation-plan.md'),CPU_threads=2,dims=dims,init_pairing=pairs,calibrator_readout='July-cal resubstitution',old_audit_unchanged=True))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');p.add_argument('--run',action='store_true');args=p.parse_args();assert args.freeze!=args.run
    torch.set_num_threads(2)
    with threadpool_limits(2):
        if args.freeze:freeze()
        else:
            try:main()
            except Exception as e:dump('failure.json',dict(type=type(e).__name__,message=str(e),traceback=traceback.format_exc()));raise
