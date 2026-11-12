"""Independent state forward and loss replay; aggregate-only diagnostics."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from scipy.special import expit
from sklearn.metrics import log_loss,brier_score_loss,average_precision_score,roc_auc_score
from threadpoolctl import threadpool_limits
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import run_budget as run

OUT=Path(__file__).resolve().parent
def independent_forward(payload,array):
    state=payload['state_dict'];dims=payload['dims'];out=[]
    with torch.no_grad():
        for start in range(0,len(array),2048):
            q=torch.from_numpy(array[start:start+2048]);views=[];offset=0
            for i,dim in enumerate(dims):
                views.append(F.relu(F.linear(q[:,offset:offset+dim],state[f'enc.{i}.weight'],state[f'enc.{i}.bias'])));offset+=dim
            stacked=torch.stack(views,dim=1)
            weight=torch.full((len(q),len(dims)),1/len(dims))
            latent=(stacked*weight.unsqueeze(-1)).sum(dim=1)
            out.append(F.linear(latent,state['head.weight'],state['head.bias']).squeeze(1).numpy().astype(np.float64))
    return np.concatenate(out)
def main():
    run.assert_freeze();rows=[];calrows=[];metricrows=[]
    for split in run.SPLITS:
        d=run.h.load_split(split,'full141',dense=True,dtype=np.float32)
        for case in run.CASES:
            for seed in run.SEEDS:
                name=f'split{split}__full141__{case}__s{seed}'
                record=json.loads((OUT/f'{name}-record.json').read_text());metadata=record['metadata']
                state=torch.load(OUT/'private'/f'{name}-model.pt',map_location='cpu',weights_only=True)
                saved=np.load(OUT/'private'/f'{name}-logits.npz');scores=np.load(OUT/'private'/f'{name}-scores.npz')
                calibration=record['calibration'];a=calibration['a'];b=calibration['b']
                for part in ['fit','cal','jan']:
                    z=independent_forward(state,d['X_'+part]);target=d['y_'+part]
                    error=float(np.max(np.abs(z-saved[part])));assert error==0.,(name,part,error)
                    loss=np.logaddexp(0,z)-target*z;p=expit(a*z+b)
                    p_error=float(np.max(np.abs(p-scores[part+'_calibrated'])));assert p_error==0.
                    if part=='fit':assert abs(float(loss.sum())-metadata['final_fit_BCE_sum'])<1e-9
                    rows.append(dict(run=name,split=split,case=case,seed=seed,part=part,logit_max_abs=error,probability_max_abs=p_error,independent_BCE_sum=float(loss.sum()),independent_BCE_mean=float(loss.mean()),saved_container=str(saved[part].dtype),execution_dtype='float32'))
                    if part in ['cal','jan']:
                        expected=next(r for r in record['metrics'] if r['scope']=='all' and r['variant']=='calibrated' and r['period']==part)
                        metrics=dict(logloss=float(log_loss(target,p,labels=[0,1])),brier=float(brier_score_loss(target,p)),AP=float(average_precision_score(target,p)),AUC=float(roc_auc_score(target,p)))
                        for metric,value in metrics.items():assert abs(value-expected[metric])<1e-13
                        metricrows.append(dict(run=name,part=part,**metrics))
                z=saved['cal'];target=d['y_cal'];p=expit(a*z+b);e=p-target
                gradient=np.array([np.dot(e,z)+a/1e6,e.sum()]);projected=gradient.copy();projected[0]=a-max(1e-6,a-gradient[0])
                residual=float(np.max(np.abs(projected)))
                assert abs(residual-calibration['projected_gradient_inf'])<1e-10
                calrows.append(dict(run=name,split=split,case=case,seed=seed,success=calibration['success'],projected_gradient_inf=residual,slope=a,intercept=b,active_lower_bound=calibration['active_lower_bound'],message=calibration['message']))
    pd.DataFrame(rows).to_csv(OUT/'model-replay.csv',index=False)
    pd.DataFrame(metricrows).to_csv(OUT/'metric-replay.csv',index=False)
    pd.DataFrame(calrows).to_csv(OUT/'calibration-status.csv',index=False)
    curves=pd.read_csv(OUT/'supervised-curves.csv');pre=pd.read_csv(OUT/'pretrain-curves.csv');support=pd.read_csv(OUT/'run-support.csv')
    colors={'mean70':'#236878','mean3040':'#b56b23','AE-shuffled':'#725a9c'}
    fig,axs=plt.subplots(1,3,figsize=(15,4.4))
    for case in run.CASES:
        subset=curves[curves['case']==case]
        for _,group in subset.groupby('run'):
            axs[0].plot(group['updates'].cumsum(),group.online_mean_BCE,color=colors[case],alpha=.12,lw=.7)
        summary=subset.groupby('epoch').online_mean_BCE.mean()
        # For final partial epoch use actual cumulative updates rather than epoch*34.
        times=subset.groupby('epoch')['updates'].first().cumsum()
        axs[0].plot(times,summary,color=colors[case],label=case,lw=2)
    axs[0].set(xlabel='Supervised Adam updates',ylabel='Online fit BCE',title='Fixed training budgets (15 runs per case)');axs[0].legend()
    for _,group in pre.groupby('run'):axs[1].plot(group.epoch,group.online_view_mean_MSE,color=colors['AE-shuffled'],alpha=.2)
    axs[1].plot(pre.groupby('epoch').online_view_mean_MSE.mean(),color=colors['AE-shuffled'],lw=2)
    axs[1].set(xlabel='Reconstruction epoch',ylabel='Online view-mean shuffled-target MSE',title='Target pairing removed; six blocks stay paired')
    sec=support.assign(training_seconds=support.supervised_seconds+support.pretraining_seconds).groupby('case').training_seconds.agg(['median','min','max']).reindex(run.CASES)
    axs[2].bar(run.CASES,sec['median'],color=[colors[c] for c in run.CASES])
    axs[2].errorbar(run.CASES,sec['median'],yerr=np.vstack([sec['median']-sec['min'],sec['max']-sec['median']]),fmt='none',ecolor='#303030',capsize=4)
    axs[2].set(ylabel='Seconds (median and range)',title='Measured training only; shared CPU contention')
    for ax in axs:ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.18)
    fig.tight_layout();fig.savefig(OUT/'budget-training-diagnostics.png',dpi=170);fig.savefig(OUT/'budget-training-diagnostics.svg');plt.close(fig)
    support.groupby('case').agg(runs=('run','count'),supervised_updates=('supervised_updates','first'),pretraining_updates=('pretraining_updates','first'),labeled_client_presentations=('supervised_clients','first'),total_input_client_presentations=('total_input_client_presentations','first'),supervised_seconds_median=('supervised_seconds','median'),pretraining_seconds_median=('pretraining_seconds','median'),fit_BCE_mean=('final_fit_BCE','mean')).to_csv(OUT/'training-budget-summary.csv')
    allfiles=[p for p in OUT.rglob('*') if p.is_file() and p.name not in ['deliverable-manifest.json','readback-verification.json']]
    run.dump('deliverable-manifest.json',dict(files=[dict(path=p.relative_to(OUT).as_posix(),sha256=run.sha(p),bytes=p.stat().st_size,private='private' in p.parts) for p in allfiles]))
    run.dump('readback-verification.json',dict(status='45_models_independently_replayed',models=45,forward_parts=135,logit_max_abs=max(r['logit_max_abs'] for r in rows),probability_max_abs=max(r['probability_max_abs'] for r in rows),fit_BCE_sum_recomputed=True,calibration_optimizer_successes=sum(r['success'] for r in calrows),calibration_projected_gradient_inf_max=max(r['projected_gradient_inf'] for r in calrows),no_exact_FLOPs_matching_claim=True,source_freeze_unchanged=True))
    print(json.dumps(json.loads((OUT/'readback-verification.json').read_text())),flush=True)
if __name__=='__main__':
    torch.set_num_threads(2)
    with threadpool_limits(limits=2):main()
