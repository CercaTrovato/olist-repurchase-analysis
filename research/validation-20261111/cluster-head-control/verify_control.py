"""Local persisted-artifact read-back; no model.fit calls."""
import sys
sys.dont_write_bytecode=True
import hashlib,json
from pathlib import Path
import joblib,numpy as np,pandas as pd
from scipy.special import expit
from sklearn.metrics import average_precision_score,roc_auc_score
from threadpoolctl import threadpool_limits
OUT=Path(__file__).resolve().parent;ROOT=OUT.parent;RP=ROOT/'representations/private';KEY=['customer_unique_id','snapshot_date']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return pd.read_csv(p,dtype={KEY[0]:'string'},float_precision='round_trip')
def rank(f,p):return f[KEY].assign(s=p).sort_values(['s']+KEY,ascending=[False,True,True]).index.to_numpy()
def main():
    receipt=json.loads((OUT/'verification.json').read_text());runs=json.loads((OUT/'run-metadata.json').read_text())
    keys={p:read(OUT/f'private/{p}-keys-labels.csv') for p in ['fit','cal','january']}
    sf={p:read(OUT/f'private/{p}-scores.csv') for p in ['cal','january']};rs={p:read(OUT/f'private/{p}-ranking-scores.csv') for p in ['cal','january']}
    for p in sf:assert keys[p][KEY+['y','cluster_id']].equals(sf[p][KEY+['y','cluster_id']]) and sf[p][KEY].equals(rs[p][KEY])
    yf=keys['fit'].y.to_numpy();assert (len(yf),sum(yf))==(16928,169)
    maxerr=0;models=0;objective_max_error=0;changed=[]
    for run in runs:
        name=f"{run['family']}-{run['seed']}";a=joblib.load(OUT/f'private/{name}.joblib');clf=a['model'];c=a['platt']
        assert clf.C==1 and clf.tol==1e-10 and clf.max_iter==5000 and clf.class_weight is None
        xf=np.load(RP/f'{name}-fit-memberships.npy').astype(float);zf=xf@clf.coef_[0]+clf.intercept_[0]
        resid=expit(zf)-yf;grad=np.r_[resid.sum(),xf.T@resid+clf.coef_[0]]
        obj=float(np.sum(np.logaddexp(0,zf)-yf*zf)+.5*np.sum(clf.coef_**2))
        objective_max_error=max(objective_max_error,abs(obj-run['sum_objective']))
        assert abs(obj-run['sum_objective'])<1e-10 and abs(np.max(np.abs(grad))-run['sum_gradient_max'])<1e-10
        for p in ['cal','january']:
            x=np.load(RP/f'{name}-{p}-memberships.npy').astype(float);z=x@clf.coef_[0]+clf.intercept_[0]
            newraw=expit(z);calibrated=expit(float(c.coef_[0,0])*z+float(c.intercept_[0]))
            maxerr=max(maxerr,float(np.max(np.abs(newraw-sf[p]['score_'+name+'__new_raw']))),float(np.max(np.abs(calibrated-sf[p]['score_'+name+'__new_Platt']))))
            assert np.max(np.abs(z-rs[p]['rank_'+name+'__new_raw']))<1e-12
            if p=='january':
                raworder=rank(keys[p],z);calorder=rank(keys[p],calibrated)
                changed.append(dict(family=run['family'],seed=run['seed'],platt_slope=float(c.coef_[0,0]),top10_changed=len(set(raworder[:2937]).symmetric_difference(set(calorder[:2937])))))
            models+=1
    assert models==24 and maxerr<1e-12
    metrics=read(OUT/'metrics.csv');capacity=read(OUT/'capacity.csv');assert len(metrics)==304 and len(capacity)==152
    for _,r in metrics.iterrows():
        f=keys[r.period];mask=np.ones(len(f),bool) if r.scope=='all' else f.cluster_id.eq(int(r.scope.split('_')[1])).to_numpy();y=f.y.to_numpy()[mask];p=sf[r.period]['score_'+r.method].to_numpy()[mask]
        assert len(y)==r.n and y.sum()==r.events
        pp=np.clip(p,np.finfo(float).eps,1-np.finfo(float).eps);ll=float(np.mean(-y*np.log(pp)-(1-y)*np.log1p(-pp)));br=float(np.mean((p-y)**2))
        assert abs(ll-r.logloss)<1e-12 and abs(br-r.brier)<1e-12
        assert abs(average_precision_score(y,p)-r.AP)<1e-12 and abs(roc_auc_score(y,p)-r.AUC)<1e-12
    for _,r in capacity.iterrows():
        mask=np.ones(len(keys['january']),bool) if r.scope=='all' else keys['january'].cluster_id.eq(1).to_numpy();f=keys['january'].loc[mask].reset_index(drop=True);rankscore=rs['january']['rank_'+r.method].to_numpy()[mask]
        take=rank(f,rankscore)[:int(r.k)];assert int(f.y.iloc[take].sum())==r.hits and len(take)==r.k
    priors=json.loads((OUT/'private/baseline-priors.json').read_text())
    for g in [0,1,2]:
        f=keys['fit'].loc[keys['fit'].cluster_id.eq(g)];assert abs((f.y.sum()+1)/(len(f)+100)-priors['H05_fit_group_priors'][str(g)])<1e-15
    original={p:sha(p)==h for p,h in receipt['input_sha256'].items()};assert all(original.values())
    pd.DataFrame(changed).to_csv(OUT/'Platt-ranking-correspondence.csv',index=False,lineterminator='\n')
    result=dict(status='PASS_local_readback',metric_rows_recomputed=304,capacity_rows_recomputed=152,models_times_periods_replayed=models,
        score_max_error=maxerr,objective_max_error=objective_max_error,source_files_unchanged=len(original),fit_only_Beta_priors_recomputed=True,
        all_new_Platt_slopes_positive=all(r['platt_slope']>0 for r in changed),new_Platt_top10_changes=sum(r['top10_changed'] for r in changed),april_rows_parsed=0,code_sha256=sha(Path(__file__)))
    result['output_sha256']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='readback-verification.json'}
    (OUT/'readback-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='output_sha256'},indent=2))
if __name__=='__main__':
    with threadpool_limits(limits=2):main()
