"""Only aggregate visualization of completed frozen statistics; no fitting."""
from pathlib import Path
import hashlib,json
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
STAT=Path(__file__).resolve().parent;FIG=STAT/'figures';FIG.mkdir(exist_ok=True)
ORDER=['weightedLR','unweightedLR','encodedCatBoost','mean','column-gate','AE','nativeCatBoost']
LABEL=['Weighted LR','Natural LR','Encoded CB','Mean NN','Column gate','AE package','Native CB bridge']
def save(fig,name):
    for ext in ['png','svg']:fig.savefig(FIG/f'{name}.{ext}',dpi=170)
    plt.close(fig)
def read(name):return pd.read_csv(STAT/name)
def main():
    main=read('main-model-information-by-split.csv')
    fig,axes=plt.subplots(2,2,figsize=(14,10))
    panels=[('all','logloss','Global Log loss (lower better)'),('all','AP','Global AP (higher better)'),('all','hits','Global K=2,937 hits'),('cluster_1_long','hits','H05 long K=79 hits')]
    for ax,(scope,metric,title) in zip(axes.ravel(),panels):
        for ii,info in enumerate(['base8','full141']):
            for j,fam in enumerate(ORDER):
                x=main.loc[main.scope.eq(scope)&main.information.eq(info)&main.family.eq(fam),metric+'_mean'].to_numpy()
                if not len(x):continue
                middle=float(np.median(x));offset=(ii-.5)*.24;color='#777777' if info=='base8' else '#2166ac' if fam!='nativeCatBoost' else '#cf7a21'
                ax.errorbar(j+offset,middle,yerr=[[middle-x.min()],[x.max()-middle]],fmt='o',capsize=4,color=color)
                ax.scatter(j+offset+np.linspace(-.035,.035,len(x)),x,s=12,color=color,alpha=.5)
        ax.set_xticks(np.arange(7),LABEL,rotation=25,ha='right');ax.set_title(title);ax.grid(axis='y',alpha=.2)
    axes[0,0].legend(handles=[Line2D([0],[0],color='#777777',marker='o',linestyle='',label='base8'),Line2D([0],[0],color='#2166ac',marker='o',linestyle='',label='full141'),Line2D([0],[0],color='#cf7a21',marker='o',linestyle='',label='native processing bridge')],fontsize=9)
    fig.suptitle('Within-split seed averages, then five overlapping training splits')
    fig.text(.05,.01,'Dot = median; whisker = min/max over five split means; small dots = individual split means. Not a confidence interval.\nSame seen January each time. Deterministic LR has one run per split; stochastic cells have three seeds. Native CB changes the processing package.',fontsize=9)
    fig.tight_layout(rect=[0,.06,1,.96]);save(fig,'model-information-split-ranges')
    # Paired information differences, without treating overlapping splits as independent tests.
    pairs=read('controlled-paired-differences-by-split.csv');pairs=pairs.loc[pairs.contrast.eq('information')]
    fig,axes=plt.subplots(2,2,figsize=(13,9))
    for ax,(scope,metric) in zip(axes.ravel(),[('all','logloss'),('all','hits'),('cluster_1_long','logloss'),('cluster_1_long','hits')]):
        for j,fam in enumerate(ORDER[:-1]):
            p=pairs.loc[pairs.family.eq(fam)&pairs.scope.eq(scope),'delta_'+metric+'_mean'].to_numpy();ax.scatter(j+np.linspace(-.12,.12,len(p)),p,s=26,color='#2166ac');ax.plot([j-.17,j+.17],[np.median(p)]*2,color='#111111',lw=2)
        ax.axhline(0,color='#777777',ls='--',lw=1);ax.set_xticks(np.arange(6),LABEL[:-1],rotation=25,ha='right');ax.set_title(f'{scope}: full141 - base8 {metric}');ax.grid(alpha=.2)
    fig.suptitle('Matched split/seed information contrasts; black line = median split difference')
    fig.text(.05,.01,'Five dots are overlapping fit/cal perturbations, not independent periods. Negative Log loss / positive hits favor full141.\nAE extra pretraining and gate initial scaling remain parts of their model packages; no causal component claim.',fontsize=9);fig.tight_layout(rect=[0,.06,1,.96]);save(fig,'paired-information-effects')
    ci=read('canonical-paired-bootstrap-intervals.csv');ci=ci.loc[ci.contrast.eq('primary_vs_weightedLR_base8')]
    candidates=sorted(ci.candidate.unique())
    for metrics,name in [(['logloss','hits'],'canonical-paired-loss-hits'),(['brier','AP'],'canonical-paired-brier-AP')]:
        fig,axes=plt.subplots(2,2,figsize=(14,11))
        for row,scope in enumerate(['all','long']):
            for col,metric in enumerate(metrics):
                ax=axes[row,col];part=ci.loc[ci.scope.eq(scope)&ci.metric.eq(metric)].set_index('candidate')
                for j,c in enumerate(candidates):
                    r=part.loc[c];value=r.observed_difference
                    # Percentile intervals need not contain the observed estimate: draw endpoints directly.
                    ax.plot([r.percentile_2_5,r.percentile_97_5],[j,j],color='#2166ac',lw=1.5);ax.plot(value,j,'o',color='#2166ac',ms=4)
                ax.axvline(0,color='#777777',ls='--',lw=.8);ax.set_yticks(np.arange(len(candidates)),candidates,fontsize=8);ax.set_title(scope+' '+metric+' difference');ax.grid(axis='x',alpha=.2)
        fig.suptitle('Canonical mean-calibrated-probability ensembles minus weightedLR-base8')
        fig.text(.05,.01,'2,000 paired customer-copy bootstraps; fixed scores, no retraining. Global K=2,937 / long K=79 reranked in each copy pool.\n95% percentile intervals; no multiple-comparison correction. Not uncertainty over new training or future time.',fontsize=9);fig.tight_layout(rect=[0,.065,1,.96]);save(fig,name)
    st=read('selection-stability-pairs.csv');fig,axes=plt.subplots(2,2,figsize=(13,9))
    for row,scope in enumerate(['all','cluster_1_long']):
        for col,kind in enumerate(['within_split_across_seeds','within_seed_across_splits']):
            ax=axes[row,col];data=np.full((7,2),np.nan);counts=np.zeros((7,2),int)
            for j,fam in enumerate(ORDER):
                for k,info in enumerate(['base8','full141']):
                    part=st.loc[st.scope.eq(scope)&st.kind.eq(kind)&st.family.eq(fam)&st.information.eq(info)]
                    if len(part):data[j,k]=part.jaccard.mean();counts[j,k]=len(part)
            image=ax.imshow(np.ma.masked_invalid(data),vmin=0,vmax=1,cmap='Blues',aspect='auto')
            for j in range(7):
                for k in range(2):ax.text(k,j,'n/a' if np.isnan(data[j,k]) else f'{data[j,k]:.3f}\nn={counts[j,k]}',ha='center',va='center',fontsize=9,color='white' if np.isfinite(data[j,k]) and data[j,k]>.6 else 'black')
            ax.set_xticks([0,1],['base8','full141']);ax.set_yticks(np.arange(7),LABEL,fontsize=9);ax.set_title(scope+'\n'+kind.replace('_',' '));fig.colorbar(image,ax=ax,fraction=.04)
    fig.suptitle('Selection Jaccard: same hit count can hide different customer lists')
    fig.text(.05,.01,'n counts dependent list pairs, not independent validation periods. Deterministic LR has no within-split seed pairs.\nAcross-split pairs preserve the same seed; all scores evaluated on the same seen January.',fontsize=9);fig.tight_layout(rect=[0,.06,1,.94]);save(fig,'selection-stability')
    # Every requested canonical model has all ten Octcal-defined bins and visible denominators.
    bins=read('canonical-calibration-all-bins.csv')
    for name in bins.model.unique():
        fig,axes=plt.subplots(2,2,figsize=(14,8),gridspec_kw={'height_ratios':[3,1.3]})
        for col,scope in enumerate(['all','cluster_1_long']):
            b=bins.loc[bins.model.eq(name)&bins.scope.eq(scope)].sort_values('bin');non=b.loc[b.n>0];ax=axes[0,col]
            error=np.vstack([non.observed_rate-non.wilson_low,non.wilson_high-non.observed_rate]);ax.errorbar(non.mean_probability,non.observed_rate,yerr=error,fmt='o',color='#2166ac',capsize=3)
            limit=min(1.01,max(float(non.mean_probability.max()),float(non.wilson_high.max()))*1.08);limit=max(limit,.015)
            ax.plot([0,limit],[0,limit],'--',color='#777777');ax.set(xlim=(0,limit),ylim=(0,limit),title=scope,xlabel='Mean predicted probability',ylabel='January event rate / 95% Wilson');ax.grid(alpha=.2)
            ax=axes[1,col];ax.axis('off');cells=[[str(int(n))+'/'+str(int(e)) for n,e in zip(b.n,b.events)],['empty' if not np.isfinite(x) else f'{x:.4f}' for x in b.mean_probability],['empty' if not np.isfinite(x) else f'{x:.4f}' for x in b.observed_rate]]
            tab=ax.table(cellText=cells,rowLabels=['N/events','Mean p','Observed'],colLabels=[str(int(x)) for x in b.bin],loc='center',cellLoc='center');tab.auto_set_font_size(False);tab.set_fontsize(8);tab.scale(1,1.5)
        fig.suptitle(name+': canonical mean(calibrated probability)',fontsize=15)
        fig.text(.055,.015,'Bin boundaries: quantiles of canonical Octcal ensemble probabilities. Constituent calibrators fit on those same cal labels.\nOctcal is in-sample for calibration; January already seen. All ten bins retained; N/events conserve scope totals. No top-K filtering.',fontsize=9);fig.tight_layout(rect=[.025,.06,1,.95]);save(fig,'calibration-'+name.replace('::','-'))
    output=dict(status='PLOTS_RENDERED_FROM_FROZEN_AGGREGATES_ONLY',model_fits=0,evaluation_configuration_changes=0,
        source_csv_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [STAT/n for n in ['main-model-information-by-split.csv','controlled-paired-differences-by-split.csv','canonical-paired-bootstrap-intervals.csv','selection-stability-pairs.csv','canonical-calibration-all-bins.csv']]},
        figure_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in FIG.iterdir() if p.is_file()},code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (STAT/'figure-manifest.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8');print('Rendered',len(output['figure_sha256'])//2,'PNG/SVG pairs')
if __name__=='__main__':main()
