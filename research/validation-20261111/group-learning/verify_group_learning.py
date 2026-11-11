"""Independent saved-model/score/metric readback for every frozen P4A candidate."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from scipy.special import expit,logit
from sklearn.metrics import average_precision_score,brier_score_loss,log_loss,roc_auc_score
from sklearn.model_selection import train_test_split
from threadpoolctl import threadpool_limits
import torch

OUT=Path(__file__).resolve().parent
P=OUT/'private'
KEY=['customer_unique_id','snapshot_date']
spec=importlib.util.spec_from_file_location('p4_independent_reader',Path('E:/app-data/codex/outputs/is6400-rfm-weighted-2x2-20261110/run_rfm_2x2.py'))
base=importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
oct,jan=base.read_dev(); oct=oct.reset_index(drop=True)
savedidx=np.load(P/'split_indices.npz')
fitidx,calidx=train_test_split(np.arange(len(oct)),test_size=.2,stratify=oct.y,random_state=20261111)
assert np.array_equal(savedidx['fit'],fitidx) and np.array_equal(savedidx['cal'],calidx)
frames={'fit':oct.iloc[fitidx].reset_index(drop=True),'cal':oct.iloc[calidx].reset_index(drop=True),'jan':jan.reset_index(drop=True)}
for period in frames:
    saved=pd.read_csv(P/f'{period}-keys-outcomes.csv',dtype={'customer_unique_id':'string'})
    assert frames[period][KEY+['y']].equals(saved[KEY+['y']])
    if period=='jan': frames[period]['cluster_id']=saved.cluster_id.to_numpy()
X=np.load(P/'features.npz')
selection=json.loads((OUT/'selection.json').read_text())
groups={name:np.load(P/f'{name}-weights-init.npz') for name in ['hard3','hard_geometry','soft_bic']}
with threadpool_limits(limits=2):
    for name,transformerfile,prefix in [('original8','original8-fit-transformer.joblib',''),('rfm','rfm-fit-transformer.joblib','rfm_')]:
        transformer=joblib.load(P/transformerfile)
        for period in ['fit','cal','jan']: assert np.array_equal(transformer.transform(frames[period]),X[prefix+period])
    transform=joblib.load(P/'original8-fit-transformer.joblib')
    fit=frames['fit']
    numeric=['R','F','M','average_item_rows','freight_share','recent30_orders','recent30_spend']
    assert np.allclose(transform.named_transformers_['num'].named_steps['scale'].mean_,np.log1p(fit[numeric]).mean(axis=0))
    assert list(transform.named_transformers_['state'].categories_[0])==sorted(fit.state.unique())
    for grouping,modelname in [('hard3','rfm-fit-kmeans-k3.joblib'),('hard_geometry',f"rfm-fit-kmeans-k{selection['kmeans_winner']}.joblib"),
                              ('soft_bic',f"rfm-fit-gmm-k{selection['gmm_winner']}.joblib")]:
        model=joblib.load(P/modelname)
        for period in ['fit','cal','jan']:
            expected=model.predict_proba(X['rfm_'+period]) if grouping=='soft_bic' else np.eye(model.n_clusters)[model.predict(X['rfm_'+period])]
            assert np.array_equal(expected,groups[grouping][period])
    # Independently reconstruct every output logit from saved parameters.
    mapping={'hard3_fixedcorr':'hard3','hard3_delta_zero':'hard3','hard3_delta_corr':'hard3',
             'hard_geometry_delta_corr':'hard_geometry','soft_bic_delta_corr':'soft_bic','hard3_intercept':'hard3'}
    scores={}
    max_differences={}
    for name in json.loads((OUT/'verification.json').read_text())['candidate_score_variants']:
        arrays=np.load(P/f'{name}-scores.npz')
        maxdiff=0.
        for period in ['cal','jan']:
            xx=X[period]
            if name=='constant_fit_prior': recomputed=np.full(len(xx),logit(fit.y.mean()))
            elif name.startswith('residual_'):
                artifact=torch.load(P/f'{name}-torch.pt',map_location='cpu',weights_only=True)
                state=artifact['state_dict']
                xt=torch.tensor(xx,dtype=torch.float32)
                wt=torch.tensor(groups['hard3'][period],dtype=torch.float32)
                hidden=xt@state['hidden.weight'].T+state['hidden.bias']
                if artifact['nonlinear']: hidden=torch.clamp(hidden,min=0)
                z=(xt@state['base.weight'].T+state['base.bias']).flatten()+artifact['eta']*torch.sum((wt@state['group_head'])*hidden,dim=1)
                recomputed=z.numpy().astype(float)
            else:
                actual='lr_balanced' if name=='lr_balanced_prior' else name
                artifact=np.load(P/f'{actual}-linear.npz')
                d=int(artifact['d']); t=artifact['theta']; eta=float(artifact['eta'])
                recomputed=t[0]+xx@t[1:d+1]
                mode=str(artifact['mode'])
                if actual in mapping:
                    ww=groups[mapping[actual]][period]
                    if mode=='fixed': recomputed+=eta*(ww*(xx@artifact['fixed'].T)).sum(axis=1)
                    if mode=='slope': recomputed+=eta*(ww*(xx@t[d+1:].reshape(int(artifact['g']),d).T)).sum(axis=1)
                    if mode=='intercept': recomputed+=eta*(ww@t[d+1:])
                if name=='lr_balanced_prior': recomputed+=logit(fit.y.mean())
            maxdiff=max(maxdiff,float(np.max(np.abs(recomputed-arrays[period+'_logit']))))
            assert np.allclose(recomputed,arrays[period+'_logit'],rtol=1e-6,atol=1e-6),(name,period,maxdiff)
            assert np.array_equal(expit(arrays[period+'_logit']),arrays[period+'_raw'])
            platt=joblib.load(P/f'{name}-platt.joblib')
            assert np.array_equal(platt.predict_proba(arrays[period+'_logit'].reshape(-1,1))[:,1],arrays[period+'_platt'])
        scores[name]=arrays
        max_differences[name]=maxdiff
    natural=pd.read_csv(OUT/'natural_probability_metrics.csv')
    nverified=0
    for _,row in natural.iterrows():
        yy=frames[row.period].y.to_numpy(); pp=scores[row['name']][row.period+'_'+row.scale]
        expected=dict(log_loss=log_loss(yy,pp,labels=[0,1]),brier=brier_score_loss(yy,pp),
                      ap=average_precision_score(yy,pp),roc_auc=roc_auc_score(yy,pp),mean_probability=pp.mean())
        for key,value in expected.items(): assert np.isclose(row[key],value,rtol=1e-10,atol=1e-12),(row['name'],key)
        chosen=pp>=.5
        assert row.tp==int(np.sum(chosen&(yy==1))) and row.fp==int(np.sum(chosen&(yy==0)))
        assert row.fn==int(np.sum(~chosen&(yy==1))) and row.tn==int(np.sum(~chosen&(yy==0)))
        nverified+=1
    ranking=pd.read_csv(OUT/'capacity_metrics.csv')
    rverified=0
    for _,row in ranking.iterrows():
        frame=frames[row.period].copy()
        frame['score']=scores[row['name']][row.period+'_'+row.scale]
        if row.scope=='H05_cluster1': frame=frame.loc[frame.cluster_id.eq(1)]
        chosen=frame.sort_values(['score']+KEY,ascending=[False,True,True]).head(int(row.k))
        assert int(chosen.y.sum())==row.hits
        assert np.isclose(row.precision,row.hits/row.k)
        assert np.isclose(row.recall,row.hits/frame.y.sum())
        rverified+=1
    # Corr initialization never reads cal/Jan outcomes.
    for grouping,artifact in groups.items():
        xx=X['fit']; yy=fit.y.to_numpy(); ww=artifact['fit']; reconstructed=np.zeros_like(artifact['corr_init'])
        for g in range(ww.shape[1]):
            w=ww[:,g]; mass=w.sum(); positives=w@yy; centeredx=xx-(w@xx/mass); centeredy=yy-positives/mass
            covariance=(w[:,None]*centeredx*centeredy[:,None]).sum(axis=0)/mass
            variancex=(w[:,None]*centeredx**2).sum(axis=0)/mass
            variancey=(w*centeredy**2).sum()/mass
            denom=np.sqrt(variancex*variancey)
            reconstructed[g]=np.divide(covariance,denom,out=np.zeros_like(covariance),where=denom>1e-14)*positives/(positives+20)
        assert np.allclose(reconstructed,artifact['corr_init'],atol=1e-12)
result=dict(status='PASS',split_recomputed=True,fit_only_scaler_means_categories_verified=True,
    exact_transformed_arrays_verified=True,group_predictions_recomputed=True,correlation_init_fit_only_recomputed=True,
    candidate_score_variants=len(scores),max_saved_logit_differences=max_differences,
    natural_metric_rows_recomputed=nverified,capacity_metric_rows_recomputed=rverified,
    model_platt_predictions_recomputed=True,calibration_resubstitution_disclosed=True,april_rows_parsed=0,
    code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(OUT/'readback_verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
