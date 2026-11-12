"""Driver for root-frozen shared matrices. No independent split or encoding."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import argparse,gc,json,time
import numpy as np
import pandas as pd
from classical_engine import train_wlr,train_cb,native_parts,verify_model,sha,dump,LR_PARAMS,CB_PARAMS

OUT=Path(__file__).resolve().parent;ROOT=OUT.parent;SHARED=ROOT/'shared';PRIVATE=OUT/'private'
sys.path.insert(0,str(ROOT))
import eval_harness as shared
SEEDS=[2026,2027,2028];SPLITS=list(range(20261111,20261116));INFO=['base8','full141']
def specifications():
    specs=[]
    for split in SPLITS:
        for information in INFO:
            for family in ['weightedLR','unweightedLR']:specs.append(dict(split=split,information=information,family=family,seed=None))
            for seed in SEEDS:specs.append(dict(split=split,information=information,family='encodedCatBoost',seed=seed))
        for seed in SEEDS:specs.append(dict(split=split,information='full141',family='nativeCatBoost',seed=seed))
    assert len(specs)==65;return specs
def name(spec):return f'{spec["family"]}-{spec["information"]}-split{spec["split"]}'+(f'-seed{spec["seed"]}' if spec['seed'] is not None else '')
def read_manifest():
    m=shared.manifest();assert m['status']=='frozen_shared_data_ready';assert m['split_ids']==SPLITS and m['model_seeds']==SEEDS
    for p,h in m['sources'].items():assert sha(p)==h,p
    for tag,h in m['raw_data_sha256'].items():assert sha(SHARED/'private'/f'{tag}-raw.csv')==h
    return m
def native_and_source(m,split):
    """Read only root loader rows; native bridge does only the authorized fit-median."""
    sd=SHARED/'private'/f'split-{split}';record=m['splits'][str(split)]
    for f,h in record['files'].items():assert sha(sd/f)==h,(split,f)
    raw=shared.load_raw(split);fields=raw['fields'];assert fields==m['raw_fields'] and raw['categorical_fields']==m['categorical_fields']
    native={p:raw[p][fields].copy() for p in ['fit','cal','jan']}
    native,pre=native_parts(native,m['categorical_fields']);dump(pre,PRIVATE/f'native-preprocess-split{split}.json')
    source=dict(shared_manifest_sha256=sha(SHARED/'data-manifest.json'),shared_split=split,split_file_sha256=record['files'],raw_sha256=m['raw_data_sha256'],fit_key_sha256=record['fit_key_sha256'],view_dimensions=record['dims'],raw_fields=141,base_encoded_columns=int(record['base8_encoded']),matrix_columns=int(record['dimension']),driver_sha256=sha(Path(__file__)),eval_harness_sha256=sha(ROOT/'eval_harness.py'))
    del raw;gc.collect();return native,pre,source

def register(spec,directory,meta,parts):
    modelid=name(spec);error=verify_model(parts,directory);logits=np.load(directory/'logits.npz')
    shared.write_run(OUT,modelid,spec['family'],spec['information'],spec['split'],spec['seed'],logits['fit'],logits['cal'],logits['jan'],metadata=meta|dict(classical_model_directory=directory.relative_to(ROOT).as_posix()))
    return spec|dict(model_id=modelid,private_directory=directory.relative_to(OUT).as_posix(),logits_path=(directory/'logits.npz').relative_to(OUT).as_posix(),metadata_path=(directory/'metadata.json').relative_to(OUT).as_posix(),training_seconds=meta['training_seconds'],reloaded_logit_max_errors=error,metadata_sha256=sha(directory/'metadata.json'),root_record_path=modelid+'-record.json')

def run(pilot=False):
    m=read_manifest();specs=specifications();dump(specs,OUT/'model-specifications.json')
    freeze={'plan_sha256':sha(OUT/'plan.md'),'root_plan_sha256':sha(ROOT/'task_plan.md'),'engine_sha256':sha(OUT/'classical_engine.py'),'driver_sha256':sha(Path(__file__)),'eval_harness_sha256':sha(ROOT/'eval_harness.py'),'shared_manifest_sha256':sha(SHARED/'data-manifest.json'),'specifications_sha256':sha(OUT/'model-specifications.json'),'LR_parameters':LR_PARAMS,'ULR_change':{'class_weight':None},'CB_parameters':CB_PARAMS,'total_models':65}
    frozenpath=OUT/'frozen-config.json'
    if frozenpath.exists():assert json.loads(frozenpath.read_text())==freeze,'Frozen source/config changed; do not silently resume'
    else:dump(freeze,frozenpath)
    pilotnames={name(s) for s in specs if s['split']==20261111 and ((s['family']=='weightedLR') or (s['family'] in ['encodedCatBoost','nativeCatBoost'] and s['information']=='full141' and s['seed']==2026))}
    chosen=[s for s in specs if not pilot or name(s) in pilotnames];assert len(chosen)==(4 if pilot else 65)
    indexpath=OUT/'models-index.json';index=json.loads(indexpath.read_text()) if indexpath.exists() else [];known={r['model_id']:r for r in index};start=time.perf_counter();failure=[]
    for split in sorted({s['split'] for s in chosen}):
        native,pre,source=native_and_source(m,split)
        for information in INFO:
            active=[s for s in chosen if s['split']==split and s['information']==information and s['family']!='nativeCatBoost']
            if not active:continue
            bundle=shared.load_split(split,information,dense=True,dtype=np.float64);parts={p:bundle['X_'+p] for p in ['fit','cal','jan']};y=bundle['y_fit'];assert bundle['dims']==source['view_dimensions']
            for spec in active:
                modelid=name(spec);directory=PRIVATE/modelid;ss=source|dict(information=information,family=spec['family'],seed=spec['seed'])
                if modelid in known:
                    saved=json.loads((directory/'metadata.json').read_text());assert saved['source']==ss;print('REUSE',modelid,flush=True);continue
                print('FIT',modelid,'columns',parts['fit'].shape[1],flush=True)
                if spec['family'] in ['weightedLR','unweightedLR']:meta=train_wlr(parts,y,directory,ss,weighted=spec['family']=='weightedLR')
                else:meta=train_cb(parts,y,directory,ss,spec['seed'])
                entry=register(spec,directory,meta,parts)
                index.append(entry);known[modelid]=entry;dump(index,indexpath);print('DONE',modelid,meta['training_seconds'],'reload',entry['reloaded_logit_max_errors'],flush=True)
            del parts,bundle;gc.collect()
        for spec in [s for s in chosen if s['split']==split and s['family']=='nativeCatBoost']:
            modelid=name(spec);directory=PRIVATE/modelid;ss=source|dict(information='full141',family=spec['family'],seed=spec['seed'])
            if modelid in known:assert json.loads((directory/'metadata.json').read_text())['source']==ss;print('REUSE',modelid,flush=True);continue
            native_y=shared.load_frames(split)['fit'].y.to_numpy(int)
            meta=train_cb(native,native_y,directory,ss,spec['seed'],native=True,categorical=m['categorical_fields'],native_preprocess=pre)
            entry=register(spec,directory,meta,native);index.append(entry);known[modelid]=entry;dump(index,indexpath);print('DONE',modelid,meta['training_seconds'],'reload',entry['reloaded_logit_max_errors'],flush=True)
        del native;gc.collect()
    assert all(name(s) in known for s in chosen);receipt=dict(mode='pilot' if pilot else 'full',completed_models=len(index),executed_seconds=time.perf_counter()-start,training_seconds=sum(r['training_seconds'] for r in index),calibration_only_via_root_harness=True,root_eval_harness_pending=False,April_rows_read=0)
    if pilot:
        times={r['family']+'-'+r['information']:r['training_seconds'] for r in index if r['model_id'] in pilotnames};receipt['pilot_training_seconds']=times;receipt['rough_full_training_seconds']=10*max(times['weightedLR-base8'],times['weightedLR-full141'])*2+30*times['encodedCatBoost-full141']+15*times['nativeCatBoost-full141'];receipt['estimate_note']='Extrapolated using slower pilot LR for WLR/ULR and full CB for both information slots; includes all65 training, excludes replay/evaluation/IO; no Jan result used'
    else:assert len(index)==65
    dump(receipt,OUT/('pilot-timing.json' if pilot else 'training-verification.json'));assert sha(SHARED/'data-manifest.json')==freeze['shared_manifest_sha256'];print('FINISHED',receipt,flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--pilot',action='store_true');args=ap.parse_args();run(args.pilot)
