"""P4B fixed imbalance/objective matrix; bounded Oct/Jan only, python -B."""
import sys
sys.dont_write_bytecode=True
import hashlib,json,math,runpy,time,traceback
from pathlib import Path
import joblib,numpy as np,pandas as pd
from scipy.special import expit
import torch
from torch import nn
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer,StandardScaler,OneHotEncoder,OrdinalEncoder
from imblearn.over_sampling import RandomOverSampler,SMOTENC
from threadpoolctl import threadpool_limits

OUT=Path(__file__).resolve().parent;ROOT=OUT.parent.parent
KEY=['customer_unique_id','snapshot_date'];NUM=['R','F','M','average_item_rows','freight_share','recent30_orders','recent30_spend'];FIELDS=NUM+['state']
SEEDS=[2026,2027,2028];SPLITSEED=20261111;LR_PARAMS=dict(C=1,max_iter=2000,solver='lbfgs',random_state=2026)
INPUTS={};MODELS={};ROWS=[];CLASS=[];STRATEGY=[];RUNS=[];HISTORY=[];CHANGES=[];FAILURES=[]
SCORES={'oct_cal':{},'jan':{}};LOGITS={'oct_cal':{},'jan':{}};FRAMES={}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def source(p):INPUTS[str(p)]=sha(p);return p
def dump(v,p):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def csv(v,p):v.to_csv(p,index=False,lineterminator='\n')
def makeprep():
    return ColumnTransformer([('numeric',Pipeline([('log1p',FunctionTransformer(np.log1p)),('scale',StandardScaler())]),NUM),('state',OneHotEncoder(handle_unknown='ignore',sparse_output=False),['state'])],sparse_threshold=0)
def rank(f,p):return f[KEY].assign(score=p).sort_values(['score']+KEY,ascending=[False,True,True]).index.to_numpy()
def scopes(f):return [('all',np.ones(len(f),bool))]+[(f'cluster_{g}'+('_long' if g==1 else ''),f.cluster_id.eq(g).to_numpy()) for g in [0,1,2]]

def predict_logit(a,frame):
    if a['kind']=='smotenc-LR':
        xnum=a['numeric'].transform(frame[NUM]);cat=a['ordinal'].transform(frame[['state']]);x=np.column_stack([xnum,a['ohe'].transform(cat)])
    else:x=a['preprocess'].transform(frame[FIELDS])
    if a['kind']=='torch-linear':return x@a['weight'].astype(float)+a['bias']
    return a['model'].decision_function(x)

def evaluate(base,family,seed,variant,scorecal,scorejan,proper,training_seconds,params):
    method=base+'__'+variant
    SCORES['oct_cal'][method]=scorecal;SCORES['jan'][method]=scorejan
    for period,p in [('oct_cal',scorecal),('jan',scorejan)]:
        f=FRAMES[period];y=f.y.to_numpy(int)
        for scope,mask in scopes(f):
            row=dict(period=period,scope=scope,method=method,base=base,family=family,seed=seed,variant=variant,probability_eligible=proper,
                calibration_readout='fitted_on_same_Octcal_labels' if period=='oct_cal' and variant=='Platt' else 'heldout_from_model_fit',
                **METRIC['basic'](y[mask],p[mask],proper))
            ROWS.append(row)
            if proper:CLASS.append({k:row[k] for k in ['period','scope','method','family','seed','variant']}|METRIC['classification'](y[mask],p[mask],.5))
        if period=='jan':
            for scope,mask in [('all',np.ones(len(f),bool)),('cluster_1_long',f.cluster_id.eq(1).to_numpy())]:
                ff=f.loc[mask].reset_index(drop=True);yy=y[mask];ps=p[mask]
                capacities=[(.05,1469),(.1,2937),(.2,5874)] if scope=='all' else [(None,79)]
                for fraction,k in capacities:
                    selected=rank(ff,ps)[:k];hits=int(yy[selected].sum())
                    STRATEGY.append(dict(method=method,base=base,family=family,seed=seed,variant=variant,scope=scope,fraction=fraction,k=k,n=len(yy),events=int(yy.sum()),hits=hits,precision=hits/k,recall=hits/yy.sum()))

