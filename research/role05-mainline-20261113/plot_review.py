"""Aggregate figures for Role05 acceptance; no fitted models or adopted CI."""
from pathlib import Path
import json,hashlib
import pandas as pd,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
O=Path(__file__).resolve().parent;F=O/'figures';F.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
def save(fig,n):
 for e in ['png','svg']:fig.savefig(F/(n+'.'+e),dpi=170,bbox_inches='tight')
 plt.close(fig)
d=pd.read_csv(O/'audit/capacity-all-models.csv');fig,ax=plt.subplots(figsize=(9.7,5.4),layout='constrained')
for name,c,m in [('F0 Weighted (Main)','#147d8d','o'),('F0 Unweighted','#64788e','s'),('B +Cluster_id','#be8531','^'),('C Segmented Fallback','#785a9d','D')]:
 p=d[d.Model.eq(name)].sort_values('Top_Fraction');ax.plot(p.Top_Fraction*100,p.Hits,marker=m,color=c,label=name.replace('(Main)','(team reference)'))
ax.set_xticks([5,10,20]);ax.set_ylim(0,90);ax.set_xlabel('List capacity (%)');ax.set_ylabel('Observed repurchasers captured');ax.grid(alpha=.2);ax.legend(loc='upper left');ax.set_title('Team R3 score tables: three capacities independently recounted\nSeen January development window; not a blind future test',fontsize=13)
save(fig,'01-role05-capacity-recount')
p=pd.read_csv(O/'audit/paired-list-recomputed.csv');fig,ax=plt.subplots(figsize=(10.2,5.6),layout='constrained');x=np.arange(len(p));w=.34
ax.bar(x-w/2,p.Added_Hits,w,color='#147d8d',label='Hits among customers added by F0');ax.bar(x+w/2,p.Dropped_Hits,w,color='#be8531',label='Hits among customers dropped by F0')
for i,r in p.iterrows():
 ax.text(i-w/2,r.Added_Hits+.15,str(int(r.Added_Hits)),ha='center');ax.text(i+w/2,r.Dropped_Hits+.15,str(int(r.Dropped_Hits)),ha='center')
 ax.text(i,13.0,f'Net {int(r.Net_Gain):+d}; {int(r.Added)} replaced',ha='center',fontsize=10)
ax.set_xticks(x,['Weighted vs unweighted','Weighted vs B','Weighted vs C']);ax.set_ylim(0,16);ax.set_ylabel('Observed repurchasers');ax.legend();ax.grid(axis='y',alpha=.2);ax.set_title('Matched lists at exactly 2,937 seats\nSet arithmetic identifies who changed; it does not establish a causal mechanism',fontsize=13)
save(fig,'02-role05-paired-changes')
p=pd.read_csv(O/'audit/weighting-group-decomposition.csv');fig,axes=plt.subplots(1,2,figsize=(12.2,5),layout='constrained');x=np.arange(3)
for ax,a,b,label in [(axes[0],'Unweighted_Selected','Weighted_Selected','Selected customers in global list'),(axes[1],'Unweighted_Hits','Weighted_Hits','Observed repurchasers captured')]:
 ax.bar(x-w/2,p[a],w,color='#64788e',label='Unweighted');ax.bar(x+w/2,p[b],w,color='#147d8d',label='Weighted')
 for i,r in p.iterrows():
  ax.annotate(str(int(r[a])),(i-w/2,r[a]),xytext=(0,5),textcoords='offset points',ha='center',fontsize=10);ax.annotate(str(int(r[b])),(i+w/2,r[b]),xytext=(0,5),textcoords='offset points',ha='center',fontsize=10)
 ax.set_xticks(x,['Recent single','Long-dormant','Multiple-order']);ax.set_ylabel(label);ax.grid(axis='y',alpha=.2);ax.legend();ax.margins(y=.15)
fig.suptitle('Equal global capacity still reallocates seats between groups\nLong-group seats: 17 to 73. Separate fixed-79 diagnostic: 1 to 2 hits.',fontsize=13)
save(fig,'03-role05-group-allocation')
files={str(p.relative_to(O)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in F.iterdir()}
(O/'plot-manifest.json').write_text(json.dumps({'png_svg_pairs':3,'new_model_fits':0,'adopted_new_CI':False,'actual_view':'PENDING','files':files},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'figures':3,'total_with_prior':88,'no_new_CI_or_fit':True}))
