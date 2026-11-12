"""Complete frozen 155-run statistics. No training, tuning, or partial results."""
import sys
sys.dont_write_bytecode=True
import hashlib,itertools,json,math,time
from pathlib import Path
import numpy as np,pandas as pd
from scipy.special import expit
from sklearn.metrics import average_precision_score,roc_auc_score
from threadpoolctl import threadpool_limits
from producer_adapter import ROOT,STAT,SPLITS,SEEDS,MAIN_FAMILIES,DETERMINISTIC,load_complete_matrix,sha,dump
from statistics_core import FixedScoreEvaluator,canonical_ensemble,paired_customer_bootstrap,paired_intervals,seed_aggregate,split_direction_summary,KEY

METRICS=['logloss','brier','AP','AUC'];CANONICAL=20261111
PAIR_METRICS=METRICS+['hits','precision','recall']
INFO=['base8','full141']

def csv(frame,name):frame.to_csv(STAT/name,index=False,lineterminator='\n')
def scopes(f):return [('all',np.ones(len(f),bool))]+[(f'cluster_{g}'+('_long' if g==1 else ''),f.cluster_id.eq(g).to_numpy()) for g in [0,1,2]]+[('single_order_F1',f.F.eq(1).to_numpy())]
def order(f,z):return np.lexsort((f.snapshot_date.astype(str).to_numpy(),f.customer_unique_id.astype(str).to_numpy(),-np.asarray(z)))
def confusion(y,p):
    pred=p>=.5;tp=int(np.sum(pred&(y==1)));fp=int(np.sum(pred&(y==0)));fn=int(np.sum(~pred&(y==1)));tn=int(np.sum(~pred&(y==0)))
    denom=math.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))
    return dict(TP=tp,FP=fp,FN=fn,TN=tn,accuracy=(tp+tn)/len(y),F1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.,MCC=(tp*tn-fp*fn)/denom if denom else 0.)
def ece10(y,p):
    bins=np.minimum((p*10).astype(int),9);value=0
    for b in range(10):
        mask=bins==b
        if mask.any():value+=mask.mean()*abs(p[mask].mean()-y[mask].mean())
    return float(value)
def natural(f,p):
    ev=FixedScoreEvaluator(f,p);row=ev.empirical_metrics();row.update(mean_probability=float(np.mean(p)),ece10=ece10(ev.y,p),**confusion(ev.y,p))
    # sklearn convention AP=0 for no events, but label it non-informative.
    row['AP_defined']=bool(row['events']>0)
    row['AUC_defined']=bool(0<row['events']<row['n'])
    return row
def capacity(f,p,policy):
    if policy=='long79':mask=f.cluster_id.eq(1).to_numpy();ff=f.loc[mask].reset_index(drop=True);pp=p[mask];k=79
    else:ff=f;pp=p;k={'global2937':2937,'global5':1469,'global20':5874}[policy]
    ev=FixedScoreEvaluator(ff,pp);r=ev.topk(k);taken=ev.order[:k]
    for g in [0,1,2]:
        mask=ff.cluster_id.to_numpy()[taken]==g;r[f'group{g}_selected']=int(mask.sum());r[f'group{g}_hits']=int(ff.y.to_numpy()[taken][mask].sum())
    return r
def finite_compare(a,b,tol=1e-11):
    if a is None or (isinstance(a,float) and not np.isfinite(a)):return b is None or not np.isfinite(b)
    if b is None or not np.isfinite(b):return False
    return abs(float(a)-float(b))<=tol
def model_name(information,family):return information+'::'+family

def primary_lookup(metrics,capacities):
    mm=metrics.loc[metrics.period.eq('jan')&metrics.variant.eq('calibrated')].set_index(['run_id','scope'])
    cc=capacities.loc[capacities.variant.eq('calibrated')].set_index(['run_id','policy'])
    result={}
    for run_id in metrics.run_id.unique():
        for scope,policy in [('all','global2937'),('cluster_1_long','long79')]:
            m=mm.loc[(run_id,scope)];c=cc.loc[(run_id,policy)]
            result[run_id,scope]={k:float(m[k]) for k in METRICS}|{k:float(c[k]) for k in ['hits','precision','recall','global_long_selected','global_long_hits']}
    return result