def finish_model(base,family,seed,a,seconds,parameters,manifest,prior=False,rank_only=False):
    t=time.perf_counter();cal=FRAMES['oct_cal'];jan=FRAMES['jan'];yc=cal.y.to_numpy(int)
    zc=predict_logit(a,cal);zj=predict_logit(a,jan)
    assert np.isfinite(zc).all() and np.isfinite(zj).all()
    rawc=zc if rank_only else expit(zc);rawj=zj if rank_only else expit(zj)
    LOGITS['oct_cal'][base]=zc;LOGITS['jan'][base]=zj
    evaluate(base,family,seed,'raw-ranking' if rank_only else 'raw',rawc,rawj,not rank_only,seconds,parameters)
    if prior:
        off=math.log(manifest['fit_negative']/manifest['fit_positive'])
        evaluate(base,family,seed,'prior',expit(zc-off),expit(zj-off),True,seconds,parameters)
    calibrator=LogisticRegression(C=1e6,max_iter=2000,solver='lbfgs',class_weight=None,random_state=SPLITSEED).fit(zc.reshape(-1,1),yc)
    pc=calibrator.predict_proba(zc.reshape(-1,1))[:,1];pj=calibrator.predict_proba(zj.reshape(-1,1))[:,1]
    evaluate(base,family,seed,'Platt',pc,pj,True,seconds,parameters)
    a.update(platt=calibrator,fields=FIELDS,manifest=manifest,parameters=parameters,family=family,seed=seed,prior_offset=math.log(manifest['fit_negative']/manifest['fit_positive']) if prior else None)
    joblib.dump(a,OUT/f'private/{base}.joblib',compress=3)
    loaded=joblib.load(OUT/f'private/{base}.joblib');err=float(np.max(np.abs(predict_logit(loaded,jan)-zj)))
    assert err==0
    MODELS[base]=a
    RUNS.append(dict(base=base,family=family,seed=seed,training_seconds=seconds,calibration_and_scoring_seconds=time.perf_counter()-t,
        platt_coef=float(calibrator.coef_[0,0]),platt_intercept=float(calibrator.intercept_[0]),reload_logit_max_error=err,parameters=parameters,manifest=manifest))
    # Raw/prior transformations must keep exact rank except possible numerical saturation ties.
    rraw=rank(jan,rawj)
    for variant,p in [('Platt',pj)]+([('prior',expit(zj-a['prior_offset']))] if prior else []):
        rr=rank(jan,p);before=set(rraw[:2937]);after=set(rr[:2937]);add=sorted(after-before);drop=sorted(before-after)
        CHANGES.append(dict(base=base,comparison='raw_to_'+variant,raw_rank_is_logit=rank_only,top10_added=len(add),top10_dropped=len(drop),positive_calibration_slope=bool(calibrator.coef_[0,0]>0),raw_hits=int(jan.y.iloc[list(before)].sum()),after_hits=int(jan.y.iloc[list(after)].sum())))
        if add or drop:
            z=jan.loc[add+drop,KEY+['cluster_id','y']].copy();z['change']=['added']*len(add)+['dropped']*len(drop);csv(z,OUT/f'private/{base}-raw-to-{variant}-list-changes.csv')
    print('DONE',base,'seconds',round(seconds,3),'LL raw/rank',next(r.get('logloss') for r in ROWS if r['period']=='jan' and r['scope']=='all' and r['base']==base),'Platt',next(r['logloss'] for r in ROWS if r['period']=='jan' and r['scope']=='all' and r['method']==base+'__Platt'),flush=True)

