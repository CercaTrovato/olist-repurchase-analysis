"""Frozen 12 membership-only heads; no representation/cluster training or April."""
import sys
sys.dont_write_bytecode=True
import hashlib,json,math,time,warnings
from pathlib import Path
import joblib,numpy as np,pandas as pd,torch
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss,brier_score_loss,average_precision_score,roc_auc_score
from threadpoolctl import threadpool_limits
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent;ROOT=OUT.parent;RP=ROOT/'representations/private';KEY=['customer_unique_id','snapshot_date'];INPUTS={}
LR=dict(C=1,solver='lbfgs',tol=1e-10,max_iter=5000,fit_intercept=True,class_weight=None)
PLATT=dict(C=1e6,solver='lbfgs',tol=1e-10,max_iter=2000,fit_intercept=True,class_weight=None)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def source(p):INPUTS[str(p)]=sha(p);return p
def read(p,cols=None):return pd.read_csv(source(p),dtype={KEY[0]:'string'},usecols=cols,float_precision='round_trip')
def csv(f,n):f.to_csv(OUT/n,index=False,lineterminator='\n')
def dump(v,p):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
def rank(f,p):return f[KEY].assign(s=p).sort_values(['s']+KEY,ascending=[False,True,True]).index.to_numpy()
def masks(f):return [('all',np.ones(len(f),bool))]+[(f'cluster_{g}'+('_long' if g==1 else ''),f.cluster_id.eq(g).to_numpy()) for g in [0,1,2]]
def values(y,p):return dict(n=len(y),events=int(y.sum()),prevalence=float(y.mean()),logloss=float(log_loss(y,p,labels=[0,1])),brier=float(brier_score_loss(y,p)),AP=float(average_precision_score(y,p)),AUC=float(roc_auc_score(y,p)),mean_probability=float(p.mean()))
def objective(clf,x,y):
    x=np.asarray(x,dtype=float);z=clf.decision_function(x);r=expit(z)-y;g=np.r_[r.sum(),x.T@r+clf.coef_.ravel()]
    data=float(np.sum(np.logaddexp(0,z)-y*z));pen=.5*float(np.sum(clf.coef_**2))
    return dict(sum_objective=data+pen,sum_BCE=data,fit_mean_BCE=data/len(y),L2_penalty=pen,sum_gradient_max=float(np.max(np.abs(g))),mean_gradient_max=float(np.max(np.abs(g)))/len(y),iterations=int(clf.n_iter_[0]),requested_tol=clf.tol,requested_max_iter=clf.max_iter,observed_mean_gradient_below_requested_tol=bool(np.max(np.abs(g))/len(y)<=clf.tol))
