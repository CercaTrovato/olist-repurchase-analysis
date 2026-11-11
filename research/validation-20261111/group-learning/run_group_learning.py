"""Frozen P4A: fit-only representation/groups, calibration-only Platt, seen January diagnostics."""
import hashlib
import importlib.util
import json
import math
import time
import warnings
from pathlib import Path

import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit, logit
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss, log_loss, roc_auc_score,
                             silhouette_score)
from sklearn.mixture import GaussianMixture
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits
import torch
from torch import nn

OUT=Path(__file__).resolve().parent
P=OUT/'private'
P.mkdir(parents=True,exist_ok=True)
KEY=['customer_unique_id','snapshot_date']
FEATURES=['R','F','M','average_item_rows','freight_share','recent30_orders','recent30_spend','state']
ETA=.1

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def dump(name,obj): (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def csv(name,rows): pd.DataFrame(rows).to_csv(OUT/name,index=False,lineterminator='\n')

def preprocessor(rfm=False):
    logscale=Pipeline([('log1p',FunctionTransformer(np.log1p,feature_names_out='one-to-one')),('scale',StandardScaler())])
    if rfm: return ColumnTransformer([('R',StandardScaler(),['R']),('FM',logscale,['F','M'])],sparse_threshold=0)
    return ColumnTransformer([('num',logscale,FEATURES[:-1]),('state',OneHotEncoder(sparse_output=False,handle_unknown='ignore'),['state'])],sparse_threshold=0)

def onehot(lab,k): return np.eye(k)[lab]

def correlation_init(X,y,W):
    """Soft support uses weighted covariance and effective positive mass; hard W is exact group corr."""
    out=np.zeros((W.shape[1],X.shape[1]))
    stats=[]
    for g in range(W.shape[1]):
        weight=W[:,g]
        mass=weight.sum()
        pos=weight@y
        mx=weight@X/mass
        my=pos/mass
        vx=weight@((X-mx)**2)/mass
        vy=(weight@((y-my)**2))/mass
        cov=weight@((X-mx)*(y-my)[:,None])/mass
        denom=np.sqrt(vx*vy)
        corr=np.divide(cov,denom,out=np.zeros_like(cov),where=denom>1e-14)
        out[g]=np.clip(corr,-1,1)*pos/(pos+20)
        stats.append(dict(group=g,mass=float(mass),positive_mass=float(pos),rate=float(my),shrink=float(pos/(pos+20)),
                          effective_n=float(mass**2/(weight@weight)),constant_columns=int((denom<=1e-14).sum())))
    return out,stats

def fit_linear(name,X,y,W=None,mode='base',initial=None,fixed=None,balanced=False):
    n,d=X.shape
    g=0 if W is None or mode in ('base','fixed') else W.shape[1]
    q=d if mode=='slope' else 1
    size=1+d+g*q
    theta=np.zeros(size)
    theta[0]=float(logit(y.mean()))
    if initial is not None and g: theta[1+d:]=initial.ravel()
    weight=(np.where(y==1,n/(2*y.sum()),n/(2*(n-y.sum()))) if balanced else np.ones(n))
    offset=np.zeros(n) if fixed is None else ETA*np.sum(W*(X@fixed.T),axis=1)
    def objective(t):
        z=t[0]+X@t[1:1+d]+offset
        delta=t[1+d:].reshape(g,q) if g else None
        if mode=='slope': z+=ETA*np.sum(W*(X@delta.T),axis=1)
        if mode=='intercept': z+=ETA*(W@delta[:,0])
        residual=(expit(z)-y)*weight
        value=float(np.sum(weight*(np.logaddexp(0,z)-y*z))+.5*np.sum(t[1:]**2))
        grad=np.empty_like(t)
        grad[0]=residual.sum()
        grad[1:1+d]=X.T@residual+t[1:1+d]
        if mode=='slope': grad[1+d:]=(ETA*(W.T@(residual[:,None]*X))+delta).ravel()
        if mode=='intercept': grad[1+d:]=ETA*(W.T@residual)+delta[:,0]
        return value,grad
    started=time.time()
    result=minimize(objective,theta,jac=True,method='L-BFGS-B',options={'maxiter':1000,'ftol':1e-12,'gtol':1e-7,'maxls':40})
    value,grad=objective(result.x)
    model=dict(name=name,mode=mode,theta=result.x,d=d,g=g,q=q,fixed=fixed,eta=ETA)
    np.savez_compressed(P/f'{name}-linear.npz',theta=result.x,mode=np.array(mode),d=np.array(d),g=np.array(g),q=np.array(q),
                        fixed=np.zeros((0,d)) if fixed is None else fixed,eta=np.array(ETA))
    info=dict(name=name,family='convex_linear',seed=None,parameters=size,fitted_parameters=size,success=bool(result.success),
        message=str(result.message),iterations=int(result.nit),objective=value,gradient_max=float(np.max(np.abs(grad))),
        fit_seconds=time.time()-started,balanced=balanced,init='corr' if initial is not None else 'zero')
    return model,info

def linear_score(model,X,W=None):
    d,g,q=model['d'],model['g'],model['q']
    t=model['theta']
    z=t[0]+X@t[1:1+d]
    if model['fixed'] is not None: z+=ETA*np.sum(W*(X@model['fixed'].T),axis=1)
    if model['mode']=='slope': z+=ETA*np.sum(W*(X@t[1+d:].reshape(g,q).T),axis=1)
    if model['mode']=='intercept': z+=ETA*(W@t[1+d:])
    return z

class Residual(nn.Module):
    def __init__(self,d,g,nonlinear):
        super().__init__()
        self.base=nn.Linear(d,1)
        self.hidden=nn.Linear(d,16)
        self.group_head=nn.Parameter(torch.zeros(g,16))
        self.nonlinear=nonlinear
    def forward(self,x,w):
        h=self.hidden(x)
        if self.nonlinear: h=torch.relu(h)
        return self.base(x).flatten()+ETA*torch.sum((w@self.group_head)*h,dim=1)

def fit_residual(name,X,y,W,base,seed,nonlinear):
    torch.manual_seed(seed)
    torch.set_num_threads(2)
    model=Residual(X.shape[1],W.shape[1],nonlinear)
    with torch.no_grad():
        model.base.weight.copy_(torch.tensor(base['theta'][1:1+X.shape[1]],dtype=torch.float32).reshape(1,-1))
        model.base.bias.copy_(torch.tensor([base['theta'][0]],dtype=torch.float32))
    xt,yt,wt=(torch.tensor(v,dtype=torch.float32) for v in (X,y,W))
    generator=torch.Generator().manual_seed(seed)
    optimizer=torch.optim.Adam(model.parameters(),lr=.001)
    started=time.time()
    trajectory=[]
    for epoch in range(50):
        model.train()
        order=torch.randperm(len(X),generator=generator)
        for idx in order.split(512):
            optimizer.zero_grad()
            prediction=model(xt[idx],wt[idx])
            reg=(model.base.weight.square().sum()+model.hidden.weight.square().sum()+model.group_head.square().sum())/(2*len(X))
            loss=nn.functional.binary_cross_entropy_with_logits(prediction,yt[idx])+reg
            loss.backward()
            optimizer.step()
        model.eval()
        with torch.no_grad():
            fitted=model(xt,wt)
            bce=nn.functional.binary_cross_entropy_with_logits(fitted,yt).item()
        trajectory.append(dict(name=name,seed=seed,epoch=epoch+1,fit_mean_bce=bce))
    torch.save(dict(state_dict=model.state_dict(),d=X.shape[1],g=W.shape[1],nonlinear=nonlinear,eta=ETA,seed=seed),P/f'{name}-torch.pt')
    info=dict(name=name,family='shared_residual_relu' if nonlinear else 'shared_residual_identity',seed=seed,
        parameters=sum(v.numel() for v in model.parameters()),fitted_parameters=sum(v.numel() for v in model.parameters()),
        success=True,message='fixed_epoch_budget_completed_not_convergence_claim',iterations=50,objective=bce,
        gradient_max=None,fit_seconds=time.time()-started,balanced=False,init='matched_LR_base_zero_group_head')
    return model,info,trajectory

def natural_metrics(y,prob):
    prob=np.clip(np.asarray(prob,dtype=float),1e-15,1-1e-15)
    pred=prob>=.5
    tp=int(np.sum(pred&(y==1))); fp=int(np.sum(pred&(y==0)))
    fn=int(np.sum(~pred&(y==1))); tn=int(np.sum(~pred&(y==0)))
    precision=tp/(tp+fp) if tp+fp else 0
    recall=tp/(tp+fn)
    ece=0.
    for lo,hi in zip(np.arange(10)/10,np.arange(1,11)/10):
        inside=(prob>=lo)&((prob<hi) if hi<1 else (prob<=hi))
        if inside.any(): ece+=inside.mean()*abs(prob[inside].mean()-y[inside].mean())
    return dict(n=len(y),positives=int(y.sum()),prevalence=float(y.mean()),log_loss=log_loss(y,prob,labels=[0,1]),
        brier=brier_score_loss(y,prob),ap=average_precision_score(y,prob),roc_auc=roc_auc_score(y,prob),ece10=ece,
        mean_probability=float(prob.mean()),calibration_in_the_large=float(prob.mean()-y.mean()),
        tp=tp,fp=fp,fn=fn,tn=tn,precision_05=precision,recall_05=recall,
        f1_05=2*precision*recall/(precision+recall) if precision+recall else 0)

def rank_metrics(frame,prob,k):
    chosen=frame[KEY].assign(score=prob).sort_values(['score']+KEY,ascending=[False,True,True]).head(k).index
    hits=int(frame.loc[chosen,'y'].sum())
    prev=frame.y.mean()
    return dict(n=len(frame),positives=int(frame.y.sum()),k=k,hits=hits,precision=hits/k,recall=hits/frame.y.sum(),
                lift=(hits/k)/prev,random_expected_hits=k*prev)

def main():
    began=time.time()
    torch.set_num_threads(2)
    source=Path('E:/app-data/codex/outputs/is6400-rfm-weighted-2x2-20261110/run_rfm_2x2.py')
    spec=importlib.util.spec_from_file_location('frozen_development_reader',source)
    base=importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
    oct,jan=base.read_dev(); oct=oct.reset_index(drop=True)
    h05path=Path('E:/app-data/codex/outputs/is6400-h05-january-handoff-20261110/validation_clusters.csv')
    jan=jan.merge(pd.read_csv(h05path,dtype={'customer_unique_id':'string'}),on=KEY,validate='one_to_one')
    fitidx,calidx=train_test_split(np.arange(len(oct)),test_size=.2,stratify=oct.y,random_state=20261111)
    fit=oct.iloc[fitidx].reset_index(drop=True); cal=oct.iloc[calidx].reset_index(drop=True)
    assert (len(fit),len(cal))==(16928,4232)
    assert jan.cluster_id.eq(1).sum()==12330 and jan.loc[jan.cluster_id.eq(1),'y'].sum()==90
    np.savez_compressed(P/'split_indices.npz',fit=fitidx,cal=calidx)
    for name,frame in [('fit',fit),('cal',cal),('jan',jan)]:
        columns=KEY+['y']+(['cluster_id'] if name=='jan' else [])
        frame[columns].to_csv(P/f'{name}-keys-outcomes.csv',index=False,lineterminator='\n')
    geometry=[]; groupstats=[]; corrrows=[]; modelinfo=[]; trajectory=[]; natural=[]; ranking=[]; calibration=[]
    models={}; scoredata={}; selection={}
    with threadpool_limits(limits=2):
        transformer=preprocessor(); X=transformer.fit_transform(fit); C=transformer.transform(cal); J=transformer.transform(jan)
        rprep=preprocessor(True); R=rprep.fit_transform(fit); RC=rprep.transform(cal); RJ=rprep.transform(jan)
        joblib.dump(transformer,P/'original8-fit-transformer.joblib'); joblib.dump(rprep,P/'rfm-fit-transformer.joblib')
        np.savez_compressed(P/'features.npz',fit=X,cal=C,jan=J,rfm_fit=R,rfm_cal=RC,rfm_jan=RJ)
        names=transformer.get_feature_names_out()
        (P/'feature_names.json').write_text(json.dumps(list(names),indent=2)+'\n',encoding='utf-8')
        y=fit.y.to_numpy(dtype=float)
        sample=np.sort(np.random.default_rng(2026).choice(len(fit),2000,replace=False))
        km={}; gm={}
        for k in range(2,9):
            km[k]=KMeans(n_clusters=k,random_state=42,n_init=20,max_iter=300,tol=1e-4,algorithm='lloyd').fit(R)
            gm[k]=GaussianMixture(n_components=k,covariance_type='diag',random_state=42,n_init=1,max_iter=300,reg_covar=1e-6).fit(R)
            geometry.append(dict(k=k,silhouette=silhouette_score(R[sample],km[k].labels_[sample]),bic=gm[k].bic(R),
                gmm_converged=bool(gm[k].converged_),gmm_iter=int(gm[k].n_iter_)))
            joblib.dump(km[k],P/f'rfm-fit-kmeans-k{k}.joblib'); joblib.dump(gm[k],P/f'rfm-fit-gmm-k{k}.joblib')
        best=max(row['silhouette'] for row in geometry)
        kwinner=min(row['k'] for row in geometry if best-row['silhouette']<=.001)
        gwinner=min(geometry,key=lambda row:row['bic'])['k']
        selection=dict(kmeans_winner=kwinner,gmm_winner=gwinner,fit_n=len(fit),cal_n=len(cal),fit_positive=int(y.sum()),cal_positive=int(cal.y.sum()),
                       feature_dimensions=X.shape[1],prior_probability=float(y.mean()),silhouette_sample_seed=2026)
        dump('selection.json',selection); csv('group_selection.csv',geometry)
        groups={}
        for groupname,algorithm,k in [('hard3','kmeans',3),('hard_geometry','kmeans',kwinner),('soft_bic','gmm',gwinner)]:
            model=km[k] if algorithm=='kmeans' else gm[k]
            W={name:onehot(model.predict(xx),k) if algorithm=='kmeans' else model.predict_proba(xx) for name,xx in [('fit',R),('cal',RC),('jan',RJ)]}
            init,stats=correlation_init(X,y,W['fit'])
            groups[groupname]=(W,init)
            np.savez_compressed(P/f'{groupname}-weights-init.npz',**W,corr_init=init)
            for row in stats: groupstats.append(dict(grouping=groupname,**row))
            for g in range(k):
                for j,feature in enumerate(names): corrrows.append(dict(grouping=groupname,group=g,feature=feature,tilde_c=float(init[g,j])))
        csv('group_fit_support.csv',groupstats); csv('correlation_initialization.csv',corrrows)
        lr,info=fit_linear('lr_unweighted',X,y); models['lr_unweighted']=lr; modelinfo.append(info)
        weighted,info=fit_linear('lr_balanced',X,y,balanced=True); models['lr_balanced']=weighted; modelinfo.append(info)
        declarations=[('hard3_fixedcorr','hard3','fixed',None),('hard3_delta_zero','hard3','slope',False),
            ('hard3_delta_corr','hard3','slope',True),('hard_geometry_delta_corr','hard_geometry','slope',True),
            ('soft_bic_delta_corr','soft_bic','slope',True),('hard3_intercept','hard3','intercept',False)]
        groupmap={}
        for name,grouping,mode,corrstart in declarations:
            W,init=groups[grouping]
            initial=init if corrstart else None
            model,info=fit_linear(name,X,y,W['fit'],mode,initial=initial,fixed=init if mode=='fixed' else None)
            models[name]=model; groupmap[name]=grouping; modelinfo.append(info)
            print('LINEAR',name,info['iterations'],info['success'],info['gradient_max'],flush=True)
        for name,model in models.items():
            grouping=groupmap.get(name)
            scoredata[name]={period:linear_score(model,xx,None if grouping is None else groups[grouping][0][period])
                             for period,xx in [('cal',C),('jan',J)]}
        scoredata['lr_balanced_prior']={period:z+logit(y.mean()) for period,z in scoredata['lr_balanced'].items()}
        modelinfo.append(dict(name='lr_balanced_prior',family='prior_corrected_balanced_LR',seed=None,parameters=1+X.shape[1],
            fitted_parameters=0,success=True,message='fixed_train_prior_offset_no_new_fit',iterations=0,objective=None,gradient_max=None,fit_seconds=0,balanced=True,init=None))
        scoredata['constant_fit_prior']={period:np.full(len(xx),logit(y.mean())) for period,xx in [('cal',C),('jan',J)]}
        modelinfo.append(dict(name='constant_fit_prior',family='constant',seed=None,parameters=1,fitted_parameters=1,success=True,
            message='fit_prevalence',iterations=0,objective=None,gradient_max=None,fit_seconds=0,balanced=False,init=None))
        initdiff=dict(objective_zero=next(r['objective'] for r in modelinfo if r['name']=='hard3_delta_zero'),
            objective_corr=next(r['objective'] for r in modelinfo if r['name']=='hard3_delta_corr'),
            max_parameter_difference=float(np.max(np.abs(models['hard3_delta_zero']['theta']-models['hard3_delta_corr']['theta']))),
            max_cal_logit_difference=float(np.max(np.abs(scoredata['hard3_delta_zero']['cal']-scoredata['hard3_delta_corr']['cal']))),
            max_jan_probability_difference=float(np.max(np.abs(expit(scoredata['hard3_delta_zero']['jan'])-expit(scoredata['hard3_delta_corr']['jan'])))))
        dump('convex_initialization_comparison.json',initdiff)
        for nonlinear in [False,True]:
            for seed in [2026,2027,2028]:
                name=f"residual_{'relu' if nonlinear else 'identity'}_s{seed}"
                model,info,trace=fit_residual(name,X,y,groups['hard3'][0]['fit'],lr,seed,nonlinear)
                modelinfo.append(info); trajectory.extend(trace)
                with torch.no_grad():
                    scoredata[name]={period:model(torch.tensor(xx,dtype=torch.float32),torch.tensor(groups['hard3'][0][period],dtype=torch.float32)).numpy().astype(float)
                                     for period,xx in [('cal',C),('jan',J)]}
                print('RESIDUAL',name,info['fit_seconds'],flush=True)
        for name,pred in scoredata.items():
            calibrator=LogisticRegression(C=1e6,solver='lbfgs',max_iter=1000,tol=1e-10).fit(pred['cal'].reshape(-1,1),cal.y)
            joblib.dump(calibrator,P/f'{name}-platt.joblib')
            calibration.append(dict(name=name,coef=float(calibrator.coef_[0,0]),intercept=float(calibrator.intercept_[0]),
                                    n=int(len(cal)),positives=int(cal.y.sum()),iterations=int(calibrator.n_iter_[0])))
            artifact={}
            for period,frame in [('cal',cal),('jan',jan)]:
                z=pred[period]; raw=expit(z); calibrated=calibrator.predict_proba(z.reshape(-1,1))[:,1]
                artifact[f'{period}_logit']=z; artifact[f'{period}_raw']=raw; artifact[f'{period}_platt']=calibrated
                for scale,prob in [('raw',raw),('platt',calibrated)]:
                    natural.append(dict(name=name,period=period,scale=scale,calibration_resubstitution=period=='cal' and scale=='platt',
                                        **natural_metrics(frame.y.to_numpy(),prob)))
                    for fraction in [.05,.1,.2]:
                        ranking.append(dict(name=name,period=period,scale=scale,scope='all',threshold=fraction,
                                            **rank_metrics(frame,prob,math.ceil(len(frame)*fraction))))
                    if period=='jan':
                        mask=frame.cluster_id.eq(1).to_numpy()
                        ranking.append(dict(name=name,period=period,scale=scale,scope='H05_cluster1',threshold=79,
                            **rank_metrics(frame.loc[mask].reset_index(drop=True),prob[mask],79)))
            np.savez_compressed(P/f'{name}-scores.npz',**artifact)
        csv('natural_probability_metrics.csv',natural); csv('capacity_metrics.csv',ranking); csv('model_fit.csv',modelinfo)
        csv('training_trajectory.csv',trajectory); csv('platt_parameters.csv',calibration)
    # Public aggregate illustrations, no ranking-based winner selection.
    ndf=pd.DataFrame(natural)
    j=ndf.query("period=='jan' and scale=='platt'").sort_values('name')
    fig,axes=plt.subplots(1,2,figsize=(13,7))
    axes[0].barh(j.name,j.log_loss,color='#4477aa'); axes[0].set(xlabel='January natural-distribution Log loss',title='All frozen candidates, Platt on Oct cal')
    axes[1].barh(j.name,j.ap,color='#66aa99'); axes[1].set(xlabel='January average precision',title='Seen January: diagnostic only')
    fig.tight_layout()
    for ext in ['png','svg']: fig.savefig(OUT/f'probability_comparison.{ext}',dpi=150)
    plt.close(fig)
    r=pd.DataFrame(ranking).query("period=='jan' and scale=='raw' and scope=='all' and threshold==0.1").sort_values('name')
    fig,ax=plt.subplots(figsize=(10,7)); ax.barh(r.name,r.hits,color='#4477aa')
    ax.axvline(2937*230/29368,color='gray',ls=':',label='Random expected hits')
    ax.set(xlabel='Hits among fixed top 2937',title='Matched fit split, raw ranking'); ax.legend(); fig.tight_layout()
    for ext in ['png','svg']: fig.savefig(OUT/f'capacity_comparison.{ext}',dpi=150)
    plt.close(fig)
    dump('verification.json',dict(status='execution_complete_readback_pending',fit_n=len(fit),fit_positive=int(y.sum()),cal_n=len(cal),
        cal_positive=int(cal.y.sum()),jan_n=len(jan),jan_positive=int(jan.y.sum()),april_rows_parsed=0,
        split_random_state=20261111,fit_only_transforms_and_groups=True,jan_selection_used=False,eta=ETA,
        original8_fields=FEATURES,sklearn=__import__('sklearn').__version__,torch=torch.__version__,cpu_threads=2,
        elapsed_seconds=time.time()-began,plan_sha256=sha(OUT/'plan.md'),code_sha256=sha(Path(__file__)),
        h05_jan_sha256=sha(h05path),read_dev_code_sha256=sha(source),candidate_score_variants=list(scoredata)))
    print('COMPLETE',time.time()-began,flush=True)

if __name__=='__main__': main()