def train_torch(kind,seed,x,y):
    torch.manual_seed(seed);rng=np.random.default_rng(seed)
    head=nn.Linear(x.shape[1],1);nn.init.xavier_uniform_(head.weight);nn.init.zeros_(head.bias)
    optimizer=torch.optim.Adam(head.parameters(),lr=.01)
    xt=torch.tensor(x,dtype=torch.float32);yt=torch.tensor(y,dtype=torch.float32)
    pos=np.flatnonzero(y==1);neg=np.flatnonzero(y==0);weight=len(neg)/len(pos);steps=0
    nsteps=math.ceil(len(y)/1024);start=time.perf_counter()
    for epoch in range(150):
        data_total=0;pen_total=0;units=0
        if kind=='pairwise':
            ip=np.repeat(pos,50);inn=rng.choice(neg,len(ip),replace=True);order=rng.permutation(len(ip));batches=np.array_split(order,nsteps)
        else:
            shuffled=rng.permutation(len(y));batches=[shuffled[i:i+1024] for i in range(0,len(y),1024)]
        # BCE: sixteen 1024-record batches + one 544-record batch; ranking splits 8450 pairs into 17 batches.
        for idx in batches:
            optimizer.zero_grad()
            if kind=='pairwise':
                zp=head(xt[ip[idx]]).squeeze(1);zn=head(xt[inn[idx]]).squeeze(1);loss=torch.nn.functional.softplus(-(zp-zn)).mean();count=len(idx)
            else:
                z=head(xt[idx]).squeeze(1);target=yt[idx]
                if kind=='weighted-BCE':loss=torch.nn.functional.binary_cross_entropy_with_logits(z,target,pos_weight=torch.tensor(weight))
                elif kind=='focal':
                    bce=torch.nn.functional.binary_cross_entropy_with_logits(z,target,reduction='none');pt=torch.exp(-bce);loss=(.5*(1-pt)**2*bce).mean()
                else:loss=torch.nn.functional.binary_cross_entropy_with_logits(z,target)
                count=len(idx)
            penalty=.001*head.weight.square().sum()/2;objective=loss+penalty
            objective.backward();optimizer.step();steps+=1
            data_total+=loss.item()*count;pen_total+=penalty.item()*count;units+=count
        HISTORY.append(dict(family='torch-'+kind,seed=seed,epoch=epoch+1,data_loss=data_total/units,L2=pen_total/units,units=units,unit_kind='pair' if kind=='pairwise' else 'customer',steps=nsteps))
        if (epoch+1)%50==0:print('TRAIN','torch-'+kind,seed,'epoch',epoch+1,'loss',round(data_total/units,6),flush=True)
    a=dict(kind='torch-linear',preprocess=PREP,weight=head.weight.detach().numpy().ravel().copy(),bias=float(head.bias.detach().numpy()[0]),state_dict={k:v.detach().cpu() for k,v in head.state_dict().items()})
    params=dict(objective=kind,seed=seed,epochs=150,batch_size_max=1024,updates_per_epoch=nsteps,total_updates=steps,Adam_lr=.01,
        L2_coefficient=.001,L2_convention='0.5*lambda*sum(weight**2); bias excluded',pos_weight=weight if kind=='weighted-BCE' else None,
        focal_gamma=2 if kind=='focal' else None,focal_alpha=.5 if kind=='focal' else None,pairs_per_epoch=len(pos)*50 if kind=='pairwise' else None,
        ranking_negative_sampling='with replacement, 50 per positive, fit only, redraw each epoch' if kind=='pairwise' else None,
        batch_sizes=[len(b) for b in batches],initialization='Xavier uniform weight, zero bias',input_features=x.shape[1],torch_threads=torch.get_num_threads(),training_device='cpu')
    return a,time.perf_counter()-start,params