def controlled_pairs(runs,lookup):
    cells={(int(r.record['split_id']),r.record['information'],r.record['family'],r.record['seed']):r.record['run_id'] for r in runs}
    deterministic_ids={r.record['run_id'] for r in runs if r.record['family'] in DETERMINISTIC}
    rows=[]
    def append(split,family,information,seed,kind,candidate,reference,interaction=False):
        for scope in ['all','cluster_1_long']:
            row=dict(split_id=split,family=family,information=information,seed=seed,contrast=kind,scope=scope,
                candidate_run_ids=json.dumps(candidate),reference_run_ids=json.dumps(reference),reference_family='encodedCatBoost' if kind=='encoding_missing_processing_package_bridge' else 'weightedLR' if 'model' in kind or interaction or kind.startswith('primary') else family,
                deterministic_reference_reused=family not in DETERMINISTIC and any(rid in deterministic_ids for rid,sign in reference))
            for metric in PAIR_METRICS+['global_long_selected','global_long_hits']:
                row['delta_'+metric]=sum(sign*lookup[rid,scope][metric] for rid,sign in candidate)-sum(sign*lookup[rid,scope][metric] for rid,sign in reference)
            rows.append(row)
    for split in SPLITS:
        for fam in MAIN_FAMILIES:
            for seed in ([None] if fam in DETERMINISTIC else SEEDS):
                base=cells[split,'base8',fam,seed];full=cells[split,'full141',fam,seed]
                append(split,fam,'full_minus_base',seed,'information',[(full,1)],[(base,1)])
                for info,rid in [('base8',base),('full141',full)]:
                    if fam!='weightedLR':append(split,fam,info,seed,'model_within_information',[(rid,1)],[(cells[split,info,'weightedLR',None],1)])
                    if info=='full141':append(split,fam,info,seed,'primary_vs_weightedLR_base8',[(rid,1)],[(cells[split,'base8','weightedLR',None],1)])
                    elif fam!='weightedLR':append(split,fam,info,seed,'primary_vs_weightedLR_base8',[(rid,1)],[(cells[split,'base8','weightedLR',None],1)])
                if fam!='weightedLR':append(split,fam,'full_minus_base',seed,'information_model_interaction',[(full,1),(base,-1)],[(cells[split,'full141','weightedLR',None],1),(cells[split,'base8','weightedLR',None],-1)],True)
        for seed in SEEDS:
            native=cells[split,'full141','nativeCatBoost',seed];encoded=cells[split,'full141','encodedCatBoost',seed]
            append(split,'nativeCatBoost','full141',seed,'encoding_missing_processing_package_bridge',[(native,1)],[(encoded,1)])
            append(split,'nativeCatBoost','full141',seed,'primary_vs_weightedLR_base8',[(native,1)],[(cells[split,'base8','weightedLR',None],1)])
    return pd.DataFrame(rows)

def stability(runs,selections,primary):
    groups={};across={};rows=[]
    for run in runs:
        r=run.record
        groups.setdefault((r['split_id'],r['information'],r['family']),[]).append(r)
        across.setdefault((r['seed'],r['information'],r['family']),[]).append(r)
    for kind,mapping in [('within_split_across_seeds',groups),('within_seed_across_splits',across)]:
        for _,members in mapping.items():
            for a,b in itertools.combinations(sorted(members,key=lambda r:r['run_id']),2):
                for scope,policy in [('all','global2937'),('cluster_1_long','long79')]:
                    sa=selections[a['run_id'],policy];sb=selections[b['run_id'],policy]
                    rows.append(dict(kind=kind,information=a['information'],family=a['family'],run_a=a['run_id'],run_b=b['run_id'],split_a=a['split_id'],split_b=b['split_id'],seed_a=a['seed'],seed_b=b['seed'],scope=scope,policy=policy,jaccard=len(sa&sb)/len(sa|sb),changed=len(sa^sb),hits_a=primary[a['run_id'],scope]['hits'],hits_b=primary[b['run_id'],scope]['hits'],global_long_selected_a=primary[a['run_id'],scope]['global_long_selected'],global_long_selected_b=primary[b['run_id'],scope]['global_long_selected']))
    return pd.DataFrame(rows)

