"""Aggregate private curves only; no customer-level output."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent
views=['behavior','geography','products','commerce','service','seller_context']
fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
for view in views:
    pre=[];sup=[]
    for split in range(20261111,20261116):
        for seed in [2026,2027,2028]:
            name=f'split{split}__full141__AE-drop-{view.replace("_","-")}__s{seed}'
            c=json.loads((OUT/'private'/f'{name}-curves.json').read_text())
            pre.append([r['online_view_mean_MSE'] for r in c['pretrain']]);sup.append([r['online_mean_BCE'] for r in c['supervised']])
    for ax,values in zip(axes,[pre,sup]):
        values=np.asarray(values);n=values.shape[1];mean=values.mean(0);low=values.min(0);high=values.max(0)
        line=ax.plot(np.arange(1,n+1),mean,label='drop '+view.replace('_',' '))[0]
        ax.fill_between(np.arange(1,n+1),low,high,color=line.get_color(),alpha=.1)
for ax,title,ylabel in zip(axes,['Reconstruction: 20 epochs','Supervision: 50 epochs'],['Online mean view MSE','Online mean BCE']):
    ax.set(title=title,xlabel='Epoch',ylabel=ylabel);ax.grid(alpha=.2)
axes[0].legend(fontsize=8)
fig.suptitle('Whole-view-zero AE | mean and min-max across 5 splits x 3 seeds',fontsize=12)
fig.text(.5,-.02,'Fit-only diagnostics. Zero targets change MSE difficulty; curves do not rank original information importance.',ha='center',fontsize=9)
for ext in ['png','svg']:fig.savefig(OUT/f'training-diagnostics.{ext}',dpi=170,bbox_inches='tight')
plt.close(fig)
