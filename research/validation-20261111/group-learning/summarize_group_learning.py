"""Aggregate frozen outputs only; no fitting or candidate selection."""
from pathlib import Path
import pandas as pd
OUT=Path(__file__).resolve().parent
n=pd.read_csv(OUT/'natural_probability_metrics.csv')
r=pd.read_csv(OUT/'capacity_metrics.csv')
jan=n.query("period == 'jan'").copy()
cap=r.query("period == 'jan' and (threshold == 0.1 or scope == 'H05_cluster1')")
piv=cap.pivot(index=['name','scale'],columns='scope',values='hits').reset_index().rename(columns={'all':'hits2937','H05_cluster1':'long_hits79'})
summary=jan.merge(piv,on=['name','scale'])
summary.to_csv(OUT/'january_summary.csv',index=False,lineterminator='\n')
seeds=summary.loc[summary.name.str.startswith('residual_')].copy()
seeds['family']=seeds.name.str.replace(r'_s\d+$','',regex=True)
fields=['log_loss','brier','ap','roc_auc','hits2937','long_hits79']
rows=[]
for (family,scale),g in seeds.groupby(['family','scale']):
    row=dict(family=family,scale=scale,seeds=len(g))
    for field in fields:
        row.update({field+'_mean':g[field].mean(),field+'_sd':g[field].std(ddof=1),field+'_min':g[field].min(),field+'_max':g[field].max()})
    rows.append(row)
pd.DataFrame(rows).to_csv(OUT/'seed_summary.csv',index=False,lineterminator='\n')
print(summary[['name','scale','log_loss','brier','ap','hits2937','long_hits79']].to_string(index=False))
print(pd.DataFrame(rows).to_string(index=False))
