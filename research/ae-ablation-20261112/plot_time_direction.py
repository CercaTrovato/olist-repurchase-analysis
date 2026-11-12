from pathlib import Path
import pandas as pd,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'svg.fonttype':'none','font.size':10})
R=Path(__file__).resolve().parent;C=R.parent;D=R/'figures';D.mkdir(exist_ok=True)
j=pd.read_csv(C/'statistics/canonical-ensemble-capacities.csv');o=pd.read_csv(R/'temporal/primary-october-capacity.csv')
names=[('mean','Mean NN'),('AE','AE20+50'),('encodedCB','Encoded CB'),('nativeCB','Native CB')];rows=[]
for period,f,base,policies in [('Jan2018',j,'base8::weightedLR',{'all':'global2937','long':'long79'}),('Oct2017',o,'weightedLR',{'all':'global10','long':'long79'})]:
 for scope,policy in policies.items():
  sub=f[f.policy.eq(policy)]
  b=sub[sub.model.eq(base)].iloc[0] if period=='Jan2018' else sub[sub.system.str.startswith(base+'__')].iloc[0]
  for family,label in names:
   jf={'mean':'full141::mean','AE':'full141::AE','encodedCB':'full141::encodedCatBoost','nativeCB':'full141::nativeCatBoost'}[family]
   v=sub[sub.model.eq(jf)].iloc[0] if period=='Jan2018' else sub[sub.system.str.startswith(family+'__')].iloc[0]
   rows.append(dict(period=period,scope=scope,family=family,label=label,k=int(v.k),hits=int(v.hits),baseline_hits=int(b.hits),delta_hits=int(v.hits-b.hits),delta_precision_pp=100*(v.hits-b.hits)/v.k))
d=pd.DataFrame(rows);d.to_csv(R/'time-direction-chart-data.csv',index=False,lineterminator='\n')
fig,ax=plt.subplots(1,2,figsize=(12,4.6));y=np.arange(4)
for a,scope,title in zip(ax,['all','long'],['Global: 10% of each evaluation cohort','Long group: same fixed 79 seats']):
 for period,offset,color in [('Oct2017',-.18,'#d58c43'),('Jan2018',.18,'#3d7fa7')]:
  q=d[d.scope.eq(scope)&d.period.eq(period)].set_index('family').loc[[n[0] for n in names]]
  a.barh(y+offset,q.delta_precision_pp,height=.32,color=color,label='July -> seen October' if period=='Oct2017' else 'October -> seen January')
  for i,row in enumerate(q.itertuples()):a.text(row.delta_precision_pp+(.035 if row.delta_precision_pp>=0 else -.035),i+offset,f'{row.delta_hits:+d} hits',va='center',ha='left' if row.delta_precision_pp>=0 else 'right',fontsize=8)
 a.set_yticks(y,[n[1] for n in names]);a.invert_yaxis();a.axvline(0,color='#555',lw=.8);a.set_title(title);a.set_xlabel('Precision change vs local WLR (percentage points)');a.grid(axis='x',alpha=.2);a.set_axisbelow(True)
ax[0].set_xlim(-.5,.5);ax[1].set_xlim(-3.3,3.3);fig.legend(*ax[1].get_legend_handles_labels(),loc='lower center',bbox_to_anchor=(.5,.07),ncol=2,frameon=False)
fig.suptitle('The apparent AE gain does not persist in the earlier time combination',y=.98)
fig.text(.02,.015,'Both evaluation windows were seen in project development. This is descriptive, not new blind-test evidence.\nGlobal K: October 2,116 vs January 2,937; long K=79 in each window. No cross-window bootstrap was run.',fontsize=8)
fig.subplots_adjust(top=.82,bottom=.30,wspace=.28)
for ext in ['png','svg']:fig.savefig(D/f'time-combination-relative-gains.{ext}',dpi=240,bbox_inches='tight')
plt.close(fig);print('Saved relative-direction figure and aggregate data')
