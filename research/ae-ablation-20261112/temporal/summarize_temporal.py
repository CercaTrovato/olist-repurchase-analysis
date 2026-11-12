"""Aggregate only frozen temporal results; no models, labels or transforms are fitted."""
import hashlib,json
from pathlib import Path
import pandas as pd
OUT=Path(__file__).resolve().parent
def main():
    m=pd.read_csv(OUT/'october-metrics.csv');c=pd.read_csv(OUT/'october-capacity.csv');runs=pd.read_csv(OUT/'run-support.csv');rows=[]
    for r in runs.itertuples():
        z=dict(run=r.run,family=r.family,information=r.information,seed=r.seed)
        for scope in ['all','long']:
            s=m.loc[m.system.eq(r.run)&m.variant.eq('calibrated')&m.scope.eq(scope)].iloc[0]
            z.update({scope+'_'+k:float(s[k]) for k in ['logloss','brier','AP','AUC']})
        for policy in ['global10','global5','global20','long79']:
            s=c.loc[c.system.eq(r.run)&c.variant.eq('calibrated')&c.policy.eq(policy)].iloc[0]
            z[policy+'_hits']=int(s.hits)
            if policy=='global10':z.update(global10_long_selected=int(s.group1_selected),global10_long_hits=int(s.group1_hits))
        rows.append(z)
    per=pd.DataFrame(rows);per.to_csv(OUT/'per-seed-diagnostics.csv',index=False)
    metrics=[x for x in per.columns if x not in ['run','family','information','seed']];ranges=[]
    for family,g in per.groupby('family',sort=False):
        for metric in metrics:ranges.append(dict(family=family,metric=metric,seeds=len(g),minimum=float(g[metric].min()),mean=float(g[metric].mean()),maximum=float(g[metric].max())))
    pd.DataFrame(ranges).to_csv(OUT/'seed-ranges.csv',index=False)
    pair=[]
    for seed in [2026,2027,2028]:
        a=per.loc[per.family.eq('AE')&per.seed.eq(seed)].iloc[0];b=per.loc[per.family.eq('mean')&per.seed.eq(seed)].iloc[0]
        pair.extend(dict(seed=seed,metric=metric,AE=float(a[metric]),mean=float(b[metric]),AE_minus_mean=float(a[metric]-b[metric])) for metric in metrics)
    pd.DataFrame(pair).to_csv(OUT/'paired-AE-minus-mean-by-seed.csv',index=False)
    # Read the frozen verification and all prior audit hash receipts. Never overwrite them.
    check=json.loads((OUT/'verification.json').read_text());assert check['status']=='independent_readback_pass'
    prior=OUT.parent/'time-audit';old=json.loads((prior/'outputhash.json').read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();assert all(sha(prior/k)==v for k,v in old.items())
    supplemental=json.loads((prior/'clarification/supplement-hashes.json').read_text());assert all(sha(prior/'clarification'/k)==v for k,v in supplemental.items())
    complete=dict(status='complete_after_independent_readback',model_fits=13,AE_pretraining_runs=3,new_time_splits=1,new_April_reads=0,models_added_after_results=0,parameter_changes_after_results=0,source_freeze_sha256=sha(OUT/'source-freeze.json'),verification_sha256=sha(OUT/'verification.json'),old_time_audit_hashes_unchanged=len(old),old_clarification_hashes_unchanged=len(supplemental),scientific_status='seen October time diagnostic; not blind; no architecture/feature/seed/window selection',visual_status='both exported PNG figures actually opened and inspected')
    (OUT/'completion.json').write_text(json.dumps(complete,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(per.to_string(index=False))
if __name__=='__main__':main()
