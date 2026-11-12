"""Three aggregate-only figure families for fixed statistical contrasts."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent
def contrast_figure(intervals,cases,name,title):
    fig,axes=plt.subplots(2,2,figsize=(12,7.5),squeeze=False)
    for row,scope in enumerate(['all','long']):
        for col,metric in enumerate(['logloss','hits']):
            ax=axes[row,col];part=intervals[(intervals.scope==scope)&(intervals.reference=='AE-full')&(intervals.metric==metric)].set_index('candidate').loc[cases]
            y=np.arange(len(cases));point=part.observed_difference.to_numpy();lo=part.percentile_2_5.to_numpy();hi=part.percentile_97_5.to_numpy()
            ax.hlines(y,lo,hi,color='#276f7c',lw=2);ax.scatter(point,y,color='#233b49',s=30,zorder=3)
            ax.axvline(0,color='#888888',lw=1);ax.set_yticks(y,cases);ax.invert_yaxis()
            ax.set(title=f'{scope}: candidate minus AE-full',xlabel=('Logloss difference (negative favors candidate)' if metric=='logloss' else 'Fixed-capacity hit difference (positive favors candidate)'))
            ax.spines[['top','right']].set_visible(False);ax.grid(axis='x',alpha=.15)
    fig.suptitle(title+'\nConditional percentile 95% intervals; 2000 shared-count customer resamples; seen January',fontsize=12)
    fig.tight_layout(rect=[0,0,1,.94]);fig.savefig(OUT/(name+'.png'),dpi=170);fig.savefig(OUT/(name+'.svg'));plt.close(fig)
def main():
    import run_statistics as run
    run.frozen();intervals=pd.read_csv(OUT/'canonical-paired-bootstrap-intervals.csv')
    contrast_figure(intervals,['mean50','mean70','mean3040','AE-shuffled'],'budget-canonical-conditional-intervals','Fixed supervision budgets and reconstruction pairing')
    contrast_figure(intervals,run.NEW[3:],'blocks-canonical-conditional-intervals','One encoded block zeroed at a time; conditional effects are not additive')
    differences=pd.read_csv(OUT/'ensemble-paired-differences-by-split.csv');stability=pd.read_csv(OUT/'selection-stability.csv')
    fig,axes=plt.subplots(2,2,figsize=(15,10))
    for col,scope in enumerate(['all','long']):
        ax=axes[0,col];part=differences[(differences.reference=='AE-full')&(differences.scope==scope)&differences.candidate.isin(run.NEW)]
        table=part.pivot(index='candidate',columns='split_id',values='delta_hits').reindex(run.NEW);v=max(1,float(np.abs(table.to_numpy()).max()))
        ax.imshow(table.to_numpy(),cmap='RdBu',vmin=-v,vmax=v,aspect='auto')
        ax.set_xticks(range(5),[str(x) for x in table.columns],rotation=30);ax.set_yticks(range(9),run.NEW);ax.set_title(scope+': hit difference versus AE-full across five overlapping splits')
        for i in range(9):
            for j in range(5):ax.text(j,i,f'{table.iloc[i,j]:+.0f}',ha='center',va='center',color='black',fontsize=9,bbox=dict(facecolor='white',edgecolor='none',alpha=.5,pad=1))
        ax=axes[1,col];subset=stability[(stability.kind=='ensemble_across_overlapping_splits')&(stability.scope==scope)]
        groups=[subset[subset.model==m].jaccard.to_numpy() for m in run.SYSTEMS]
        ax.boxplot(groups,labels=run.SYSTEMS,showfliers=True);ax.tick_params(axis='x',rotation=65);ax.set_ylim(0,1.02)
        ax.set(ylabel='Selected-customer Jaccard',title=scope+': same system across all 10 split pairs');ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.15)
    fig.suptitle('Training perturbations on the same seen January cohort; not five independent periods',fontsize=13)
    fig.tight_layout(rect=[0,0,1,.96]);fig.savefig(OUT/'five-split-directions-and-list-stability.png',dpi=170);fig.savefig(OUT/'five-split-directions-and-list-stability.svg');plt.close(fig)
if __name__=='__main__':main()