def wilson(events,n):
    if not n:return np.nan,np.nan
    z=1.959963984540054;rate=events/n;den=1+z*z/n;center=(rate+z*z/(2*n))/den;half=z*np.sqrt(rate*(1-rate)/n+z*z/(4*n*n))/den
    return float(center-half),float(center+half)

def calibration_bins(ensembles,cal_ensembles):
    rows=[]
    chosen=[('base8','weightedLR'),('full141','encodedCatBoost'),('full141','nativeCatBoost'),('full141','column-gate'),('full141','AE')]
    for info,fam in chosen:
        name=model_name(info,fam);jan=ensembles[name];cal=cal_ensembles[name];edge=np.quantile(cal.ensemble_probability,np.linspace(0,1,11))
        for scope in ['all','cluster_1_long']:
            mask=np.ones(len(jan),bool) if scope=='all' else jan.cluster_id.eq(1).to_numpy();p=jan.ensemble_probability.to_numpy()[mask];y=jan.y.to_numpy()[mask];assigned=np.searchsorted(edge[1:-1],p,side='right')
            for b in range(10):
                inside=assigned==b;n=int(inside.sum());events=int(y[inside].sum());lo,hi=wilson(events,n)
                rows.append(dict(model=name,information=info,family=fam,scope=scope,bin=b+1,cal_quantile_lower=float(edge[b]),cal_quantile_upper=float(edge[b+1]),assignment_lower='-inf' if b==0 else float(edge[b]),assignment_upper='+inf' if b==9 else float(edge[b+1]),n=n,events=events,mean_probability=float(p[inside].mean()) if n else np.nan,observed_rate=events/n if n else np.nan,wilson_low=lo,wilson_high=hi,cal_boundary_status='Octcal ensemble prediction; constituent calibrators fit on same cal labels; in-sample boundaries'))
            assert sum(r['n'] for r in rows[-10:])==mask.sum() and sum(r['events'] for r in rows[-10:])==y.sum()
    return pd.DataFrame(rows)

