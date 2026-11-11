"""Independent persisted-artifact read-back: no fitting or parameter selection."""
import sys
sys.dont_write_bytecode=True
import hashlib,json,math,runpy
from pathlib import Path
import joblib,numpy as np,pandas as pd
from scipy.special import expit
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
OUT=Path(__file__).resolve().parent;ROOT=OUT.parent.parent
KEY=['customer_unique_id','snapshot_date'];NUM=['R','F','M','average_item_rows','freight_share','recent30_orders','recent30_spend'];FIELDS=NUM+['state']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def csv(f,n):f.to_csv(OUT/n,index=False,lineterminator='\n')
def sorted_indices(frame,p):
    # Key-preserving independent rank reconstruction.
    return pd.DataFrame({'customer':frame.customer_unique_id.to_numpy(),'date':frame.snapshot_date.to_numpy(),'s':p}).sort_values(['s','customer','date'],ascending=[False,True,True]).index.to_numpy()
def infer(a,f):
    if a['kind']=='smotenc-LR':
        cat=a['ordinal'].transform(f[['state']]);x=np.column_stack([a['numeric'].transform(f[NUM]),a['ohe'].transform(cat)])
    else:x=a['preprocess'].transform(f[FIELDS])
    if a['kind']=='torch-linear':z=x@np.asarray(a['weight'],dtype=float)+a['bias']
    else:z=x@a['model'].coef_[0]+a['model'].intercept_[0]
    value={'raw-ranking' if a['family']=='torch-pairwise' else 'raw':z if a['family']=='torch-pairwise' else expit(z),
        'Platt':expit(float(a['platt'].coef_[0,0])*z+float(a['platt'].intercept_[0]))}
    if a['prior_offset'] is not None:value['prior']=expit(z-a['prior_offset'])
    return z,value
