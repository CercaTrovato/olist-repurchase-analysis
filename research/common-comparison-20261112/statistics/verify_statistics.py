"""Independent persisted-output read-back. No fits or new bootstrap analysis.

Selected saved bootstrap replicates are checked against explicitly expanded
customer-copy pools and sklearn, rather than the weighted core implementation.
The root's after-results five-split ensemble supplement is independently scored.
"""
import sys
sys.dont_write_bytecode=True
import hashlib,json,itertools
from pathlib import Path
import numpy as np,pandas as pd
from scipy.special import expit
from sklearn.metrics import log_loss,brier_score_loss,average_precision_score,roc_auc_score
from threadpoolctl import threadpool_limits
from producer_adapter import ROOT,STAT,KEY,load_harness,sha,dump

def read(path):return pd.read_csv(path,dtype={'customer_unique_id':'string','snapshot_date':'string'},float_precision='round_trip')
def close(a,b,tol=1e-11):
    if pd.isna(a) and pd.isna(b):return
    assert abs(float(a)-float(b))<=tol,(a,b)
def rank(f,p):return np.lexsort((f.snapshot_date.astype(str).to_numpy(),f.customer_unique_id.astype(str).to_numpy(),-p))
def metric(y,p):return dict(logloss=float(log_loss(y,p,labels=[0,1])),brier=float(brier_score_loss(y,p)),AP=float(average_precision_score(y,p)),AUC=float(roc_auc_score(y,p)))
def original_scientific_output_hashes():
    run=json.loads((STAT/'statistics-verification.json').read_text());config=json.loads((STAT/'runner-freeze.json').read_text())
    assert sha(STAT/'run_statistics.py')==config['source_sha256']['run_statistics.py']==run['runner_sha256']
    for name,digest in config['producer_source_sha256'].items():assert sha(ROOT/name)==digest
    for name,digest in run['output_sha256'].items():assert sha(STAT/name)==digest,name
    return run

