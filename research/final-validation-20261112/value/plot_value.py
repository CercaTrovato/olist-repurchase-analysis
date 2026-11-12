"""Aggregate-only publication figures. No per-customer data is read."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

ROOT=Path(__file__).resolve().parent
RULES=['p','purchase_F_M','repeat_Fminus1_M','historical_M','historical_AOV','expected_G']
LABELS=['Probability','p * F * M (main original)','p * max(F-1,0) * M','p * M','p * (M/F)','p * conditional G']
COLORS=['#475569','#a21caf','#d97706','#0891b2','#65a30d','#dc2626']

def main():
    df=pd.read_csv(ROOT/'capacity-results.csv')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    folder=ROOT/'figures'; folder.mkdir(exist_ok=True)
    for family in ['p_wlr','p_ulr','p_catboost']:
        fig,axes=plt.subplots(3,2,figsize=(12,12),sharex=True,sharey=True)
        for i,date in enumerate(['2017-11-01','2017-12-01','2018-01-01']):
            for j,strategy in enumerate(['single','pooled']):
                ax=axes[i,j]
                z=df[(df.evaluation_date==date)&(df.strategy==strategy)&(df.family==family)&(df.scope=='global')]
                for rule,label,color in zip(RULES,LABELS,COLORS):
                    r=z[z.rule==rule].sort_values('capacity')
                    ax.plot(r.capacity*100,r.G_share*100,'o-',color=color,label=label,markersize=3,linewidth=1.5)
                ax.plot([0,100],[0,100],':',color='#94a3b8',label='Random expectation')
                ax.axvline(10,color='#cbd5e1',lw=.8); ax.set_title(f'{date} | {strategy}')
                ax.grid(alpha=.15); ax.set_xlim(0,100); ax.set_ylim(0,103)
                if j==0: ax.set_ylabel('Actual future 90d GMV captured (%)')
                if i==2: ax.set_xlabel('Customer capacity (%)')
        handles,labels=axes[0,0].get_legend_handles_labels()
        fig.legend(handles,labels,loc='lower center',ncol=3,bbox_to_anchor=(.5,.015),frameon=False)
        fig.suptitle(f'Frozen value rules at identical capacities | {family}',fontsize=16,y=.995)
        fig.text(.5,.960,'Known historical windows; overlapping customers and label calendars. Amount capture is not profit or causal uplift.',ha='center',fontsize=9,color='#475569')
        fig.tight_layout(rect=[0,.08,1,.95])
        for ext in ['svg','png']: fig.savefig(folder/f'capacity-gmv-{family}.{ext}',dpi=140,bbox_inches='tight')
        plt.close(fig)

if __name__=='__main__': main()
