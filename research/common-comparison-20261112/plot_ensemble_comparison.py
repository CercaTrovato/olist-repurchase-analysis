from pathlib import Path
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'svg.fonttype':'none','font.size':10})
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'figures';OUT.mkdir(exist_ok=True)
models=[('base8::weightedLR','Weighted LR / base8','#333333'),('full141::mean','Mean NN / full141','#3579b8'),('full141::column-gate','Column gate / full141','#db8d28'),('full141::AE','AE / full141','#ad4c98'),('full141::encodedCatBoost','Encoded CB / full141','#469d9b'),('full141::nativeCatBoost','Native CB / full141','#5e9947')]
def save(fig,name):
 fig.savefig(OUT/(name+'.png'),dpi=240,bbox_inches='tight');fig.savefig(OUT/(name+'.svg'),bbox_inches='tight');plt.close(fig)
f=pd.read_csv(ROOT/'ensemble-five-split-results.csv');splits=sorted(f.split_id.unique());x=np.arange(5)
fig,axes=plt.subplots(1,2,figsize=(13,6.2))
for ax,scope,title in zip(axes,['all','long'],['Global fixed K = 2,937','H05 long group: fixed K = 79']):
 for model,label,color in models:
  v=f[(f.model==model)&(f.scope==scope)].sort_values('split_id');ax.plot(x,v.hits,marker='o',color=color,label=label,lw=2 if model.startswith('base8') else 1.5)
 ax.set_xticks(x,[f'Split {i+1}' for i in x]);ax.set_title(title);ax.set_xlabel('Overlapping random fit / calibration splits');ax.set_ylabel('January repurchasers captured');ax.grid(alpha=.2)
 if scope=='long':ax.set_ylim(.7,4.4);ax.set_yticks([1,2,3,4])
handles,labels=axes[1].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,.12),ncol=3,frameon=False)
fig.suptitle('Same frozen mean(calibrated probability) system, all five splits',y=.97)
fig.text(.02,.015,'Supplementary sensitivity analysis: same January N=29,368 / 230 events; long N=12,330 / 90 events.\nSplit 1 = canonical seed20261111. All five train on October 2017; they are not new months or confidence intervals. No refit/new bootstrap.',fontsize=8)
fig.subplots_adjust(left=.07,right=.98,top=.86,bottom=.34,wspace=.25);save(fig,'ensemble-five-split-hits')
c=pd.read_csv(ROOT/'statistics/canonical-ensemble-capacities.csv');n=np.arange(len(models));fig,axes=plt.subplots(1,2,figsize=(13,5.5))
for ax in axes:ax.set_yticks(n,[label for _,label,_ in models]);ax.invert_yaxis();ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True)
for i,(model,label,color) in enumerate(models):
 a=c[(c.model==model)&c.policy.eq('global2937')].iloc[0];b=c[(c.model==model)&c.policy.eq('long79')].iloc[0]
 axes[0].barh(i,a.global_long_selected,color=color,alpha=.85);axes[0].text(a.global_long_selected+8,i,f'{int(a.global_long_selected)} seats / {int(a.global_long_hits)} hits',va='center',fontsize=8)
 axes[1].barh(i,b.hits,color=color,alpha=.85);axes[1].text(b.hits+.08,i,str(int(b.hits)),va='center')
axes[0].set_xlim(0,820);axes[0].set_title('Inside the global 2,937-person list');axes[0].set_xlabel('Seats allocated to the long group')
axes[1].set_xlim(0,5.1);axes[1].set_title('Independent long-group ranking, same 79 seats');axes[1].set_xlabel('Repurchasers captured within those 79 seats');axes[1].axvline(2,color='#333333',ls='--',lw=1)
fig.suptitle('Broader long-group coverage and sharper within-group ranking are different results',y=1.02)
fig.text(.02,-.02,'Canonical split20261111; stochastic models = mean of three calibrated probabilities, LR = one model.\nSame January clients and H05 group labels. The paired bootstrap hit-difference intervals include zero; this plot is descriptive.',fontsize=8)
fig.tight_layout(rect=[0,.04,1,1]);save(fig,'coverage-versus-within-long79')
print('Saved 2 PNG/SVG pairs')
