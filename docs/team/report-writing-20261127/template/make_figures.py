from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Patch
B=Path(__file__).resolve().parent
F=B/'figures';F.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'Times New Roman','font.size':11,'axes.labelsize':11,'xtick.labelsize':11,'ytick.labelsize':11,'legend.fontsize':11,'svg.fonttype':'none','pdf.fonttype':42,'ps.fonttype':42,'svg.hashsalt':'is6400-layout-sample-v1','axes.spines.top':False,'axes.spines.right':False})
fig,ax=plt.subplots(figsize=(160/25.4,68/25.4));fig.subplots_adjust(left=.13,right=.98,top=.94,bottom=.27)
df=pd.read_csv(B/'data/feature-experiment-results.csv');q=df[df.fraction.eq(.1)].set_index('method').loc[['F0','G1','G2']]
assert q.hits.tolist()==[50,49,48] and q.K.unique().tolist()==[2937]
ax.bar(range(3),q.hits,color=['#315c85','#2a7f82','#b36736'],width=.55)
ax.set_xticks(range(3),['F0\nBase fields','G1\nDelivery fields','G2\nReview fields']);ax.set_ylim(0,60);ax.set_yticks([0,20,40,60]);ax.set_ylabel('Repeat buyers in the list')
ax.grid(axis='y',color='#dce1e5',linewidth=.6);ax.set_axisbelow(True)
for i,n in enumerate(q.hits):ax.text(i,n+1,str(n),ha='center',va='bottom')
for ext in ['pdf','svg']:fig.savefig(F/('feature-comparison.'+ext),metadata={'CreationDate':None,'ModDate':None} if ext=='pdf' else {'Date':None})
plt.close(fig)
fig,ax=plt.subplots(figsize=(160/25.4,75/25.4));fig.subplots_adjust(left=.20,right=.98,top=.95,bottom=.38)
records=[('2017-04-01','2017-10-01','2017-12-30',1),('2017-07-01','2018-01-01','2018-04-01',0)]
for start,snap,end,y in records:
 lo,mid,hi=[mdates.date2num(pd.Timestamp(x)) for x in [start,snap,end]]
 ax.broken_barh([(lo,mid-lo)],(y-.13,.26),facecolors='#315c85')
 ax.broken_barh([(mid,hi-mid)],(y-.13,.26),facecolors='#b36736')
 ax.plot(mid,y,'o',color='#162f43',markersize=5,zorder=3)
ax.set_yticks([1,0],['Train\n21,160','Develop\n29,368']);ax.set_ylim(-.48,1.48)
ticks=pd.to_datetime(['2017-04-01','2017-07-01','2017-10-01','2018-01-01','2018-04-01'])
ax.set_xticks([mdates.date2num(x) for x in ticks],[x.strftime('%b\n%Y') for x in ticks]);ax.set_xlim(mdates.date2num(ticks[0])-5,mdates.date2num(ticks[-1])+5)
ax.spines[['top','left','right']].set_visible(False);ax.tick_params(axis='y',length=0,pad=8);ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
fig.legend(handles=[Patch(color='#315c85',label='Past six calendar months'),Patch(color='#b36736',label='Next 90 days')],loc='lower center',bbox_to_anchor=(.5,.015),frameon=False,ncol=1,handlelength=1.4,labelspacing=.2)
for ext in ['pdf','svg']:fig.savefig(F/('time-windows.'+ext),metadata={'CreationDate':None,'ModDate':None} if ext=='pdf' else {'Date':None})
plt.close(fig)