def main():
    run=original_scientific_output_hashes();metadata=json.loads((STAT/'all-run-training-metadata.json').read_text());assert len(metadata)==155
    h=load_harness();source_frame=h.load_frames(20261111)['jan'];canonical_frame=source_frame.sort_values(KEY).reset_index(drop=True);sortix=source_frame.sort_values(KEY).index.to_numpy()
    private=read(STAT/'private/canonical-january-ensembles.csv');assert private[KEY+['y','cluster_id','F']].equals(canonical_frame[KEY+['y','cluster_id','F']])
    cal_frame=h.load_frames(20261111)['cal'];cal_order=cal_frame.sort_values(KEY).index.to_numpy();calprivate=read(STAT/'private/canonical-octcal-ensembles.csv')
    assert calprivate[KEY+['y','cluster_id','F']].equals(cal_frame.sort_values(KEY).reset_index(drop=True)[KEY+['y','cluster_id','F']])
    sums={};nmodels={};canonical_cal={};records={};hashes_checked=0
    for entry in metadata:
        record_path=Path(entry['record_path']);assert sha(record_path)==entry['record_sha256'];r=json.loads(record_path.read_text());records[r['run_id']]=r
        score=ROOT/r['score_file'];assert sha(score)==r['score_sha256'];hashes_checked+=1
        key=(int(r['split_id']),r['information'],r['family'])
        with np.load(score,allow_pickle=False) as arrays:
            p=arrays['jan_calibrated'];sums[key]=sums.get(key,0)+p;nmodels[key]=nmodels.get(key,0)+1
            if key[0]==20261111:canonical_cal[key]=canonical_cal.get(key,0)+arrays['cal_calibrated']
    probabilities={k:sums[k]/nmodels[k] for k in sums};assert len(probabilities)==65
    maximum_ensemble_error=0
    for (split,info,fam),p in probabilities.items():
        if split!=20261111:continue
        name=info+'::'+fam;error=float(np.max(np.abs(p[sortix]-private['probability_'+name].to_numpy())));maximum_ensemble_error=max(maximum_ensemble_error,error)
        close(error,0,1e-15)
        close(float(np.max(np.abs((canonical_cal[split,info,fam]/nmodels[split,info,fam])[cal_order]-calprivate['probability_'+name].to_numpy()))),0,1e-15)
    # Independent source-record comparison for every saved per-run metric/capacity row.
    allm=read(STAT/'all-run-metrics.csv');allc=read(STAT/'all-run-capacities.csv');assert len(allm)==3200 and len(allc)==1280
    scope_map={'all':'all','cluster_0':'group0','cluster_1_long':'group1','cluster_2':'group2','single_order_F1':'F1'}
    for _,r in allm.iterrows():
        source=next(x for x in records[r.run_id]['metrics'] if x['period']==r.period and x['variant']==r.variant and x['scope']==scope_map[r.scope])
        for name in ['logloss','brier','AP','AUC','accuracy','F1']:
            if name in ['AP','AUC'] and not r[name+'_defined']:continue
            close(r[name],source[name])
    for _,r in allc.iterrows():
        source=next(x for x in records[r.run_id]['capacities'] if x['variant']==r.variant and x['policy']==r.policy)
        for name in ['hits','precision','recall']+[f'group{g}_{v}' for g in [0,1,2] for v in ['selected','hits']]:close(r[name],source[name])
    # Jensen check + explicit distinction between average run performance and ensemble performance.
    mainmetrics=read(STAT/'canonical-ensemble-metrics.csv');maincaps=read(STAT/'canonical-ensemble-capacities.csv');assert len(mainmetrics)==65 and len(maincaps)==52
    jensen=[]
    for model in sorted(mainmetrics.model.unique()):
        info,fam=model.split('::');p=private['probability_'+model].to_numpy();y=private.y.to_numpy()
        for scope,mask in [('all',np.ones(len(y),bool)),('cluster_1_long',private.cluster_id.eq(1).to_numpy())]:
            recomputed=metric(y[mask],p[mask]);row=mainmetrics.loc[mainmetrics.model.eq(model)&mainmetrics.scope.eq(scope)].iloc[0]
            for name,value in recomputed.items():close(value,row[name])
            policy='global2937' if scope=='all' else 'long79';k=2937 if scope=='all' else 79;ff=private.loc[mask].reset_index(drop=True);selected=rank(ff,p[mask])[:k]
            observed=int(ff.y.iloc[selected].sum());close(observed,maincaps.loc[maincaps.model.eq(model)&maincaps.policy.eq(policy),'hits'].iloc[0])
        subset=allm.loc[allm.split_id.eq(20261111)&allm.information.eq(info)&allm.family.eq(fam)&allm.scope.eq('all')&allm.period.eq('jan')&allm.variant.eq('calibrated')]
        ll=log_loss(y,p);br=brier_score_loss(y,p);assert ll<=subset.logloss.mean()+1e-12 and br<=subset.brier.mean()+1e-12
        jensen.append(dict(model=model,n_models=len(subset),mean_run_logloss=subset.logloss.mean(),ensemble_logloss=ll,mean_run_brier=subset.brier.mean(),ensemble_brier=br,logloss_Jensen_gap=subset.logloss.mean()-ll))
    pd.DataFrame(jensen).to_csv(STAT/'mean-run-metrics-versus-ensemble.csv',index=False,lineterminator='\n')
    # Check all predeclared and exploratory CI endpoints directly from saved replicate differences.
    reps=read(STAT/'canonical-bootstrap-replicates.csv.gz');observed=read(STAT/'canonical-bootstrap-observed.csv');assert len(reps)==52000
    assert reps.groupby(['scope','replicate']).model.nunique().eq(13).all()
    assert reps.groupby(['scope','replicate']).events.nunique().eq(1).all() and reps.groupby(['scope','replicate']).n.nunique().eq(1).all()
    ci_checks=0
    for file in ['canonical-paired-bootstrap-intervals.csv','exploratory-complete-same-information-canonical-CI.csv']:
        intervals=read(STAT/file)
        for (scope,name),part in intervals.groupby(['scope','metric']):
            wide=reps.loc[reps.scope.eq(scope)].pivot(index='replicate',columns='model',values=name);obs=observed.loc[observed.scope.eq(scope)].set_index('model')
            for _,r in part.iterrows():
                difference=(wide[r.candidate]-wide[r.reference]).to_numpy();difference=difference[np.isfinite(difference)]
                lo,hi=np.percentile(difference,[2.5,97.5]);close(lo,r.percentile_2_5);close(hi,r.percentile_97_5);close(difference.mean(),r.bootstrap_mean)
                close(obs.loc[r.candidate,name]-obs.loc[r.reference,name],r.observed_difference);ci_checks+=1
    # Known saved replicate IDs: explicitly expand repeated customer instances and rerank.
    requested={1,2,10,50,100,250,500,1000,1500,2000};expanded_checks=0;expanded_max_error=0
    for scope,k,seed in [('all',2937,2026111201),('long',79,2026111202)]:
        mask=np.ones(len(private),bool) if scope=='all' else private.cluster_id.eq(1).to_numpy();f=private.loc[mask].reset_index(drop=True);n=len(f);rng=np.random.default_rng(seed);yy=f.y.to_numpy();gg=f.cluster_id.to_numpy();ref=reps.loc[reps.scope.eq(scope)].set_index(['replicate','model'])
        for replicate in range(1,2001):
            counts=rng.multinomial(n,np.full(n,1/n))
            if replicate not in requested:continue
            copy_indices=np.repeat(np.arange(n),counts);copied=f.iloc[copy_indices].reset_index(drop=True);yc=yy[copy_indices]
            for model in sorted(mainmetrics.model.unique()):
                pc=f['probability_'+model].to_numpy()[copy_indices];computed=metric(yc,pc);r=ref.loc[(replicate,model)]
                for name,value in computed.items():error=abs(value-r[name]);expanded_max_error=max(expanded_max_error,error);close(value,r[name])
                take=rank(copied,pc)[:k];close(yc[take].sum(),r.hits);close(copied.cluster_id.to_numpy()[take].tolist().count(1),r.global_long_selected);close(copied.y.to_numpy()[take][copied.cluster_id.to_numpy()[take]==1].sum(),r.global_long_hits)
                expanded_checks+=1
    # Calibration denominators, boundaries, probabilities and Wilson intervals from persisted scores.
    bins=read(STAT/'canonical-calibration-all-bins.csv');assert len(bins)==100
    for (model,scope),b in bins.groupby(['model','scope']):
        b=b.sort_values('bin');edge=np.quantile(calprivate['probability_'+model],np.linspace(0,1,11));mask=np.ones(len(private),bool) if scope=='all' else private.cluster_id.eq(1).to_numpy();p=private.loc[mask,'probability_'+model].to_numpy();y=private.loc[mask,'y'].to_numpy();assignment=np.searchsorted(edge[1:-1],p,side='right')
        assert b.n.sum()==len(y) and b.events.sum()==y.sum()
        for j,(_,r) in enumerate(b.iterrows()):
            inside=assignment==j;n=int(inside.sum());events=int(y[inside].sum());assert n==r.n and events==r.events;close(edge[j],r.cal_quantile_lower);close(edge[j+1],r.cal_quantile_upper)
            if n:
                close(p[inside].mean(),r.mean_probability);close(events/n,r.observed_rate)
                z=1.959963984540054;rate=events/n;den=1+z*z/n;center=(rate+z*z/(2*n))/den;half=z*np.sqrt(rate*(1-rate)/n+z*z/(4*n*n))/den;close(center-half,r.wilson_low);close(center+half,r.wilson_high)
    # Cross-check root independently produced seed-mean table, without treating it as ensemble scores.
    root_table=read(ROOT/'root-independent-split-means.csv');ours=read(STAT/'main-model-information-by-split.csv');root_comparisons=[]
    for _,r in root_table.iterrows():
        globalrow=ours.loc[ours.family.eq(r.family)&ours.information.eq(r.information)&ours.split_id.eq(r.split_id)&ours.scope.eq('all')].iloc[0]
        longrow=ours.loc[ours.family.eq(r.family)&ours.information.eq(r.information)&ours.split_id.eq(r.split_id)&ours.scope.eq('cluster_1_long')].iloc[0]
        for name,value in [('logloss',globalrow.logloss_mean),('AP',globalrow.AP_mean),('global_hits',globalrow.hits_mean),('long79_hits',longrow.hits_mean),('global_long_seats',globalrow.global_long_selected_mean),('global_long_hits',globalrow.global_long_hits_mean)]:
            close(value,r[name]);root_comparisons.append(dict(split_id=r.split_id,information=r.information,family=r.family,metric=name,difference=value-r[name]))
    pd.DataFrame(root_comparisons).to_csv(STAT/'root-independent-summary-crosscheck.csv',index=False,lineterminator='\n')
    # Independently check the root's separately labeled post-results same-ensemble stability supplement.
    supplemental=read(ROOT/'ensemble-five-split-results.csv');suppdirections=read(ROOT/'ensemble-five-split-directions.csv');suppstability=read(ROOT/'ensemble-five-split-selection-stability.csv')
    assert len(supplemental)==130 and len(suppstability)==260;lists={};supp_checks=0;max_supp_error=0
    for _,r in supplemental.iterrows():
        p=probabilities[int(r.split_id),r.information,r.family];mask=np.ones(len(source_frame),bool) if r.scope=='all' else source_frame.cluster_id.eq(1).to_numpy();f=source_frame.loc[mask].reset_index(drop=True);pp=p[mask];y=f.y.to_numpy();rr=metric(y,pp)
        for name,value in rr.items():max_supp_error=max(max_supp_error,abs(value-r[name]));close(value,r[name])
        selected=rank(f,pp)[:int(r.k)];assert y[selected].sum()==r.hits
        global_indices=np.flatnonzero(mask)[selected];lists[int(r.split_id),r.information,r.family,r.scope]=set(map(int,global_indices));supp_checks+=1
    for _,r in suppstability.iterrows():
        a=lists[int(r.split_a),r.information,r.family,r.scope];b=lists[int(r.split_b),r.information,r.family,r.scope];close(len(a&b)/len(a|b),r.jaccard);close(len(a-b),r.replacements)
    for _,r in suppdirections.iterrows():
        cell=supplemental.loc[supplemental.information.eq(r.information)&supplemental.family.eq(r.family)&supplemental.scope.eq(r.scope)].set_index('split_id')
        ref=supplemental.loc[supplemental.information.eq('base8')&supplemental.family.eq('weightedLR')&supplemental.scope.eq(r.scope)].set_index('split_id');d=cell[r.metric]-ref[r.metric];benefit=-d if r.metric in ['logloss','brier'] else d;tol=0 if r.metric=='hits' else 1e-12
        assert int((benefit>tol).sum())==r.wins and int((benefit.abs()<=tol).sum())==r.ties and int((benefit < -tol).sum())==r.losses
    supplement_review=dict(status='PASS_TARGETED_POST_RESULT_SENSITIVITY_REVIEW',source_code='ensemble_split_audit.py',source_code_sha256=sha(ROOT/'ensemble_split_audit.py'),ensemble_rows_independently_recomputed=supp_checks,selection_pairs_recomputed=260,direction_rows_recomputed=len(suppdirections),maximum_metric_difference=max_supp_error,
        interpretation='all 13 pre-existing mean(calibrated probability) systems rescored across five overlapping splits; results-after supplementary sensitivity, not new periods or a prespecified independent confirmatory test',new_fits=0,new_bootstrap=0,
        implementation_caveat='root sort uses customer key only, whereas canonical key includes date; all cohort dates identical, so the rankings are equivalent here')
    dump(STAT/'root-ensemble-supplement-review.json',supplement_review)
    # Final sources unchanged; no main table, replicate or original contrast overwrite.
    original_scientific_output_hashes()
    receipt=dict(status='PASS_INDEPENDENT_STATISTICS_READBACK',source_models=155,source_score_SHA_rechecked=hashes_checked,
        saved_run_metric_rows_source_crosschecked=3200,saved_run_capacity_rows_source_crosschecked=1280,
        canonical_models=13,canonical_mean_probability_max_error=maximum_ensemble_error,canonical_metric_and_policy_rows_checked=117,
        all_bootstrap_interval_rows_recomputed=ci_checks,existing_bootstrap_replicate_rows=52000,
        expanded_customer_copy_replicate_checks=expanded_checks,expanded_replicate_ids=sorted(requested),expanded_pool_sklearn_metric_max_error=expanded_max_error,
        all_calibration_bins_recomputed=100,root_independent_seedmean_comparisons=len(root_comparisons),root_ensemble_supplement=supplement_review,
        model_fits=0,new_bootstrap_resamples=0,formal_model_adopted=False,april_rows_parsed=0,code_sha256=sha(Path(__file__)))
    dump(STAT/'readback-verification.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k!='root_ensemble_supplement'},indent=2),flush=True)
    print('Root ensemble supplement independently verified',supp_checks,'rows;',len(suppstability),'selection pairs',flush=True)
if __name__=='__main__':
    with threadpool_limits(limits=2):main()