def main():
    global METRIC,PREP
    assert (OUT/'frozen-plan.md').is_file();start=time.perf_counter();torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
    METRIC=runpy.run_path(str(source(ROOT/'is6400-validation-20261111/probability/run_probability.py')))
    bounded=runpy.run_path(str(source(ROOT/'is6400-rfm-weighted-2x2-20261110/run_rfm_2x2.py')))
    source(bounded['TEAM']/'H02_candidate_v2.zip');october,jan=bounded['read_dev']()
    for which,path in [('oct',ROOT/'is6400-local-round2-20261110/role-04/train_clusters.csv'),('jan',bounded['H05'])]:
        f=october if which=='oct' else jan;g=pd.read_csv(source(path),dtype={KEY[0]:'string'})
        f=f.merge(g[KEY+['cluster_id']],on=KEY,how='outer',validate='one_to_one',indicator='_g');assert f._g.eq('both').all();f=f.drop(columns='_g').reset_index(drop=True)
        if which=='oct':october=f
        else:jan=f
    fit_idx,cal_idx=train_test_split(np.arange(len(october)),test_size=.2,stratify=october.y,random_state=SPLITSEED)
    fit=october.iloc[fit_idx].reset_index(drop=True);cal=october.iloc[cal_idx].reset_index(drop=True)
    assert (len(fit),len(cal),len(jan),int(jan.y.sum()))==(16928,4232,29368,230)
    assert (len(jan.query('cluster_id==1')),int(jan.query('cluster_id==1').y.sum()))==(12330,90)
    FRAMES.update(oct_cal=cal,jan=jan)
    manifest=october[KEY+['cluster_id','y']].copy();manifest['split']='';manifest.loc[fit_idx,'split']='fit';manifest.loc[cal_idx,'split']='cal';manifest['original_oct_index']=np.arange(len(october));csv(manifest,OUT/'private/october-fit-cal-manifest.csv')
    assert set(fit[KEY[0]]).isdisjoint(set(cal[KEY[0]]))
    y=fit.y.to_numpy(int);npos=int(y.sum());nneg=len(y)-npos
    counts=dict(fit_n=len(fit),fit_positive=npos,fit_negative=nneg,cal_n=len(cal),cal_positive=int(cal.y.sum()),original_positive_prior=npos/len(fit),sampling_target='balanced1to1')
    PREP=makeprep();x=PREP.fit_transform(fit[FIELDS]);assert np.isfinite(x).all()
    joblib.dump(dict(preprocessor=PREP,features=FIELDS,fit_keys=fit[KEY].to_dict('records')),OUT/'private/fit-only-preprocessor.joblib',compress=3)
    np.savez_compressed(OUT/'private/fit-transformed-original.npz',X=x,y=y,fit_original_indices=fit_idx,cal_original_indices=cal_idx)
    print('SPLIT',counts,'input dimension',x.shape[1],flush=True)
    # Fixed deterministic baselines; fit once, no invented seed variation.
    for family,balance in [('LR-unweighted',False),('LR-balanced',True)]:
        t=time.perf_counter();clf=LogisticRegression(**LR_PARAMS,class_weight='balanced' if balance else None).fit(x,y)
        assert clf.n_iter_.max()<LR_PARAMS['max_iter']
        a=dict(kind='LR',preprocess=PREP,model=clf)
        finish_model(family,family,None,a,time.perf_counter()-t,LR_PARAMS|dict(class_weight='balanced' if balance else None),counts|dict(training_rows=len(y),synthetic_rows=0,duplicated_rows=0),prior=balance)
    # Replication uses original transformed fit rows only; preprocessing never sees cal.
    for seed in SEEDS:
        t=time.perf_counter();sampler=RandomOverSampler(random_state=seed,sampling_strategy='auto');xr,yr=sampler.fit_resample(x,y)
        assert yr.sum()==len(yr)/2 and np.array_equal(xr,x[sampler.sample_indices_])
        np.savez_compressed(OUT/f'private/ROS-seed{seed}-training-indices.npz',sample_indices=sampler.sample_indices_)
        clf=LogisticRegression(**LR_PARAMS).fit(xr,yr);assert clf.n_iter_.max()<LR_PARAMS['max_iter']
        finish_model(f'ROS-LR-seed{seed}','ROS-LR',seed,dict(kind='LR',preprocess=PREP,model=clf,sampler=sampler),time.perf_counter()-t,LR_PARAMS|dict(sampling='RandomOverSampler',sampling_seed=seed),counts|dict(training_rows=len(yr),synthetic_rows=0,duplicated_rows=len(yr)-len(y)),prior=True)
    # SMOTENC state is categorical before resampling, not an interpolated OHE coordinate.
    numeric=Pipeline([('log1p',FunctionTransformer(np.log1p)),('scale',StandardScaler())]).fit(fit[NUM])
    ordinal=OrdinalEncoder(handle_unknown='use_encoded_value',unknown_value=-1).fit(fit[['state']])
    state=ordinal.transform(fit[['state']]);mixed=np.column_stack([numeric.transform(fit[NUM]),state])
    ohe=OneHotEncoder(handle_unknown='ignore',sparse_output=False).fit(state)
    for seed in SEEDS:
        try:
            t=time.perf_counter();sampler=SMOTENC(categorical_features=[len(NUM)],random_state=seed,k_neighbors=5,sampling_strategy='auto')
            mixedr,yr=sampler.fit_resample(mixed,y)
            assert yr.sum()==len(yr)/2 and np.array_equal(mixedr[:len(y)],mixed)
            assert np.isin(mixedr[:,len(NUM)],state.ravel()).all()
            xr=np.column_stack([mixedr[:,:len(NUM)],ohe.transform(mixedr[:,len(NUM):])])
            np.savez_compressed(OUT/f'private/SMOTENC-LR-seed{seed}-training.npz',X_mixed=mixedr,y=yr,original_rows=len(y),synthetic_start=len(y))
            clf=LogisticRegression(**LR_PARAMS).fit(xr,yr);assert clf.n_iter_.max()<LR_PARAMS['max_iter']
            a=dict(kind='smotenc-LR',numeric=numeric,ordinal=ordinal,ohe=ohe,model=clf,sampler=sampler)
            finish_model(f'SMOTENC-LR-seed{seed}','SMOTENC-LR',seed,a,time.perf_counter()-t,LR_PARAMS|dict(sampling='SMOTENC',sampling_seed=seed,k_neighbors=5,categorical_features=[len(NUM)],categorical_legal_values=np.unique(state).astype(int).tolist()),counts|dict(training_rows=len(yr),synthetic_rows=len(yr)-len(y),duplicated_rows=0),prior=True)
        except Exception as e:
            FAILURES.append(dict(method=f'SMOTENC-LR-seed{seed}',error=repr(e),traceback=traceback.format_exc()));print('FAILED SMOTENC',seed,repr(e),flush=True)
    # Same feature map, head, initialization seed, update count, and weight penalty; objective changes only.
    for seed in SEEDS:
        for objective in ['BCE','weighted-BCE','focal','pairwise']:
            a,seconds,params=train_torch(objective,seed,x,y)
            finish_model(f'torch-{objective}-seed{seed}','torch-'+objective,seed,a,seconds,params,counts|dict(training_rows=len(y),synthetic_rows=0,duplicated_rows=0),prior=objective=='weighted-BCE',rank_only=objective=='pairwise')
    # Deterministic near-tie diagnostic: the same fit, preprocessing, solver, and parameters.
    original=MODELS['LR-balanced']['model'];ref=original.predict_proba(PREP.transform(jan[FIELDS]))[:,1]
    ties=[]
    for threads in [1,2]:
        with threadpool_limits(limits=threads):repeat=LogisticRegression(**LR_PARAMS,class_weight='balanced').fit(x,y)
        re=repeat.predict_proba(PREP.transform(jan[FIELDS]))[:,1];ob=rank(jan,ref);orr=rank(jan,re);s1=set(ob[:2937]);s2=set(orr[:2937]);ids=sorted(s1.symmetric_difference(s2))
        z=jan.loc[ids,KEY+['cluster_id','y']].copy();z['baseline_score']=ref[ids];z['repeat_score']=re[ids];z['baseline_selected']=[i in s1 for i in ids];z['repeat_selected']=[i in s2 for i in ids];csv(z,OUT/f'private/LR-balanced-repeat-threads{threads}-changes.csv')
        ties.append(dict(repeat_threads=threads,max_absolute_score_error=float(np.max(np.abs(re-ref))),top10_changed=len(ids),baseline_hits=int(jan.y.iloc[list(s1)].sum()),repeat_hits=int(jan.y.iloc[list(s2)].sum()),baseline_boundary_gap=float(ref[ob[2936]]-ref[ob[2937]])))
    # Clearly separate historical full-Oct training population from current fit-only run.
    old=pd.read_csv(source(ROOT/'is6400-round3-20261111/baselines/private/january-scores.csv'),dtype={KEY[0]:'string'},float_precision='round_trip')
    z=jan[KEY+['y']].merge(old[KEY+['score_weightedLR']],on=KEY,validate='one_to_one');hist=z.score_weightedLR.to_numpy();ob=rank(jan,hist);on=rank(jan,ref);sb=set(ob[:2937]);sn=set(on[:2937]);ids=sorted(sb.symmetric_difference(sn))
    change=jan.loc[ids,KEY+['cluster_id','y']].copy();change['old_fullOct_selected']=[i in sb for i in ids];change['new_fitOnly_selected']=[i in sn for i in ids];csv(change,OUT/'private/LR-balanced-history-fullOct-vs-fitOnly-changes.csv')
    dump(dict(same_fit_repeat=ties,historical_fullOct_comparison=dict(reason='different training population 21160 vs16928, not numerical noise',changed=len(ids),fullOct_hits=int(jan.y.iloc[list(sb)].sum()),fitOnly_hits=int(jan.y.iloc[list(sn)].sum()))),OUT/'balanced-LR-list-sensitivity.json')
    csv(pd.DataFrame(ROWS),OUT/'metrics-all-scopes.csv');csv(pd.DataFrame(CLASS),OUT/'classification-0.5.csv');csv(pd.DataFrame(STRATEGY),OUT/'strategy-capacities.csv');csv(pd.DataFrame(HISTORY),OUT/'training-history.csv');csv(pd.DataFrame(CHANGES),OUT/'calibration-list-changes.csv')
    for period,frame in FRAMES.items():
        s=frame[KEY+['cluster_id','y']].copy()
        for method,p in SCORES[period].items():s['score_'+method]=p
        csv(s,OUT/f'private/{period}-scores.csv')
        zz=frame[KEY+['cluster_id','y']].copy()
        for base,z in LOGITS[period].items():zz['logit_'+base]=z
        csv(zz,OUT/f'private/{period}-logits.csv')
    # Save natural fit prior without changing the trained candidate count.
    const=[]
    for period,f in FRAMES.items():
        for scope,mask in scopes(f):const.append(dict(period=period,scope=scope,method='constant_fit_prior',**METRIC['basic'](f.y.to_numpy()[mask],np.full(mask.sum(),npos/len(y)),True)))
    csv(pd.DataFrame(const),OUT/'constant-reference.csv')
    dump(RUNS,OUT/'run-metadata.json');dump(FAILURES,OUT/'failures.json')
    assert all(sha(p)==h for p,h in INPUTS.items())
    dump(dict(status='complete_with_recorded_failures' if FAILURES else 'complete',elapsed_seconds=time.perf_counter()-start,
        fit_counts=counts,january_n=len(jan),january_events=int(jan.y.sum()),base_runs=len(RUNS),score_variants=len(SCORES['jan']),seeds=SEEDS,split_seed=SPLITSEED,
        input_sha256=INPUTS,april_snapshot_rows_parsed=0,april_label_rows_parsed=0,jan_used_for_hyperparameter_or_calibration_fit=False,
        octave_calibration='heldout Oct20 percent; all preprocessing fit only on Oct80; Platt in-sample cal metrics are diagnostic',
        sklearn_version=__import__('sklearn').__version__,imblearn_version=__import__('imblearn').__version__,torch_version=torch.__version__,script_sha256=sha(Path(__file__)),frozen_plan_sha256=sha(OUT/'frozen-plan.md')),OUT/'verification.json')
    print('COMPLETE base runs',len(RUNS),'variants',len(SCORES['jan']),'seconds',time.perf_counter()-start,flush=True)

if __name__=='__main__':
    with threadpool_limits(limits=2):main()
