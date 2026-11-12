"""Plot saved aggregate results only. No training or individual data reads."""
from pathlib import Path
import json, hashlib
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'figures'; OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
COLORS=['#167d8d','#d78c31','#6b56a6']
saved=[]
def save(fig,name):
    fig.savefig(OUT/(name+'.png'),dpi=170,bbox_inches='tight')
    fig.savefig(OUT/(name+'.svg'),bbox_inches='tight')
    plt.close(fig)
    saved.extend([str((OUT/(name+s)).relative_to(ROOT)).replace('\\','/') for s in ('.png','.svg')])

p=pd.read_csv(ROOT/'probability/primary-eval-metrics.csv')
p[['date','strategy']]=p['cell'].str.split('__',expand=True)
families=['weightedLR','unweightedLR','native_catboost_mean3']
actual=list(p.family.unique())
families=[next(v for v in actual if ('cat' in v.lower())), 'weightedLR','unweightedLR']
fig,axes=plt.subplots(1,3,figsize=(13.2,4.4),layout='constrained')
for ax,fam,name in zip(axes,families,['Native CatBoost, mean of 3 seeds','Weighted logistic regression','Unweighted logistic regression']):
    for strategy,color,marker in [('single',COLORS[0],'o'),('pooled',COLORS[1],'s')]:
        q=p[(p.family==fam)&(p.strategy==strategy)].sort_values('date')
        ax.plot(np.arange(3),q.logloss,marker=marker,color=color,label=strategy)
    ax.set_title(name);ax.set_xticks(np.arange(3),['Nov 2017','Dec 2017','Jan 2018']);ax.set_ylabel('All-customer log loss (lower is better)');ax.grid(alpha=.2);ax.legend()
fig.suptitle('More mature historical snapshots did not consistently improve probability quality\nAll eligible customers scored; overlapping historical evaluation windows',fontsize=13)
save(fig,'01-rolling-probability')

c=pd.read_csv(ROOT/'value/capacity-results.csv')
jan=c[(c.evaluation_date=='2018-01-01')&(c.scope=='global')&(c.capacity==.1)]
names={'p_wlr':'Weighted LR','p_ulr':'Unweighted LR','p_catboost':'Native CatBoost'}
rules=['p','purchase_F_M','expected_G']
labels=['Probability','Original p x F x M','Expected goods amount']
fig,axes=plt.subplots(2,3,figsize=(13.2,8),layout='constrained')
for row,strategy in enumerate(['single','pooled']):
    for ax,(family,title) in zip(axes[row],names.items()):
        q=jan[(jan.family==family)&(jan.strategy==strategy)].set_index('rule')
        for rule,label,color in zip(rules,labels,COLORS):
            v=q.loc[rule];ax.scatter(v['hits'],v.captured_G,color=color,s=70,label=label)
        ax.set_title(f'{title} | {strategy}');ax.set_xlabel('Actual repurchasers captured');ax.xaxis.set_major_locator(MaxNLocator(integer=True));ax.set_ylabel('Actual future goods amount captured');ax.grid(alpha=.2);ax.margins(x=.28,y=.3)
handles,leg=axes[0,0].get_legend_handles_labels();fig.legend(handles,leg,loc='outside lower center',ncol=3)
fig.suptitle('Same January capacity: 2,937 customers in every list\nMore captured goods amount can mean fewer repurchasers; no common winner',fontsize=13)
save(fig,'02-january-hits-value-tradeoff')

long=c[(c.evaluation_date=='2018-01-01')&(c.scope!='global')]
fig,axes=plt.subplots(2,3,figsize=(13.2,7.8),layout='constrained')
for col,(family,title) in enumerate(names.items()):
    for row,strategy in enumerate(['single','pooled']):
        ax=axes[row,col];q=long[(long.family==family)&(long.strategy==strategy)].set_index('rule')
        vals=[q.loc[r,'hits'] for r in rules]
        bars=ax.bar(np.arange(3),vals,color=COLORS)
        for b,r in zip(bars,rules):
            ax.text(b.get_x()+b.get_width()/2,b.get_height()+.12,f"{int(q.loc[r,'hits'])} hits\nG={q.loc[r,'captured_G']:,.0f}",ha='center',va='bottom',fontsize=9)
        ax.set_xticks(np.arange(3),['p','p x F x M','Expected G']);ax.set_ylim(0,max(4,max(vals)+2));ax.set_yticks(np.arange(0,max(4,max(vals)+2)+1,1));ax.set_ylabel('Actual repurchasers captured');ax.set_title(f'{title} | {strategy}');ax.grid(axis='y',alpha=.2)
fig.suptitle('Separate long-dormant-group diagnostic: exactly 79 customers\nNot the long-group seats naturally selected in the global list',fontsize=13)
save(fig,'03-long79-rule-comparison')

inputs=['probability/primary-eval-metrics.csv','value/capacity-results.csv']
receipt={'status':'PLOTS_GENERATED_VIEW_PENDING','new_model_fits':0,'source_hashes':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in inputs},'figures':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in saved},'notes':'All points use saved aggregate scores. No new capacity, model, or target search.'}
(ROOT/'plot-generation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'files':len(saved),'families':actual,'long_scopes':long.scope.unique().tolist()}))
