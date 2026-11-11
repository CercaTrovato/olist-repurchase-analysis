"""Re-render existing aggregate CSV only; no fit or score computation."""
from pathlib import Path
import pandas as pd,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent
mt=pd.read_csv(OUT/'metrics.csv');families=['rfm-hard','rfm-soft','deep-hard','deep-soft'];colors=['#b2182b','#2166ac','#1b7837']
fig,axes=plt.subplots(1,2,figsize=(12,5))
for ax,metric in zip(axes,['logloss','AP']):
    for vi,(variant,color) in enumerate(zip(['old_50epoch_raw','new_raw','new_Platt'],colors)):
        for i,f in enumerate(families):
            pp=mt.loc[mt.family.eq(f)&mt.variant.eq(variant)&mt.period.eq('january')&mt.scope.eq('all'),metric]
            ax.errorbar(i+(vi-1)*.15,pp.mean(),yerr=pp.std(ddof=1),fmt='o',capsize=3,color=color,label=variant if i==0 else None)
    ax.set_xticks(np.arange(4),families);ax.set_title('Jan '+metric);ax.grid(alpha=.2)
    if metric=='logloss':ax.set_yscale('log')
axes[0].legend(fontsize=8);fig.suptitle('Fixed memberships: old Adam head vs high-precision LR control')
fig.text(.06,.015,'Mean +/- sample SD across the three frozen representation/cluster seeds. No representation or clustering refit.\nOld raw strategies use original logits; new Platt has its own ranking. January already seen.',fontsize=8)
fig.tight_layout(rect=[0,.07,1,.95])
for ext in ['png','svg']:fig.savefig(OUT/f'figures/membership-head-control.{ext}',dpi=170)
plt.close(fig)
fdf=pd.read_csv(OUT/'optimization-control.csv');fig,ax=plt.subplots(figsize=(10,5));xx=np.arange(len(fdf))
ax.plot(xx,fdf.old_final_model_fit_BCE,'o',label='old head final fit BCE');ax.plot(xx,fdf.fit_mean_BCE,'o',label='new LR fit BCE');ax.axhline(fdf.fit_constant_BCE.iloc[0],ls='--',color='#777777',label='fit prevalence constant')
ax.set_xticks(xx,fdf.family+'-'+fdf.seed.astype(str),rotation=35,ha='right');ax.set_ylabel('Fit mean BCE (training diagnostic only)');ax.legend();ax.grid(alpha=.2);fig.tight_layout()
for ext in ['png','svg']:fig.savefig(OUT/f'figures/fit-optimization-control.{ext}',dpi=170)
plt.close(fig)