def main():
    start=time.perf_counter();(STAT/'private').mkdir(exist_ok=True)
    runs,frames,binding=load_complete_matrix();print('Complete 155 identities + score SHA verified; begin independent metrics',flush=True)
    all_metrics=[];all_caps=[];cal_audit=[];rank_audit=[];selections={};source_errors=[];metadata=[]
    for ri,run in enumerate(runs):
        r=run.record;a=run.arrays;tag={k:r[k] for k in ['run_id','family','information','split_id','seed']};ff=frames[int(r['split_id'])]
        source_metric={(x['period'],x['variant'],x['scope']):x for x in r['metrics']};source_caps={(x['variant'],x['policy']):x for x in r['capacities']}
        variants=['raw','calibrated']+(['prior'] if r['family']=='weightedLR' else [])
        for period in ['cal','jan']:
            f=ff[period]
            for variant in variants:
                p=a[period+'_'+variant]
                for scope,mask in scopes(f):
                    row=tag|dict(period=period,variant=variant,scope=scope,main_comparison=variant=='calibrated',probability_status='weighted_training_scale_diagnostic' if r['family']=='weightedLR' and variant=='raw' else 'calibrated' if variant=='calibrated' else 'uncalibrated_diagnostic',calibration_resubstitution=period=='cal' and variant=='calibrated')|natural(f.loc[mask].reset_index(drop=True),p[mask])
                    producer_scope={'all':'all','cluster_0':'group0','cluster_1_long':'group1','cluster_2':'group2','single_order_F1':'F1'}[scope];source=source_metric[period,variant,producer_scope]
                    for metric in METRICS+['accuracy','F1']:
                        if metric in ['AP','AUC'] and not row[metric+'_defined']:continue
                        if not finite_compare(row[metric],source[metric]):source_errors.append(dict(run_id=r['run_id'],kind='metric',period=period,variant=variant,scope=scope,metric=metric,recomputed=row[metric],producer=source[metric]))
                    assert row['n']==source['n'] and row['events']==source['positives']
                    all_metrics.append(row)
                if period=='jan':
                    for policy in ['global2937','global5','global20','long79']:
                        row=tag|dict(variant=variant,policy=policy,main_comparison=variant=='calibrated')|capacity(f,p,policy)
                        source=source_caps[variant,policy]
                        for metric in ['hits','precision','recall']+[f'group{g}_{v}' for g in [0,1,2] for v in ['selected','hits']]:
                            if not finite_compare(row[metric],source[metric]):source_errors.append(dict(run_id=r['run_id'],kind='capacity',variant=variant,policy=policy,metric=metric,recomputed=row[metric],producer=source[metric]))
                        all_caps.append(row)
                        if variant=='calibrated' and policy in ['global2937','long79']:
                            if policy=='long79':mask=f.cluster_id.eq(1).to_numpy();ix=np.flatnonzero(mask);ordered=order(f.loc[mask].reset_index(drop=True),p[mask]);selected=set(ix[ordered[:79]])
                            else:selected=set(order(f,p)[:2937])
                            selections[r['run_id'],policy]=selected
        # Independent calibration formula and projected-gradient check, never refit.
        c=r['calibration'];z=a['cal_logit'];y=ff['cal'].y.to_numpy();slope=float(c['a']);intercept=float(c['b']);t=slope*z+intercept;e=expit(t)-y
        grad=np.array([e@z+slope/1e6,e.sum()]);projected=np.array([slope-max(1e-6,slope-grad[0]),grad[1]]);obj=float(np.sum(np.logaddexp(0,t)-y*t)+.5*slope*slope/1e6)
        p_error=max(float(np.max(np.abs(expit(slope*a[p+'_logit']+intercept)-a[p+'_calibrated']))) for p in ['fit','cal','jan'])
        if abs(obj-c['objective'])>1e-8 or np.max(np.abs(grad-c['gradient']))>1e-8 or abs(np.max(np.abs(projected))-c['projected_gradient_inf'])>1e-8 or p_error>1e-12:raise ValueError('Calibration formula/gradient/score mismatch: '+r['run_id'])
        cal_audit.append(tag|dict(a=slope,b=intercept,active_lower_bound=c['active_lower_bound'],projected_gradient_inf=float(np.max(np.abs(projected))),actual_meets_requested_1e_10=bool(np.max(np.abs(projected))<=1e-10),success=c['success'],message=c['message'],cal_n=len(y),cal_events=int(y.sum()),objective=obj,calibrated_probability_replay_max_error=p_error))
        jf=ff['jan'];longmask=jf.cluster_id.eq(1).to_numpy()
        for scope,mask,k in [('all',np.ones(len(jf),bool),2937),('cluster_1_long',longmask,79)]:
            sub=jf.loc[mask].reset_index(drop=True);zs={name:a['jan_'+name][mask] for name in ['logit','raw','calibrated']};orders={name:order(sub,value) for name,value in zs.items()};sets={name:set(v[:k]) for name,v in orders.items()}
            rank_audit.append(tag|dict(scope=scope,k=k,logit_vs_raw_changed=len(sets['logit']^sets['raw']),logit_vs_calibrated_changed=len(sets['logit']^sets['calibrated']),raw_vs_calibrated_changed=len(sets['raw']^sets['calibrated']),n_unique_logit=len(np.unique(zs['logit'])),n_unique_raw=len(np.unique(zs['raw'])),n_unique_calibrated=len(np.unique(zs['calibrated']))))
        if rank_audit[-2]['logit_vs_calibrated_changed']!=r['Jan_raw_vs_calibrated_selected_symmetric_difference']:raise ValueError('Producer ranking diagnostic differs')
        metadata.append(tag|dict(calibration=r['calibration'],metadata=r['metadata'],record_path=str(run.record_path),record_sha256=sha(run.record_path),score_file=r['score_file'],score_sha256=r['score_sha256']))
        if (ri+1)%25==0:print('Independently recomputed runs',ri+1,flush=True)
    if source_errors:
        csv(pd.DataFrame(source_errors),'producer-differences.csv');raise ValueError('Producer metrics differ: preserve diagnostics and stop statistic stage')
    metrics=pd.DataFrame(all_metrics);caps=pd.DataFrame(all_caps)
    csv(metrics,'all-run-metrics.csv');csv(caps,'all-run-capacities.csv');csv(pd.DataFrame(cal_audit),'calibration-optimization-audit.csv');csv(pd.DataFrame(rank_audit),'finite-ranking-correspondence.csv');dump(STAT/'all-run-training-metadata.json',metadata)
    assert len(metrics)==3200 and len(caps)==1280
    seed_metrics=seed_aggregate(metrics,['split_id','information','family','variant','period','scope'],METRICS+['accuracy','F1','MCC','ece10'])
    seed_caps=seed_aggregate(caps,['split_id','information','family','variant','policy'],['hits','precision','recall','global_long_selected','global_long_hits'])
    csv(seed_metrics,'within-split-seed-metrics.csv');csv(seed_caps,'within-split-seed-capacities.csv')
    primary=primary_lookup(metrics,caps);pairs=controlled_pairs(runs,primary);csv(pairs,'controlled-paired-differences-by-seed.csv')
    pair_ids=['split_id','family','information','contrast','scope'];pair_cols=['delta_'+m for m in PAIR_METRICS+['global_long_selected','global_long_hits']]
    pair_means=seed_aggregate(pairs,pair_ids,pair_cols);csv(pair_means,'controlled-paired-differences-by-split.csv')
    directions=[]
    for metric in PAIR_METRICS:
        directions.append(split_direction_summary(pair_means,['family','information','contrast','scope'],'delta_'+metric+'_mean',metric))
    csv(pd.concat(directions,ignore_index=True),'five-overlapping-split-directions.csv')
    stable=stability(runs,selections,primary);csv(stable,'selection-stability-pairs.csv')
    # A compact model x information table: within-split seed means, then five-split ranges.
    main_m=seed_metrics.loc[seed_metrics.variant.eq('calibrated')&seed_metrics.period.eq('jan')&seed_metrics.scope.isin(['all','cluster_1_long'])]
    main_c=seed_caps.loc[seed_caps.variant.eq('calibrated')&seed_caps.policy.isin(['global2937','long79'])].copy();main_c['scope']=main_c.policy.map({'global2937':'all','long79':'cluster_1_long'})
    combined=main_m.merge(main_c.drop(columns=['variant','policy','n_models']),on=['split_id','information','family','scope'],validate='one_to_one',suffixes=('','_capacity'))
    csv(combined,'main-model-information-by-split.csv')
    five=[]
    for (info,fam,scope),part in combined.groupby(['information','family','scope']):
        assert len(part)==5;row=dict(information=info,family=fam,scope=scope,overlapping_splits=5)
        for metric in METRICS+['hits','global_long_selected','global_long_hits']:
            arr=part[metric+'_mean'].to_numpy();row[metric+'_median']=float(np.median(arr));row[metric+'_min']=float(arr.min());row[metric+'_max']=float(arr.max())
        five.append(row)
    csv(pd.DataFrame(five),'main-model-information-five-split.csv')
    # Canonical mean(calibrated probability), using the same score everywhere.
    groups={}
    for run in runs:
        if int(run.record['split_id'])==CANONICAL:groups.setdefault((run.record['information'],run.record['family']),[]).append(run)
    assert len(groups)==13;ensembles={};cal_ensembles={};canonical_metrics=[];canonical_caps=[];raw_diag=[];ensemble_manifest=[]
    for (info,fam),members in sorted(groups.items()):
        name=model_name(info,fam);n_expected=1 if fam in DETERMINISTIC else 3;assert len(members)==n_expected
        aligned={}
        for period in ['cal','jan']:
            fs=[]
            for run in members:
                f=frames[CANONICAL][period][KEY+['cluster_id','y','F']].copy();f['calibrated_probability']=run.arrays[period+'_calibrated'];f['raw_logit']=run.arrays[period+'_logit'];fs.append(f)
            en=canonical_ensemble(fs);en=en.merge(frames[CANONICAL][period][KEY+['F']],on=KEY,validate='one_to_one',sort=False)
            aligned[period]=en
        ensembles[name]=aligned['jan'];cal_ensembles[name]=aligned['cal'];f=aligned['jan'];p=f.ensemble_probability.to_numpy()
        for scope,mask in scopes(f):canonical_metrics.append(dict(model=name,information=info,family=fam,n_models=n_expected,scope=scope,**natural(f.loc[mask].reset_index(drop=True),p[mask])))
        for policy in ['global2937','global5','global20','long79']:canonical_caps.append(dict(model=name,information=info,family=fam,n_models=n_expected,policy=policy,**capacity(f,p,policy)))
        raw=f.diagnostic_mean_raw_logit.to_numpy();yy=f.y.to_numpy();raw_order=order(f,raw);main_order=order(f,p)
        for scope,mask,k in [('all',np.ones(len(f),bool),2937),('cluster_1_long',f.cluster_id.eq(1).to_numpy(),79)]:
            sub=f.loc[mask].reset_index(drop=True);z=raw[mask];pp=p[mask];take=order(sub,z)[:k];mtake=order(sub,pp)[:k]
            raw_diag.append(dict(model=name,scope=scope,rule='diagnostic_mean_raw_logit_ranking_only',AP=float(average_precision_score(sub.y,z)),AUC=float(roc_auc_score(sub.y,z)),k=k,hits=int(sub.y.iloc[take].sum()),changed_vs_main_probability_mean=len(set(take)^set(mtake))))
        ensemble_manifest.append(dict(model=name,n_models=n_expected,run_ids=[r.record['run_id'] for r in members],rule='mean(calibrated probability)',proper_and_policy_same_score=True))
    base_frame=next(iter(ensembles.values()))[KEY+['y','cluster_id','F']].copy();private=base_frame.copy();calprivate=next(iter(cal_ensembles.values()))[KEY+['y','cluster_id','F']].copy();probabilities={}
    for name,en in ensembles.items():
        assert en[KEY+['y','cluster_id','F']].equals(base_frame)
        private['probability_'+name]=en.ensemble_probability;private['diagnostic_mean_logit_'+name]=en.diagnostic_mean_raw_logit;probabilities[name]=en.ensemble_probability.to_numpy()
        calprivate['probability_'+name]=cal_ensembles[name].ensemble_probability
    csv(private,'private/canonical-january-ensembles.csv');csv(calprivate,'private/canonical-octcal-ensembles.csv');dump(STAT/'canonical-ensemble-manifest.json',ensemble_manifest)
    csv(pd.DataFrame(canonical_metrics),'canonical-ensemble-metrics.csv');csv(pd.DataFrame(canonical_caps),'canonical-ensemble-capacities.csv');csv(pd.DataFrame(raw_diag),'canonical-raw-mean-logit-diagnostic.csv')
    csv(calibration_bins(ensembles,cal_ensembles),'canonical-calibration-all-bins.csv')
    # Predeclared paired contrasts, preserving all cells rather than selecting a winner.
    reference=model_name('base8','weightedLR');contrasts=[(n,reference,'primary_vs_weightedLR_base8') for n in sorted(ensembles) if n!=reference]
    contrasts += [(model_name('full141',fam),model_name('base8',fam),'information') for fam in MAIN_FAMILIES]
    contrasts += [(model_name(info,fam),model_name(info,'weightedLR'),'model_within_information') for info in INFO for fam in MAIN_FAMILIES if fam!='weightedLR']
    contrasts += [(model_name('full141','nativeCatBoost'),model_name('full141','encodedCatBoost'),'encoding_missing_processing_package_bridge')]
    dump(STAT/'canonical-contrasts.json',[dict(candidate=a,reference=b,kind=k) for a,b,k in contrasts])
    point_receipt=dict(status='POINT_ESTIMATES_AND_FIVE_SPLIT_DIRECTIONS_READY_BOOTSTRAP_PENDING',supervised_runs=155,
        all_variant_metric_rows=len(metrics),all_variant_capacity_rows=len(caps),canonical_ensembles=13,
        point_files=['main-model-information-by-split.csv','main-model-information-five-split.csv','five-overlapping-split-directions.csv','canonical-ensemble-metrics.csv','canonical-ensemble-capacities.csv'],
        source_records_checked=155,score_SHA_checked=155,producer_metric_discrepancies=0,formal_model_adopted=False)
    dump(STAT/'point-estimates-ready.json',point_receipt)
    print('POINT_ESTIMATES_READY: canonical means and 5 overlapping-split directions saved; bootstrap begins next',flush=True)
    print(pd.DataFrame(five)[['information','family','scope','logloss_median','AP_median','hits_median']].to_string(index=False),flush=True)
    observed=[];replicates=[]
    for scope,k,seed in [('all',2937,2026111201),('long',79,2026111202)]:
        print('Bootstrap begin',scope,'2000 paired customer resamples; fixed score',flush=True)
        ob,reps=paired_customer_bootstrap(base_frame,probabilities,scope,k,replicates=2000,seed=seed)
        observed.append(ob);replicates.append(reps);print('Bootstrap done',scope,flush=True)
    observed=pd.concat(observed,ignore_index=True);replicates=pd.concat(replicates,ignore_index=True)
    intervals=paired_intervals(observed,replicates,contrasts,PAIR_METRICS+['global_long_selected','global_long_hits'])
    intervals=intervals.loc[~(intervals.scope.eq('long')&intervals.metric.str.startswith('global_long'))].reset_index(drop=True)
    csv(observed,'canonical-bootstrap-observed.csv');csv(replicates,'canonical-bootstrap-replicates.csv.gz');csv(intervals,'canonical-paired-bootstrap-intervals.csv')
    # No formal model selection. First complete fact summary precedes plots/read-back.
    summary=dict(status='METRICS_READY_PLOTS_READBACK_PENDING',supervised_models=155,all_variant_metric_rows=len(metrics),all_variant_capacity_rows=len(caps),producer_discrepancies=0,
        shared_and_score_SHA_checked=True,canonical_ensembles=13,bootstrap_replicates_per_scope=2000,bootstrap_rep_rows=len(replicates),
        primary_ensemble_rule='mean(calibrated probability)',calibration_bins=100,split_interpretation='five overlapping training perturbations, same seen January; not independent periods',
        formal_model_adopted=False,april_rows_parsed=0,elapsed_seconds=time.perf_counter()-start)
    summary['source_sha256']=binding['source_sha256'];summary['runner_sha256']=sha(Path(__file__));summary['output_sha256']={str(p.relative_to(STAT)):sha(p) for p in STAT.rglob('*') if p.is_file() and p.name!='statistics-verification.json'}
    dump(STAT/'statistics-verification.json',summary)
    print('FIRST COMPLETE SUMMARY',json.dumps({k:v for k,v in summary.items() if k not in ['output_sha256','source_sha256']},indent=2),flush=True)
    print(pd.DataFrame(five).loc[lambda x:x.scope.eq('all')][['information','family','logloss_median','AP_median','hits_median','global_long_selected_median']].to_string(index=False),flush=True)

if __name__=='__main__':
    with threadpool_limits(limits=2):main()
