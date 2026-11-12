"""Presentation-only supplement: shorter labels and fewer numeric ticks.

The original frozen renderer and every scientific source/input stay unchanged.
"""
import sys
sys.dont_write_bytecode=True
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import run_statistics as run
OUT=run.OUT
def figure(intervals,cases,name,title):
    fig,axes=plt.subplots(2,2,figsize=(13,7.5))
    labels=[case.replace('AE-drop-','drop ') for case in cases]
    for row,scope in enumerate(['all','long']):
        for col,metric in enumerate(['logloss','hits']):
            ax=axes[row,col];part=intervals[(intervals.scope==scope)&(intervals.reference=='AE-full')&(intervals.metric==metric)].set_index('candidate').loc[cases]
            y=np.arange(len(cases));ax.hlines(y,part.percentile_2_5,part.percentile_97_5,color='#276f7c',lw=2)
            ax.scatter(part.observed_difference,y,color='#233b49',s=30,zorder=3);ax.axvline(0,color='#888888',lw=1)
            ax.set_yticks(y,labels);ax.invert_yaxis();ax.xaxis.set_major_locator(MaxNLocator(nbins=4))
            ax.set(title=f'{scope}: candidate minus AE-full',xlabel='Logloss difference (lower is better)' if metric=='logloss' else 'Fixed-capacity hit difference (higher is better)')
            ax.spines[['top','right']].set_visible(False);ax.grid(axis='x',alpha=.15)
    fig.suptitle(title+'\nConditional 95% intervals; 2000 paired customer resamples; seen January',fontsize=12)
    fig.subplots_adjust(left=.16,right=.98,bottom=.09,top=.83,hspace=.39,wspace=.54)
    fig.savefig(OUT/(name+'.png'),dpi=170);fig.savefig(OUT/(name+'.svg'));plt.close(fig)
def main():
    run.frozen();data=pd.read_csv(OUT/'canonical-paired-bootstrap-intervals.csv')
    figure(data,['mean50','mean70','mean3040','AE-shuffled'],'budget-canonical-conditional-intervals','Fixed supervision budgets and reconstruction pairing')
    figure(data,run.NEW[3:],'blocks-canonical-conditional-intervals','Zero one encoded block at a time: conditional effects cannot be added')
    run.dump('presentation-supplement.json',dict(purpose='readability only: shorten block labels and reduce tick count; no changed data, statistics or scientific source',supplement_code_sha256=run.sha(__file__),interval_data_sha256=run.sha(OUT/'canonical-paired-bootstrap-intervals.csv'),original_frozen_renderer_sha256=run.sha(OUT/'render_statistics.py'),updated_figures=[dict(path=p.name,sha256=run.sha(p)) for p in OUT.glob('*canonical-conditional-intervals.*')]))
if __name__=='__main__':main()
