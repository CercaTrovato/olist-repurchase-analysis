"""Aggregate chart support and final integrity receipt; no model fitting."""
import sys
sys.dont_write_bytecode=True
import gzip,hashlib,json
from pathlib import Path
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    bins=pd.read_csv(OUT/'calibration-all-bins.csv')
    assert len(bins)==15*4*10
    metrics=pd.read_csv(OUT/'january-metrics-all-scopes.csv')
    assert len(metrics)==21*4
    support=[]
    for (scope,method),b in bins.groupby(['scope','method']):
        row=metrics.loc[metrics.scope.eq(scope)&metrics.method.eq(method)].iloc[0]
        assert b.n.sum()==row.n and b.events.sum()==row.events
        support.append(dict(scope=scope,method=method,n=int(b.n.sum()),events=int(b.events.sum()),bins=10,nonempty_bins=int((b.n>0).sum())))
    pd.DataFrame(support).to_csv(OUT/'calibration-conservation-check.csv',index=False)
    for method in ['LR8','weightedLR','weightedLR-prior-corrected','weightedLR-oof-Platt']:
        fig,axes=plt.subplots(2,2,figsize=(14,8),gridspec_kw={'height_ratios':[3,1.3]})
        for col,scope in enumerate(['all','cluster_1_long']):
            b=bins.loc[bins.scope.eq(scope)&bins.method.eq(method)].sort_values('bin')
            non=b.loc[b.n>0];ax=axes[0,col]
            ax.errorbar(non.mean_probability,non.observed_rate,yerr=np.vstack([non.observed_rate-non.wilson_low,non.wilson_high-non.observed_rate]),fmt='o',capsize=3,color='#2166ac')
            lim=max(float(non.mean_probability.max()),float(non.wilson_high.max()))*1.08
            ax.plot([0,lim],[0,lim],ls='--',color='#777777');ax.set(xlim=(0,lim),ylim=(0,lim),title=scope,xlabel='Mean predicted probability',ylabel='January observed rate (95% Wilson)');ax.grid(alpha=.2)
            ax=axes[1,col];ax.axis('off')
            cell=[[str(int(n))+'/'+str(int(e)) for n,e in zip(b.n,b.events)],
                  [f'{x:.4f}' if np.isfinite(x) else 'empty' for x in b.mean_probability],
                  [f'{x:.4f}' if np.isfinite(x) else 'empty' for x in b.observed_rate]]
            tab=ax.table(cellText=cell,rowLabels=['N/events','Mean p','Observed'],colLabels=[str(i) for i in b.bin],loc='center',cellLoc='center');tab.auto_set_font_size(False);tab.set_fontsize(8);tab.scale(1,1.5)
        fig.suptitle(method+': all ten Oct-defined bins, including empty bins',fontsize=15)
        fig.text(.06,.015,'N/events are displayed for every bin; Jan was not used to choose bin boundaries. Error bars quantify bin event-rate uncertainty.\nModels fixed; January already seen. No top-K filtering. Probability calibration is separate from ranking.',fontsize=9)
        fig.tight_layout(rect=[.03,.06,1,.95])
        for ext in ['png','svg']:fig.savefig(OUT/f'figures/calibration-support-{method}.{ext}',dpi=160)
        plt.close(fig)
    # Lossless compact copy for handoff; retain the original complete CSV as the auditable source.
    curve=OUT/'all-pr-roc-curves.csv'
    with curve.open('rb') as src,gzip.open(OUT/'all-pr-roc-curves.csv.gz','wb',compresslevel=6) as dst:
        while chunk:=src.read(1024*1024):dst.write(chunk)
    digest=hashlib.sha256()
    with gzip.open(OUT/'all-pr-roc-curves.csv.gz','rb') as src:
        while chunk:=src.read(1024*1024):digest.update(chunk)
    assert digest.hexdigest()==sha(curve)
    core=json.loads((OUT/'verification.json').read_text())
    unchanged={p:sha(Path(p))==h for p,h in core['input_sha256'].items()}
    assert all(unchanged.values())
    final=dict(status='complete',april_rows_parsed=0,calibration_bin_conservation_groups=len(support),input_files_unchanged=len(unchanged),
        core_run_plan_sha256=core['plan_sha256'],final_plan_with_single_order_supplement_sha256=sha(OUT/'frozen-plan.md'),
        full_curves_lossless_gzip_verified=True,files={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name not in ['final-verification.json']})
    (OUT/'final-verification.json').write_text(json.dumps(final,indent=2)+'\n',encoding='utf-8')
    print('Verified 600 calibration bins, 84 ranking/proper rows, portable predictor via supplement,',len(unchanged),'unchanged inputs')
if __name__=='__main__':main()
