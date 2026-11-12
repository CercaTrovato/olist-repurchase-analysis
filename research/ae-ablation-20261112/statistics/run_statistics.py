"""Fixed 200-record follow-up statistics; no fitting or source mutation."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import argparse,hashlib,importlib.util,itertools,json,time
import numpy as np
import pandas as pd
from scipy.special import expit
from threadpoolctl import threadpool_limits

OUT=Path(__file__).resolve().parent;LAB=OUT.parent;ROOT=LAB.parent
sys.path.insert(0,str(ROOT/'statistics'))
from statistics_core import FixedScoreEvaluator,canonical_ensemble,paired_customer_bootstrap,paired_intervals,seed_aggregate,split_direction_summary,KEY
spec=importlib.util.spec_from_file_location('legacy_stat_runner',ROOT/'statistics/run_statistics.py');legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
spec=importlib.util.spec_from_file_location('legacy_harness',ROOT/'eval_harness.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
SPLITS=list(range(20261111,20261116));SEEDS=[2026,2027,2028]
NEW=['mean70','mean3040','AE-shuffled']+['AE-drop-'+x for x in ['behavior','geography','products','commerce','service','seller-context']]
REFS=['AE-full','mean50','WLR-base8','encodedCB-full','nativeCB-full'];SYSTEMS=REFS+NEW
METRICS=['logloss','brier','AP','AUC','hits','precision','recall']
CONTRASTS=[(c,r,'new_case_vs_'+r) for c in NEW for r in ['AE-full','WLR-base8']]+[(c,r,'retained_reference_vs_'+r) for c in ['mean50','encodedCB-full','nativeCB-full'] for r in ['AE-full','WLR-base8']]+[('AE-full','WLR-base8','fixed_candidate_vs_target_reference')]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(name,value):h.dump(OUT/name,value)
def csv(df,name):df.to_csv(OUT/name,index=False,lineterminator='\n')
def frozen_paths():return [OUT/'plan.md',Path(__file__),OUT/'verify_statistics.py',OUT/'render_statistics.py',LAB/'task_plan.md',LAB/'candidate-freeze.json',ROOT/'statistics/statistics_core.py',ROOT/'statistics/run_statistics.py',ROOT/'statistics/producer_adapter.py',ROOT/'eval_harness.py',ROOT/'shared/data-manifest.json']
def freeze():
    assert not (OUT/'source-freeze.json').exists()
    dump('source-freeze.json',dict(status='statistical_plan_and_code_frozen_before_complete_matrix_execution',source_sha256={str(p):sha(p) for p in frozen_paths()},systems=SYSTEMS,new_cases=NEW,contrasts=CONTRASTS,expected_records=200,bootstrap_replicates_per_scope=2000))
def frozen():
    f=json.loads((OUT/'source-freeze.json').read_text())
    for p,digest in f['source_sha256'].items():assert sha(p)==digest,('source changed',p)
    return f
def expected():
    candidate=json.loads((LAB/'candidate-freeze.json').read_text());items=[]
    mapping={'AE':'AE-full','mean':'mean50','weightedLR':'WLR-base8','encodedCatBoost':'encodedCB-full','nativeCatBoost':'nativeCB-full'}
    for r in candidate['old_reference_records']:
        system=mapping[r['family']];items.append(dict(model=system,record_path=str(ROOT/r['record']),expected_record_sha256=r['record_sha256'],expected_score_sha256=r['score_sha256'],split_id=int(r['split_id']),seed=r['seed'],source='reused_reference'))
    assert len(items)==65
    for case in NEW:
        directory='budget' if case in NEW[:3] else 'feature-groups'
        for split in SPLITS:
            for seed in SEEDS:items.append(dict(model=case,record_path=str(LAB/directory/f'split{split}__full141__{case}__s{seed}-record.json'),split_id=split,seed=seed,source='new_followup'))
    assert len(items)==200 and len({(i['model'],i['split_id'],i['seed']) for i in items})==200
    return items
def bind():
    frozen();items=expected();missing=[i['record_path'] for i in items if not Path(i['record_path']).exists()]
    assert not missing,('Incomplete matrix; no statistics run',len(missing),missing[:3])
    assert not (OUT/'input-binding.json').exists()
    for i in items:
        p=Path(i['record_path']);r=json.loads(p.read_text());score=ROOT/r['score_file'];record_sha=sha(p);score_sha=sha(score)
        assert score_sha==r['score_sha256']
        if i['source']=='reused_reference':assert record_sha==i['expected_record_sha256'] and score_sha==i['expected_score_sha256']
        else:
            metadata=r['metadata'];assert metadata['followup_plan_sha256']==sha(LAB/'task_plan.md');assert metadata['candidate_freeze_sha256']==sha(LAB/'candidate-freeze.json')
        assert int(r['split_id'])==i['split_id'] and r['seed']==i['seed']
        i.update(record_sha256=record_sha,score_path=str(score),score_sha256=score_sha)
    dump('input-binding.json',dict(status='complete_200_records_bound_waiting_parent_RUN_STATS',items=items,source_freeze_sha256=sha(OUT/'source-freeze.json')))
def load():
    frozen();binding=json.loads((OUT/'input-binding.json').read_text());items=binding['items'];assert len(items)==200
    result=[]
    for i in items:
        assert sha(i['record_path'])==i['record_sha256'];assert sha(i['score_path'])==i['score_sha256']
        r=json.loads(Path(i['record_path']).read_text());a=dict(np.load(i['score_path']));result.append((i,r,a))
    return result
def masks(frame):return [('all',np.ones(len(frame),bool)),('long',frame.cluster_id.eq(1).to_numpy())]
def selection(frame,p,scope):
    mask=dict(masks(frame))[scope];ev=FixedScoreEvaluator(frame.loc[mask].reset_index(drop=True),p[mask]);k=2937 if scope=='all' else 79
    return ev,ev.selected_key_set(k),k
def measure(frame,p,scope):
    ev,keys,k=selection(frame,p,scope);return ev.empirical_metrics()|ev.topk(k)
def main():
    began=time.perf_counter();runs=load();(OUT/'private').mkdir(exist_ok=True);frames={s:h.load_frames(s) for s in SPLITS}
    rows=[];caps=[];calibration=[];errors=[];groups={};runselect={};run_primary=[]
    for i,r,a in runs:
        tag={k:i[k] for k in ['model','split_id','seed','source']};tag['run_id']=r['run_id'];ff=frames[i['split_id']]
        source_metrics={(x['period'],x['variant'],x['scope']):x for x in r['metrics']};source_caps={(x['variant'],x['policy']):x for x in r['capacities']}
        variants=['raw','calibrated']+(['prior'] if i['model']=='WLR-base8' else [])
        for period in ['cal','jan']:
            frame=ff[period]
            for variant in variants:
                p=a[period+'_'+variant];assert len(p)==len(frame) and np.isfinite(p).all()
                for scope,mask in legacy.scopes(frame):
                    computed=legacy.natural(frame.loc[mask].reset_index(drop=True),p[mask]);row=tag|dict(period=period,variant=variant,scope=scope)|computed;rows.append(row)
                    producer_scope={'all':'all','cluster_0':'group0','cluster_1_long':'group1','cluster_2':'group2','single_order_F1':'F1'}[scope];original=source_metrics[period,variant,producer_scope]
                    for metric in ['logloss','brier','AP','AUC','accuracy','F1']:
                        if metric in ['AP','AUC'] and not computed[metric+'_defined']:continue
                        if not legacy.finite_compare(computed[metric],original[metric]):errors.append(dict(run_id=r['run_id'],kind='metric',period=period,variant=variant,scope=scope,metric=metric,recomputed=computed[metric],producer=original[metric]))
                if period=='jan':
                    for policy in ['global2937','global5','global20','long79']:
                        computed=legacy.capacity(frame,p,policy);caps.append(tag|dict(variant=variant,policy=policy)|computed);original=source_caps[variant,policy]
                        for metric in ['hits','precision','recall']+[f'group{g}_{q}' for g in [0,1,2] for q in ['selected','hits']]:
                            if not legacy.finite_compare(computed[metric],original[metric]):errors.append(dict(run_id=r['run_id'],kind='capacity',variant=variant,policy=policy,metric=metric,recomputed=computed[metric],producer=original[metric]))
        c=r['calibration'];z=a['cal_logit'];y=ff['cal'].y.to_numpy();slope=c['a'];intercept=c['b'];e=expit(slope*z+intercept)-y;grad=np.array([e@z+slope/1e6,e.sum()]);proj=grad.copy();proj[0]=slope-max(1e-6,slope-grad[0]);residual=float(np.abs(proj).max())
        p_error=max(float(np.abs(expit(slope*a[p+'_logit']+intercept)-a[p+'_calibrated']).max()) for p in ['fit','cal','jan'])
        assert p_error<=1e-12 and abs(residual-c['projected_gradient_inf'])<1e-8
        calibration.append(tag|dict(success=c['success'],slope=slope,intercept=intercept,active_lower_bound=c['active_lower_bound'],projected_gradient_inf=residual,actual_meets_1e_10=residual<=1e-10,probability_replay_max_abs=p_error,message=c['message']))
        groups.setdefault((i['split_id'],i['model']),[]).append((i,r,a))
        for scope in ['all','long']:
            ev,keys,k=selection(ff['jan'],a['jan_calibrated'],scope);runselect[r['run_id'],scope]=keys
            run_primary.append(tag|dict(scope=scope)|ev.empirical_metrics()|ev.topk(k))
    csv(pd.DataFrame(errors),'producer-differences.csv');assert not errors,'Producer discrepancy preserved; do not change score'
    metrics=pd.DataFrame(rows);capacity=pd.DataFrame(caps);primary=pd.DataFrame(run_primary)
    assert len(metrics)==4050 and len(capacity)==1620 and len(primary)==400
    csv(metrics,'all-run-metrics.csv');csv(capacity,'all-run-capacities.csv');csv(primary,'all-run-primary.csv');csv(pd.DataFrame(calibration),'calibration-optimization-audit.csv')
    csv(seed_aggregate(primary,['split_id','model','scope'],METRICS),'within-split-seed-summary.csv')
    ensemble_points=[];ensemble_caps=[];ensembles={};ensemble_selection={};en_manifest=[]
    for split in SPLITS:
        arrays={}
        for model in SYSTEMS:
            members=groups[split,model];assert len(members)==(1 if model=='WLR-base8' else 3)
            aligned={}
            for part in ['cal','jan']:
                fs=[]
                for i,r,a in members:
                    frame=frames[split][part][KEY+['y','cluster_id']].copy();frame['calibrated_probability']=a[part+'_calibrated'];fs.append(frame)
                en=canonical_ensemble(fs);aligned[part]=en
                arrays[part+'__'+model]=en.ensemble_probability.to_numpy()
            en=aligned['jan'];frame=en[KEY+['y','cluster_id']];p=en.ensemble_probability.to_numpy();ensembles[split,model]=(frame,p)
            if model==SYSTEMS[0]:base=frame.copy();calbase=aligned['cal'][KEY+['y','cluster_id']].copy()
            else:assert frame.equals(base) and aligned['cal'][KEY+['y','cluster_id']].equals(calbase)
            for scope in ['all','long']:
                ensemble_points.append(dict(split_id=split,model=model,scope=scope,n_models=len(members),**measure(frame,p,scope)));ensemble_selection[split,model,scope]=selection(frame,p,scope)[1]
            for policy in ['global2937','global5','global20','long79']:ensemble_caps.append(dict(split_id=split,model=model,policy=policy,**legacy.capacity(frame,p,policy)))
            en_manifest.append(dict(split_id=split,model=model,run_ids=[r['run_id'] for i,r,a in members],rule='same-key mean(calibrated probability)',n_models=len(members)))
        np.savez_compressed(OUT/'private'/f'split{split}-ensemble-probabilities.npz',**arrays)
        base.to_csv(OUT/'private'/f'split{split}-jan-cohort.csv',index=False);calbase.to_csv(OUT/'private'/f'split{split}-cal-cohort.csv',index=False)
    points=pd.DataFrame(ensemble_points);csv(points,'ensemble-primary-by-split.csv');csv(pd.DataFrame(ensemble_caps),'ensemble-capacities-by-split.csv');dump('ensemble-manifest.json',en_manifest)
    point_index=points.set_index(['split_id','model','scope']);differences=[]
    for split in SPLITS:
        for candidate,reference,kind in CONTRASTS:
            for scope in ['all','long']:
                a=point_index.loc[split,candidate,scope];b=point_index.loc[split,reference,scope]
                differences.append(dict(split_id=split,candidate=candidate,reference=reference,contrast=kind,scope=scope,**{'delta_'+m:float(a[m]-b[m]) for m in METRICS}))
    differences=pd.DataFrame(differences);csv(differences,'ensemble-paired-differences-by-split.csv')
    directions=pd.concat([split_direction_summary(differences,['candidate','reference','contrast','scope'],'delta_'+m,m) for m in METRICS],ignore_index=True);csv(directions,'five-overlapping-split-directions.csv')
    stability=[]
    def stab(kind,model,scope,a,b,sa,sb):return dict(kind=kind,model=model,scope=scope,label_a=str(a),label_b=str(b),jaccard=len(sa&sb)/len(sa|sb),changed=len(sa^sb))
    for model in SYSTEMS:
        for scope in ['all','long']:
            for a,b in itertools.combinations(SPLITS,2):stability.append(stab('ensemble_across_overlapping_splits',model,scope,a,b,ensemble_selection[a,model,scope],ensemble_selection[b,model,scope]))
            for split in SPLITS:
                members=groups[split,model]
                for a,b in itertools.combinations(members,2):
                    ia,ra,aa=a;ib,rb,ab=b;stability.append(stab('single_run_across_seeds',model,scope,str(split)+'_'+str(ia['seed']),str(split)+'_'+str(ib['seed']),runselect[ra['run_id'],scope],runselect[rb['run_id'],scope]))
                if model in NEW:stability.append(stab('new_case_versus_AE_full_same_split',model,scope,str(split)+'_'+model,str(split)+'_AE-full',ensemble_selection[split,model,scope],ensemble_selection[split,'AE-full',scope]))
    csv(pd.DataFrame(stability),'selection-stability.csv')
    dump('point-estimates-ready.json',dict(status='complete_matrix_points_ready_bootstrap_pending',records=200,systems=14,ensemble_cells=70,producer_discrepancies=0))
    print('POINTS READY 200 records /70 ensemble cells; bootstrap starts',flush=True)
    frame=ensembles[20261111,SYSTEMS[0]][0];probabilities={m:ensembles[20261111,m][1] for m in SYSTEMS};observed=[];replicates=[]
    for scope,k,seed in [('all',2937,2026111201),('long',79,2026111202)]:
        print('BOOTSTRAP',scope,'2000',flush=True);ob,rep=paired_customer_bootstrap(frame,probabilities,scope,k,replicates=2000,seed=seed);observed.append(ob);replicates.append(rep);print('BOOTSTRAP DONE',scope,flush=True)
    observed=pd.concat(observed,ignore_index=True);replicates=pd.concat(replicates,ignore_index=True);intervals=paired_intervals(observed,replicates,CONTRASTS,METRICS)
    assert len(replicates)==56000 and len(intervals)==350
    csv(observed,'canonical-bootstrap-observed.csv');csv(replicates,'private/canonical-bootstrap-replicates.csv.gz');csv(intervals,'canonical-paired-bootstrap-intervals.csv')
    dump('execution.json',dict(status='statistics_complete_render_and_readback_pending',records=200,new_records=135,reused_reference_records=65,systems=14,ensemble_cells=70,source_metric_discrepancies=0,bootstrap_replicates_per_scope=2000,bootstrap_rows=len(replicates),interval_rows=len(intervals),elapsed_seconds=time.perf_counter()-began,source_freeze_sha256=sha(OUT/'source-freeze.json'),input_binding_sha256=sha(OUT/'input-binding.json'),formal_adoption=False,temporal_models_included=0,April_rows_read=0))
    print('STATISTICS COMPLETE',time.perf_counter()-began,flush=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['freeze','bind','run']);parser.add_argument('--authorization');args=parser.parse_args()
    with threadpool_limits(limits=2):
        if args.mode=='run':assert args.authorization=='RUN_STATS';main()
        else:globals()[args.mode]()