def main():
    meta=json.loads((OUT/'verification.json').read_text());runs=json.loads((OUT/'run-metadata.json').read_text())
    bounded=runpy.run_path(str(ROOT/'is6400-rfm-weighted-2x2-20261110/run_rfm_2x2.py'));october,jan=bounded['read_dev']()
    split=pd.read_csv(OUT/'private/october-fit-cal-manifest.csv',dtype={KEY[0]:'string'})
    assert len(split)==21160 and not split.duplicated(KEY).any()
    assert split.y.sum()==211 and (split.split=='fit').sum()==16928 and (split.split=='cal').sum()==4232
    assert split.loc[split.split.eq('fit'),'y'].sum()==169 and split.loc[split.split.eq('cal'),'y'].sum()==42
    ss=october.merge(split[KEY+['split','original_oct_index']].rename(columns={'split':'partition'}),on=KEY,validate='one_to_one')
    fit=ss.loc[ss.partition.eq('fit')];fitkeys=set(fit.customer_unique_id)
    assert fitkeys.isdisjoint(set(ss.loc[ss.partition.eq('cal'),'customer_unique_id']))
    prep=joblib.load(OUT/'private/fit-only-preprocessor.joblib')['preprocessor']
    mean=prep.named_transformers_['numeric'].named_steps['scale'].mean_
    assert np.allclose(mean,np.log1p(fit[NUM]).mean().to_numpy(),rtol=0,atol=1e-12)
    frames={};scores={};metrics=pd.read_csv(OUT/'metrics-all-scopes.csv');strategies=pd.read_csv(OUT/'strategy-capacities.csv')
    max_score_error=0;max_logit_error=0;model_checks=0;metric_checks=0;strategy_checks=0
    for period in ['oct_cal','jan']:
        score=pd.read_csv(OUT/f'private/{period}-scores.csv',dtype={KEY[0]:'string'},float_precision='round_trip')
        logits=pd.read_csv(OUT/f'private/{period}-logits.csv',dtype={KEY[0]:'string'},float_precision='round_trip')
        raw=october if period=='oct_cal' else jan
        f=score[KEY+['y','cluster_id']].merge(raw,on=KEY,how='left',validate='one_to_one',suffixes=('','_source'))
        assert f.y.eq(f.y_source).all();assert len(f)==(4232 if period=='oct_cal' else 29368)
        assert score[KEY].equals(logits[KEY]);frames[period]=f;scores[period]=score
        for r in runs:
            a=joblib.load(OUT/f"private/{r['base']}.joblib");z,values=infer(a,f)
            err=float(np.max(np.abs(z-logits['logit_'+r['base']].to_numpy())));max_logit_error=max(max_logit_error,err)
            for variant,p in values.items():
                pe=float(np.max(np.abs(p-score['score_'+r['base']+'__'+variant].to_numpy())));max_score_error=max(max_score_error,pe)
            model_checks+=1
    assert max_score_error<1e-12 and max_logit_error<1e-12
    assert len(metrics)==400 and len(strategies)==200 and len(runs)==20
    for _,r in metrics.iterrows():
        f=frames[r.period];mask=np.ones(len(f),bool) if r.scope=='all' else f.cluster_id.eq(int(r.scope.split('_')[1])).to_numpy()
        y=f.y.to_numpy()[mask];p=scores[r.period]['score_'+r.method].to_numpy()[mask]
        assert len(y)==r.n and y.sum()==r.events
        if r.probability_eligible:
            pp=np.clip(p,np.finfo(float).eps,1-np.finfo(float).eps)
            ll=float(np.mean(-y*np.log(pp)-(1-y)*np.log1p(-pp)));br=float(np.mean((p-y)**2))
            assert abs(ll-r.logloss)<1e-12 and abs(br-r.brier)<1e-12
        else:assert pd.isna(r.logloss) and r.variant=='raw-ranking'
        metric_checks+=1
    for _,r in strategies.iterrows():
        f=frames['jan'];s=scores['jan'];mask=np.ones(len(f),bool) if r.scope=='all' else f.cluster_id.eq(1).to_numpy()
        ff=f.loc[mask].reset_index(drop=True);p=s.loc[mask,'score_'+r.method].to_numpy();y=ff.y.to_numpy();order=sorted_indices(ff,p)
        assert len(order[:int(r.k)])==r.k and y[order[:int(r.k)]].sum()==r.hits
        assert abs(r.precision-r.hits/r.k)<1e-12 and abs(r.recall-r.hits/y.sum())<1e-12
        strategy_checks+=1
    for r in runs:
        a=joblib.load(OUT/f"private/{r['base']}.joblib");man=r['manifest'];p=r['parameters']
        assert man['fit_positive']==169 and man['fit_negative']==16759
        if r['family'].startswith('torch-'):
            assert p['epochs']==150 and p['total_updates']==2550 and p['updates_per_epoch']==17
            assert sum(p['batch_sizes'])==(8450 if r['family']=='torch-pairwise' else 16928)
            if r['family']!='torch-pairwise':assert p['batch_sizes']==[1024]*16+[544]
        if r['family']=='ROS-LR':
            indices=np.load(OUT/f"private/ROS-seed{r['seed']}-training-indices.npz")['sample_indices']
            assert len(indices)==33518 and indices.min()>=0 and indices.max()<16928
            assert man['duplicated_rows']==16590 and man['synthetic_rows']==0
        if r['family']=='SMOTENC-LR':
            archive=np.load(OUT/f"private/SMOTENC-LR-seed{r['seed']}-training.npz")
            assert archive['X_mixed'].shape==(33518,8) and archive['y'].sum()==16759
            assert np.isin(archive['X_mixed'][:,7],p['categorical_legal_values']).all()
            assert (archive['y'][16928:]==1).all() and man['synthetic_rows']==16590
    history=pd.read_csv(OUT/'training-history.csv')
    assert len(history)==1800 and history.steps.sum()==30600
    source_checks={p:sha(p)==h for p,h in meta['input_sha256'].items()};assert all(source_checks.values())
    # Actual seed summaries: deterministic baselines have n=1 and SD=NaN, not duplicated zero variance.
    meanrows=[]
    for group,part in metrics.groupby(['period','scope','family','variant']):
        row=dict(zip(['period','scope','family','variant'],group));row['runs']=len(part);row['seeds']=','.join(str(int(v)) for v in sorted(part.seed.dropna().unique()))
        for col in ['logloss','brier','AP','AUC']:
            row[col+'_mean']=part[col].mean();row[col+'_std']=part[col].std(ddof=1);row[col+'_min']=part[col].min();row[col+'_max']=part[col].max()
        meanrows.append(row)
    summary=pd.DataFrame(meanrows);csv(summary,'seed-summary-metrics.csv')
    ss=[]
    for group,part in strategies.groupby(['scope','k','family','variant']):
        row=dict(zip(['scope','k','family','variant'],group));row['runs']=len(part)
        for c in ['hits','precision','recall']:row[c+'_mean']=part[c].mean();row[c+'_std']=part[c].std(ddof=1);row[c+'_min']=part[c].min();row[c+'_max']=part[c].max()
        ss.append(row)
    csv(pd.DataFrame(ss),'seed-summary-strategy.csv')
    order=['LR-unweighted','LR-balanced','ROS-LR','SMOTENC-LR','torch-BCE','torch-weighted-BCE','torch-focal','torch-pairwise']
    colors={'raw':'#b2182b','prior':'#ef8a62','Platt':'#2166ac','raw-ranking':'#777777'}
    fig,axes=plt.subplots(2,2,figsize=(15,10))
    jan_summary=summary.loc[summary.period.eq('jan')&summary.scope.eq('all')]
    for ax,metric in zip(axes.ravel(),['logloss','brier','AP','AUC']):
        for vi,variant in enumerate(['raw','prior','Platt','raw-ranking']):
            part=jan_summary.loc[jan_summary.variant.eq(variant)].set_index('family')
            for i,fam in enumerate(order):
                if fam not in part.index:continue
                r=part.loc[fam];value=r[metric+'_mean']
                if pd.isna(value):continue
                sd=r[metric+'_std'];ax.errorbar(i+(vi-1.5)*.12,value,yerr=0 if pd.isna(sd) else sd,fmt='o',capsize=3,color=colors[variant],label=variant if i==0 or (variant=='raw-ranking' and i==7) else None)
        ax.set_xticks(np.arange(len(order)),order,rotation=30,ha='right');ax.set_title(metric+(' (lower better; log axis)' if metric in ['logloss','brier'] else ' (higher better)'));ax.grid(alpha=.2)
        if metric in ['logloss','brier']:ax.set_yscale('log')
    axes[0,0].legend(handles=[Line2D([0],[0],color=c,marker='o',linestyle='',label=v) for v,c in colors.items()],fontsize=9);fig.suptitle('P4B: objective / resampling matrix, same Oct fit/cal split')
    fig.text(.05,.01,'Mean +/- sample SD across seeds 2026/27/28; deterministic LR is a single run. Pairwise raw is ranking-only.\nPlatt fit only on 4,232 Oct calibration customers; Jan already seen. All negatives/results retained.',fontsize=9);fig.tight_layout(rect=[0,.055,1,.96])
    for ext in ['png','svg']:fig.savefig(OUT/f'figures/objectives-proper-and-ranking.{ext}',dpi=160)
    plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(15,10))
    for ax,(scope,metric) in zip(axes.ravel(),[('all','logloss'),('all','brier'),('cluster_1_long','logloss'),('cluster_1_long','brier')]):
        tab=summary.loc[summary.period.eq('jan')&summary.scope.eq(scope)&summary.variant.eq('Platt')].set_index('family')
        for i,fam in enumerate(order):
            r=tab.loc[fam];sd=r[metric+'_std'];ax.errorbar(i,r[metric+'_mean'],yerr=0 if pd.isna(sd) else sd,fmt='o',capsize=3,color='#2166ac')
            ax.annotate(f"{r[metric+'_mean']:.6f}",(i,r[metric+'_mean']),xytext=(0,8),textcoords='offset points',ha='center',fontsize=8)
        ax.set_xticks(np.arange(len(order)),order,rotation=30,ha='right');ax.set_title(scope+' '+metric+' (Platt only, lower better)');ax.grid(alpha=.2)
    fig.tight_layout()
    for ext in ['png','svg']:fig.savefig(OUT/f'figures/calibrated-loss-detail.{ext}',dpi=160)
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(14,5))
    st=pd.DataFrame(ss)
    for ax,(scope,k) in zip(axes,[('all',2937),('cluster_1_long',79)]):
        part=st.loc[st.scope.eq(scope)&st.k.eq(k)&st.variant.eq('Platt')].set_index('family')
        for i,fam in enumerate(order):
            r=part.loc[fam];sd=r.hits_std;ax.errorbar(i,r.hits_mean,yerr=0 if pd.isna(sd) else sd,fmt='o',capsize=3,color='#2166ac');ax.annotate(f'{r.hits_mean:.2f}',(i,r.hits_mean),xytext=(0,8),textcoords='offset points',ha='center',fontsize=8)
        ax.set_xticks(np.arange(len(order)),order,rotation=30,ha='right');ax.set_title(f'{scope}: fixed K={k}');ax.set_ylabel('True repeat buyers selected');ax.grid(alpha=.2)
    fig.suptitle('Strategy diagnostic: Platt variant; full 5/10/20% and raw results in CSV');fig.tight_layout()
    for ext in ['png','svg']:fig.savefig(OUT/f'figures/objectives-topk.{ext}',dpi=160)
    plt.close(fig)
    receipt=dict(status='verified',jan_rows=29368,cal_rows=4232,source_files_unchanged=len(source_checks),metric_rows_recomputed=metric_checks,strategy_rows_recomputed=strategy_checks,
        saved_model_period_checks=model_checks,reloaded_logit_max_error=max_logit_error,reloaded_score_max_error=max_score_error,calibration_leakage_check='fit-only scaler mean matched raw fit rows; fit/cal keys disjoint; SMOTE/ROS source rows only fit',
        all_torch_updates=2550,torch_total_trained_runs=12,ranking_pairs_per_epoch=8450,ranking_customers_per_pair=2,BCE_batches=[1024]*16+[544],ranking_batch_sizes=[498]+[497]*16,
        april_rows_parsed=0,failures=json.loads((OUT/'failures.json').read_text()),script_sha256=sha(Path(__file__)))
    receipt['output_sha256']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='independent-verification.json'}
    (OUT/'independent-verification.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(jan_summary[['family','variant','runs','logloss_mean','logloss_std','brier_mean','AP_mean','AUC_mean']].to_string(index=False))
    print(st.loc[st.scope.eq('all')&st.k.eq(2937)][['family','variant','runs','hits_mean','hits_min','hits_max']].to_string(index=False))
    print('INDEPENDENT READBACK VERIFIED',metric_checks,strategy_checks,'model maxerror',max_score_error)
if __name__=='__main__':main()
