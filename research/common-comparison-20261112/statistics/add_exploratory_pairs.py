"""Root-requested complete exploratory appendix, using existing statistics only."""
import sys
sys.dont_write_bytecode=True
import hashlib,itertools,json
from pathlib import Path
import numpy as np,pandas as pd
from statistics_core import paired_intervals,seed_aggregate,split_direction_summary
STAT=Path(__file__).resolve().parent
FAMILIES=['weightedLR','unweightedLR','encodedCatBoost','mean','column-gate','AE']
METRICS=['logloss','brier','AP','AUC','hits','precision','recall']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def csv(f,n):f.to_csv(STAT/n,index=False,lineterminator='\n')
def main():
    names=['canonical-bootstrap-observed.csv','canonical-bootstrap-replicates.csv.gz','canonical-contrasts.json','canonical-paired-bootstrap-intervals.csv','all-run-metrics.csv','all-run-capacities.csv']
    before={n:sha(STAT/n) for n in names};obs=pd.read_csv(STAT/names[0]);reps=pd.read_csv(STAT/names[1]);contrasts=[];definitions=[]
    for info in ['base8','full141']:
        families=FAMILIES+(['nativeCatBoost'] if info=='full141' else [])
        for reference,candidate in itertools.combinations(families,2):
            contrasts.append((info+'::'+candidate,info+'::'+reference,'EXPLORATORY_COMPLETE_SAME_INFORMATION_MODEL_PACKAGE'))
            definitions.append(dict(information=info,candidate_family=candidate,reference_family=reference,processing_package_bridge='nativeCatBoost' in [candidate,reference],after_first_results_requested=True,confirmatory=False))
    assert len(contrasts)==36
    intervals=paired_intervals(obs,reps,contrasts,METRICS+['global_long_selected','global_long_hits'])
    intervals=intervals.loc[~(intervals.scope.eq('long')&intervals.metric.str.startswith('global_long'))].copy()
    intervals['exploratory_after_initial_results']=True;intervals['new_bootstrap_resamples']=0
    csv(intervals,'exploratory-complete-same-information-canonical-CI.csv')
    # All 5 split/seed point effects, using the same frozen main calibrated score.
    m=pd.read_csv(STAT/'all-run-metrics.csv');c=pd.read_csv(STAT/'all-run-capacities.csv')
    m=m.loc[m.period.eq('jan')&m.variant.eq('calibrated')&m.scope.isin(['all','cluster_1_long'])]
    c=c.loc[c.variant.eq('calibrated')&c.policy.isin(['global2937','long79'])].copy();c['scope']=c.policy.map({'global2937':'all','long79':'cluster_1_long'})
    table=m[['run_id','family','information','split_id','seed','scope','logloss','brier','AP','AUC']].merge(c[['run_id','scope','hits','precision','recall','global_long_selected','global_long_hits']],on=['run_id','scope'],validate='one_to_one')
    rows=[]
    for definition in definitions:
        info=definition['information'];a=definition['candidate_family'];b=definition['reference_family']
        for split in sorted(table.split_id.unique()):
            aa=table.loc[table.information.eq(info)&table.family.eq(a)&table.split_id.eq(split)];bb=table.loc[table.information.eq(info)&table.family.eq(b)&table.split_id.eq(split)]
            stochastic=a not in ['weightedLR','unweightedLR'] or b not in ['weightedLR','unweightedLR']
            for seed in ([2026,2027,2028] if stochastic else [None]):
                for scope in ['all','cluster_1_long']:
                    ar=aa.loc[aa.scope.eq(scope)&(aa.seed.isna() if a in ['weightedLR','unweightedLR'] else aa.seed.eq(seed))].iloc[0]
                    br=bb.loc[bb.scope.eq(scope)&(bb.seed.isna() if b in ['weightedLR','unweightedLR'] else bb.seed.eq(seed))].iloc[0]
                    row=definition|dict(split_id=int(split),seed=seed,scope=scope,candidate_run_id=ar.run_id,reference_run_id=br.run_id)
                    for metric in METRICS+['global_long_selected','global_long_hits']:row['delta_'+metric]=float(ar[metric]-br[metric])
                    rows.append(row)
    byseed=pd.DataFrame(rows);csv(byseed,'exploratory-complete-same-information-by-seed.csv')
    ids=['split_id','information','candidate_family','reference_family','scope'];means=seed_aggregate(byseed,ids,['delta_'+m for m in METRICS+['global_long_selected','global_long_hits']]);csv(means,'exploratory-complete-same-information-by-split.csv')
    direction=[]
    for metric in METRICS:direction.append(split_direction_summary(means,['information','candidate_family','reference_family','scope'],'delta_'+metric+'_mean',metric))
    csv(pd.concat(direction,ignore_index=True),'exploratory-complete-same-information-directions.csv')
    assert all(sha(STAT/n)==h for n,h in before.items())
    receipt=dict(status='EXPLORATORY_APPENDIX_COMPLETE_ORIGINAL_TABLES_UNCHANGED',model_pairs=36,new_model_fits=0,new_bootstrap_resamples=0,
        original_source_SHA256=before,plan_sha256=sha(STAT/'exploratory-appendix-plan.md'),code_sha256=sha(Path(__file__)))
    (STAT/'exploratory-appendix-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(intervals.loc[intervals.candidate.isin(['full141::column-gate','full141::AE'])&intervals.reference.eq('full141::mean')&intervals.metric.isin(['logloss','AP','hits'])][['scope','candidate','metric','observed_difference','percentile_2_5','percentile_97_5']].to_string(index=False))
if __name__=='__main__':main()