def main():
    start=time.perf_counter();assert (OUT/'plan.md').is_file();torch.set_num_threads(2)
    split=read(RP/'october-split.csv');source(RP/'fit-matrix.npz');source(RP/'cal-matrix.npz')
    keys={'fit':split.loc[split.part.eq('fit'),KEY+['y']].reset_index(drop=True),'cal':split.loc[split.part.eq('cal'),KEY+['y']].reset_index(drop=True)}
    keys['january']=read(ROOT/'features/private/january-features.csv',KEY+['y','cluster_id'])
    y={'fit':np.load(RP/'fit-matrix.npz')['y'].astype(int),'cal':np.load(RP/'cal-matrix.npz')['y'].astype(int),'january':keys['january'].y.to_numpy(int)}
    assert (len(y['fit']),sum(y['fit']),len(y['cal']),sum(y['cal']),len(y['january']),sum(y['january']))==(16928,169,4232,42,29368,230)
    assert keys['fit'].y.eq(y['fit']).all() and keys['cal'].y.eq(y['cal']).all()
    groups=read(ROOT.parent/'is6400-local-round2-20261110/role-04/train_clusters.csv',KEY+['cluster_id'])
    for period in ['fit','cal']:
        keys[period]=keys[period].merge(groups,on=KEY,how='left',validate='one_to_one');assert keys[period].cluster_id.notna().all()
    authority=read(ROOT.parent/'is6400-h05-january-handoff-20261110/validation_clusters.csv',KEY+['cluster_id'])
    check=keys['january'].merge(authority,on=KEY,validate='one_to_one',suffixes=('','_authority'));assert check.cluster_id.eq(check.cluster_id_authority).all()
    assert (keys['january'].cluster_id.eq(1).sum(),keys['january'].loc[keys['january'].cluster_id.eq(1),'y'].sum())==(12330,90)
    for period,f in keys.items():csv(f,f'private/{period}-keys-labels.csv')
    metrics=[];capacities=[];runs=[];fitrows=[];predictions={'cal':{},'january':{}};logits={'cal':{},'january':{}}
    prior=float(y['fit'].mean());constantBCE=float(-prior*np.log(prior)-(1-prior)*np.log1p(-prior))
    def evaluate(name,family,seed,variant,probs,ranks):
        for period in ['cal','january']:
            pp=probs[period];rs=ranks[period];f=keys[period];predictions[period][name]=pp;logits[period][name]=rs
            for scope,mask in masks(f):metrics.append(dict(method=name,family=family,seed=seed,variant=variant,period=period,scope=scope,calibration_resubstitution=period=='cal' and variant=='new_Platt',**values(y[period][mask],pp[mask])))
            if period=='january':
                for scope,mask in [('all',np.ones(len(f),bool)),('cluster_1_long',f.cluster_id.eq(1).to_numpy())]:
                    ff=f.loc[mask].reset_index(drop=True);yy=y[period][mask];ranked=rank(ff,rs[mask])
                    for policy,k in ([('global5',1469),('global10',2937),('global20',5874)] if scope=='all' else [('long79',79)]):
                        hits=int(yy[ranked[:k]].sum());capacities.append(dict(method=name,family=family,seed=seed,variant=variant,scope=scope,policy=policy,k=k,n=len(yy),events=int(yy.sum()),hits=hits,precision=hits/k,recall=hits/yy.sum(),ranking_source='old_raw_logit' if variant=='old_50epoch_raw' else ('new_probability' if variant=='new_Platt' else 'new_raw_logit_or_baseline_probability')))
    oldopt=read(ROOT/'representations/optimization-audit.csv')
    for representation in ['rfm','deep']:
        for membership in ['hard','soft']:
            family=representation+'-'+membership
            for seed in [2026,2027,2028]:
                name=f'{family}-{seed}';members={}
                for period in ['fit','cal','january']:
                    members[period]=np.load(source(RP/f'{name}-{period}-memberships.npy'))
                    assert members[period].shape[0]==len(y[period]) and np.isfinite(members[period]).all()
                    assert members[period].min()>=0 and np.allclose(members[period].sum(1),1,atol=1e-6,rtol=0)
                assert len(set(a.shape[1] for a in members.values()))==1
                oldjan=read(RP/f'{name}-january-scores.csv');oldcal=read(RP/f'{name}-calibration.csv')
                assert keys['january'][KEY+['y','cluster_id']].equals(oldjan[KEY+['y','cluster_id']])
                assert np.array_equal(oldcal.cal_y.to_numpy(int),y['cal'])
                oldstate=torch.load(source(RP/f'{name}.pt'),map_location='cpu',weights_only=True)
                with torch.no_grad():oldfit=torch.nn.functional.linear(torch.tensor(members['fit'],dtype=torch.float32),oldstate['head.weight'],oldstate['head.bias']).squeeze(1).numpy().astype(float)
                oldfitBCE=float(np.mean(np.logaddexp(0,oldfit)-y['fit']*oldfit))
                old_probs={'cal':expit(oldcal.cal_logit.to_numpy(float)),'january':oldjan.raw_probability.to_numpy(float)}
                old_ranks={'cal':oldcal.cal_logit.to_numpy(float),'january':oldjan.raw_logit.to_numpy(float)}
                evaluate(name+'__old_raw',family,seed,'old_50epoch_raw',old_probs,old_ranks)
                began=time.perf_counter()
                with warnings.catch_warnings(record=True) as recorded:
                    warnings.simplefilter('always');clf=LogisticRegression(**LR).fit(members['fit'],y['fit'])
                seconds=time.perf_counter()-began;warn=[dict(category=type(w.message).__name__,message=str(w.message)) for w in recorded]
                z={period:clf.decision_function(members[period]) for period in ['cal','january']};raw={p:expit(z[p]) for p in z}
                with warnings.catch_warnings(record=True) as recorded:
                    warnings.simplefilter('always');calibrator=LogisticRegression(**PLATT).fit(z['cal'].reshape(-1,1),y['cal'])
                plattwarn=[dict(category=type(w.message).__name__,message=str(w.message)) for w in recorded]
                platt={p:calibrator.predict_proba(z[p].reshape(-1,1))[:,1] for p in z}
                evaluate(name+'__new_raw',family,seed,'new_raw',raw,z);evaluate(name+'__new_Platt',family,seed,'new_Platt',platt,platt)
                fitted=objective(clf,members['fit'],y['fit']);row=oldopt.loc[oldopt.candidate.eq(family)&oldopt.seed.eq(seed)].iloc[0]
                fitrows.append(dict(family=family,seed=seed,membership_columns=members['fit'].shape[1],fit_n=len(y['fit']),fit_events=int(y['fit'].sum()),old_logged_epoch50_BCE=float(row.epoch50_BCE),old_final_model_fit_BCE=oldfitBCE,fit_constant_BCE=constantBCE,**fitted))
                artifact=dict(kind='fixed-membership-logistic-control',model=clf,platt=calibrator,family=family,seed=seed,source_membership_files={p:str(RP/f'{name}-{p}-memberships.npy') for p in members},train_parameters=LR,calibration_parameters=PLATT,fit_n=len(y['fit']),fit_events=int(y['fit'].sum()))
                joblib.dump(artifact,OUT/f'private/{name}.joblib',compress=3)
                runs.append(dict(family=family,seed=seed,training_seconds=seconds,fit_parameters=LR,calibration_parameters=PLATT,warnings=warn,platt_warnings=plattwarn,platt_coef=float(calibrator.coef_[0,0]),platt_intercept=float(calibrator.intercept_[0]),**fitted))
                print('HEAD',name,'old fit BCE',round(oldfitBCE,6),'new',round(fitted['fit_mean_BCE'],6),'Jan LL',round(values(y['january'],raw['january'])['logloss'],6),'Platt',round(values(y['january'],platt['january'])['logloss'],6),flush=True)
    # Baselines do not refit calibration, and are determined only by fit labels.
    constant={p:np.full(len(y[p]),prior) for p in ['cal','january']};evaluate('global_fit_prior','baseline',None,'global_fit_prior',constant,constant)
    group_support=[];rates={}
    for g,part in keys['fit'].groupby('cluster_id'):
        count=len(part);events=int(part.y.sum());rates[int(g)]=(events+1)/(count+100);group_support.append(dict(H05_group=int(g),fit_n=count,fit_events=events,Beta_alpha=1,Beta_beta=99,smoothed_prior=rates[int(g)]))
    gp={p:keys[p].cluster_id.map(rates).to_numpy(float) for p in ['cal','january']};evaluate('H05_fit_group_Beta1_99','baseline',None,'H05_fit_group_Beta1_99',gp,gp)
    csv(pd.DataFrame(group_support),'H05-fit-prior-support.csv');dump(dict(global_fit_prior=prior,H05_fit_group_priors=rates),OUT/'private/baseline-priors.json')
    csv(pd.DataFrame(metrics),'metrics.csv');csv(pd.DataFrame(capacities),'capacity.csv');csv(pd.DataFrame(fitrows),'optimization-control.csv');dump(runs,OUT/'run-metadata.json')
    for period in ['cal','january']:
        sf=keys[period].copy();rf=keys[period].copy()
        for n,p in predictions[period].items():sf['score_'+n]=p
        for n,z in logits[period].items():rf['rank_'+n]=z
        csv(sf,f'private/{period}-scores.csv');csv(rf,f'private/{period}-ranking-scores.csv')
    summary=pd.DataFrame(metrics).groupby(['family','variant','period','scope'])[['logloss','brier','AP','AUC']].agg(['mean','std','min','max']);summary.to_csv(OUT/'seed-summary.csv')
    cs=pd.DataFrame(capacities).groupby(['family','variant','scope','policy'])[['hits','precision','recall']].agg(['mean','std','min','max']);cs.to_csv(OUT/'seed-summary-capacity.csv')
    mt=pd.DataFrame(metrics);fig,axes=plt.subplots(1,2,figsize=(12,5));families=['rfm-hard','rfm-soft','deep-hard','deep-soft'];colors=['#b2182b','#2166ac','#1b7837']
    for ax,metric in zip(axes,['logloss','AP']):
        for vi,(variant,color) in enumerate(zip(['old_50epoch_raw','new_raw','new_Platt'],colors)):
            for i,f in enumerate(families):
                pp=mt.loc[mt.family.eq(f)&mt.variant.eq(variant)&mt.period.eq('january')&mt.scope.eq('all'),metric];ax.errorbar(i+(vi-1)*.15,pp.mean(),yerr=pp.std(ddof=1),fmt='o',capsize=3,color=color,label=variant if i==0 else None)
        ax.set_xticks(np.arange(4),families);ax.set_title('Jan '+metric);ax.grid(alpha=.2)
        if metric=='logloss':ax.set_yscale('log')
    axes[0].legend(fontsize=8);fig.suptitle('Fixed memberships: old Adam head vs converged-logistic control');fig.tight_layout()
    for ext in ['png','svg']:fig.savefig(OUT/f'figures/membership-head-control.{ext}',dpi=170)
    plt.close(fig)
    fdf=pd.DataFrame(fitrows);fig,ax=plt.subplots(figsize=(10,5));xx=np.arange(len(fdf));ax.plot(xx,fdf.old_final_model_fit_BCE,'o',label='old head final fit BCE');ax.plot(xx,fdf.fit_mean_BCE,'o',label='new LR fit BCE');ax.axhline(constantBCE,ls='--',color='#777777',label='fit prevalence constant');ax.set_xticks(xx,fdf.family+'-'+fdf.seed.astype(str),rotation=35,ha='right');ax.set_ylabel('Fit mean BCE (training diagnostic only)');ax.legend();ax.grid(alpha=.2);fig.tight_layout()
    for ext in ['png','svg']:fig.savefig(OUT/f'figures/fit-optimization-control.{ext}',dpi=170)
    plt.close(fig)
    assert all(sha(p)==h for p,h in INPUTS.items())
    receipt=dict(status='executed_pending_local_readback',new_membership_head_fits=12,score_variants=38,metric_rows=len(metrics),capacity_rows=len(capacities),fit_n=16928,fit_events=169,cal_n=4232,cal_events=42,jan_n=29368,jan_events=230,H05_long_n=12330,H05_long_events=90,april_rows_parsed=0,representation_or_cluster_fits=0,elapsed_seconds=time.perf_counter()-start,input_sha256=INPUTS,plan_sha256=sha(OUT/'plan.md'),code_sha256=sha(Path(__file__)))
    receipt['output_sha256']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='verification.json'};dump(receipt,OUT/'verification.json')
    print(mt.loc[mt.period.eq('january')&mt.scope.eq('all')].groupby(['family','variant'])[['logloss','brier','AP','AUC']].mean().to_string());print('COMPLETE pending readback',receipt['elapsed_seconds'],flush=True)
if __name__=='__main__':
    with threadpool_limits(limits=2):main()
