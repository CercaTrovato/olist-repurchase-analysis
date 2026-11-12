"""Exact schema adapter. Import/bind never reads model records or scores.

Study-result loading is an explicit second phase, gated by root authorization.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib,importlib.util,json,sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
STAT=ROOT/'statistics'
KEY=['customer_unique_id','snapshot_date']
SPLITS=[20261111,20261112,20261113,20261114,20261115]
SEEDS=[2026,2027,2028]
DETERMINISTIC={'weightedLR','unweightedLR'}
MAIN_FAMILIES=['weightedLR','unweightedLR','encodedCatBoost','mean','column-gate','AE']
ALL_FAMILIES=MAIN_FAMILIES+['nativeCatBoost']

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def load_harness():
    spec=importlib.util.spec_from_file_location('common_comparison_producer_harness',ROOT/'eval_harness.py')
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module
def expected_cells():
    cells=set()
    for split_id in SPLITS:
        for information in ['base8','full141']:
            for family in MAIN_FAMILIES:
                for seed in ([None] if family in DETERMINISTIC else SEEDS):cells.add((split_id,information,family,seed))
        for seed in SEEDS:cells.add((split_id,'full141','nativeCatBoost',seed))
    assert len(cells)==155
    return cells
def cell_key(record):
    return (int(record['split_id']),str(record['information']),str(record['family']),None if record['seed'] is None else int(record['seed']))
def normalized_model_id(record):
    split_id,information,family,seed=cell_key(record)
    return f'{split_id}__{information}__{family}__'+('deterministic' if seed is None else str(seed))

def freeze_binding(preflight_receipt:dict|None=None):
    """Use only shared inputs/source. No classical/neural record enumeration."""
    h=load_harness();m=h.manifest()
    if m['split_ids']!=SPLITS or m['model_seeds']!=SEEDS:raise ValueError('Producer split/seed contract changed')
    if set(m['information'])!={'base8','full141'} or set(m['families'])!=set(ALL_FAMILIES):raise ValueError('Family/information contract changed')
    binding=dict(status='BOUND_WAITING_ROOT_RUN_STATS',schema_version=1,root=str(ROOT),expected_supervised_runs=155,
        expected_AE_pretrains=30,split_ids=SPLITS,seeds=SEEDS,main_families=MAIN_FAMILIES,extra_family='nativeCatBoost',
        deterministic_families=sorted(DETERMINISTIC),main_ensemble='mean(jan_calibrated)',canonical_split=20261111,
        record_globs=['classical/*-record.json','neural/*-record.json'],
        source_sha256={n:sha(ROOT/n) for n in ['task_plan.md','protocol-clarification.md','eval_harness.py','prepare_shared.py','shared/data-manifest.json']},
        statistics_source_sha256={p.name:sha(p) for p in [Path(__file__),STAT/'statistics_core.py',STAT/'audit_shared_and_bind.py',STAT/'statistics-plan.md',STAT/'schema-contract.md']},
        NPZ_required=['fit_logit','cal_logit','jan_logit','fit_raw','cal_raw','jan_raw','fit_calibrated','cal_calibrated','jan_calibrated'],
        weightedLR_additional=['fit_prior','cal_prior','jan_prior'],scope_mapping={'all':'all','group0':'cluster_0','group1':'cluster_1_long','group2':'cluster_2','F1':'single_order_F1'},
        ready_gate='Require statistics/RUN_STATS.authorization.json written only after root explicitly announces complete matrix',
        study_records_read=False,study_scores_read=False,preflight=preflight_receipt)
    dump(STAT/'adapter-binding.json',binding)
    return binding

@dataclass
class BoundRun:
    record_path:Path
    record:dict
    arrays:dict[str,np.ndarray]

    @property
    def identity(self):
        return {k:self.record[k] for k in ['run_id','family','information','split_id','seed']}

def load_complete_matrix():
    """Never call before explicit root RUN_STATS. No partial-matrix analysis."""
    auth_path=STAT/'RUN_STATS.authorization.json'
    if not auth_path.is_file():raise RuntimeError('WAIT_ROOT_RUN_STATS: no study results read')
    auth=json.loads(auth_path.read_text(encoding='utf-8'))
    if auth.get('authorized_action')!='RUN_STATS_COMPLETE_155_MATRIX':raise RuntimeError('Invalid statistics authorization scope')
    binding=json.loads((STAT/'adapter-binding.json').read_text(encoding='utf-8'))
    for name,digest in binding['source_sha256'].items():
        if sha(ROOT/name)!=digest:raise RuntimeError(f'Producer source changed after binding: {name}')
    # First verify record cardinality and identities; do not read any score NPZ yet.
    paths=sorted([*(ROOT/'classical').glob('*-record.json'),*(ROOT/'neural').glob('*-record.json')])
    if len(paths)!=155:raise RuntimeError(f'Incomplete matrix: {len(paths)}/155 records; no score NPZ read')
    records=[(p,json.loads(p.read_text(encoding='utf-8'))) for p in paths]
    cells=[cell_key(r) for _,r in records]
    if len(set(cells))!=155 or set(cells)!=expected_cells():raise ValueError('Missing/duplicate/unplanned model cells')
    ids=[r['run_id'] for _,r in records]
    if len(set(ids))!=155:raise ValueError('Duplicate producer run_id')
    h=load_harness();manifest=h.manifest();manifest_sha=sha(ROOT/'shared/data-manifest.json')
    frames={s:h.load_frames(s) for s in SPLITS}
    cohort=frames[SPLITS[0]]['jan'][KEY+['y','cluster_id','F']].reset_index(drop=True)
    if (len(cohort),int(cohort.y.sum()),int(cohort.cluster_id.eq(1).sum()),int(cohort.loc[cohort.cluster_id.eq(1),'y'].sum()))!=(29368,230,12330,90):raise ValueError('Authoritative January support changed')
    for s in SPLITS:
        if not cohort.equals(frames[s]['jan'][KEY+['y','cluster_id','F']].reset_index(drop=True)):raise ValueError('Jan row order changed across split')
    loaded=[]
    for path,record in records:
        for key in ['metrics','capacities','calibration','metadata','score_file','score_sha256','shared_manifest_sha256','eval_harness_sha256']:
            if key not in record:raise ValueError(f'Missing producer record key {key}: {path.name}')
        if record['shared_manifest_sha256']!=manifest_sha or record['eval_harness_sha256']!=binding['source_sha256']['eval_harness.py']:raise ValueError('Score producer manifest/source differs from binding')
        score_path=(ROOT/record['score_file']).resolve()
        if not score_path.is_relative_to(ROOT.resolve()):raise ValueError('Score path escapes comparison root')
        if sha(score_path)!=record['score_sha256']:raise ValueError('Producer score SHA mismatch')
        with np.load(score_path,allow_pickle=False) as archive:arrays={k:np.asarray(archive[k],dtype=np.float64).copy() for k in archive.files}
        required=set(binding['NPZ_required'])| (set(binding['weightedLR_additional']) if record['family']=='weightedLR' else set())
        if not required<=set(arrays):raise ValueError('Score NPZ lacks planned fields')
        split=int(record['split_id'])
        for period in ['fit','cal','jan']:
            n=len(frames[split][period])
            for suffix in ['logit','raw','calibrated']+(['prior'] if record['family']=='weightedLR' else []):
                a=arrays[period+'_'+suffix]
                if a.shape!=(n,) or not np.isfinite(a).all():raise ValueError('Malformed/nonfinite producer score array')
                if suffix!='logit' and ((a<0)|(a>1)).any():raise ValueError('Invalid producer probability')
        loaded.append(BoundRun(path,record,arrays))
    return loaded,frames,binding

def score_frame(run:BoundRun,frames:dict,variant='calibrated'):
    f=frames[int(run.record['split_id'])]['jan'][KEY+['cluster_id','y','F']].copy()
    f['raw_logit']=run.arrays['jan_logit']
    f['calibrated_probability']=run.arrays['jan_calibrated']
    f['probability']=run.arrays['jan_'+variant]
    return f
