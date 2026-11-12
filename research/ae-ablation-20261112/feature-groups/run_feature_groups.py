"""Frozen leave-one-view-zero AE adapter. Parent data and implementations are read only."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import argparse, gc, hashlib, json, time, traceback
import numpy as np
import pandas as pd
import torch
from threadpoolctl import threadpool_limits
OUT=Path(__file__).resolve().parent
LAB=OUT.parent
ROOT=LAB.parent
PRIVATE=OUT/'private'
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'neural'))
import eval_harness as harness
import neural_models as nm
SPLITS=[20261111,20261112,20261113,20261114,20261115]
SEEDS=[2026,2027,2028]
PARTS=['fit','cal','jan']

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ah(x): return hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()
def dump(p,x): harness.dump(p,x)
def sources():
    paths=[Path(__file__),OUT/'verify_feature_groups.py',OUT/'plot_training_diagnostics.py',OUT/'plan.md',LAB/'task_plan.md',ROOT/'eval_harness.py',ROOT/'neural/neural_models.py',ROOT/'shared/data-manifest.json']
    return {str(p):sha(p) for p in paths}
def slug(view): return view.replace('_','-')
def run_id(split,view,seed): return f'split{split}__full141__AE-drop-{slug(view)}__s{seed}'

def load(split):
    d=harness.load_split(split,'full141',dense=True,dtype=np.float32)
    for part in PARTS:
        x=d['X_'+part]
        assert x.dtype==np.float32 and np.isfinite(x).all()
        x.setflags(write=False)
    return d

def masked(d,view):
    names=harness.manifest()['view_order'];index=names.index(view)
    offsets=np.cumsum([0]+d['dims']);start,end=map(int,offsets[index:index+2])
    keep=np.ones(sum(d['dims']),dtype=bool);keep[start:end]=False
    mask=keep.astype(np.float32)
    audit={'view':view,'view_index':index,'start_inclusive':start,'end_exclusive':end,'dims':d['dims'],
           'column_mask_sha256':ah(mask),'zeroed_columns':end-start,'kept_columns':int(keep.sum()),'parts':{}}
    tensors={}
    for part in PARTS:
        full=d['X_'+part];x=full.copy();x[:,start:end]=0
        assert np.array_equal(x[:,keep],full[:,keep])
        assert np.count_nonzero(x[:,start:end])==0 and x.shape==full.shape
        audit['parts'][part]={'shape':list(x.shape),'dtype':str(x.dtype),'full_sha256':ah(full),'masked_sha256':ah(x),
          'full_nnz':int(np.count_nonzero(full)),'masked_nnz':int(np.count_nonzero(x)),
          'removed_original_nnz':int(np.count_nonzero(full[:,start:end])),
          'other_columns_unchanged':True,'zero_segment_nnz':0}
        assert audit['parts'][part]['full_nnz']-audit['parts'][part]['masked_nnz']==audit['parts'][part]['removed_original_nnz']
        tensors[part]=torch.from_numpy(x)
    tensors['yfit']=torch.tensor(d['y_fit'],dtype=torch.float32)
    return tensors,audit

def prepare():
    PRIVATE.mkdir(exist_ok=True)
    audits=[];baseline=[]
    for split in SPLITS:
        d=load(split)
        desc=harness.manifest()['splits'][str(split)]
        for fn,expected in desc['files'].items():
            assert sha(ROOT/f'shared/private/split-{split}'/fn)==expected,(split,fn)
        for view in harness.manifest()['view_order']:
            tensors,audit=masked(d,view);audits.append({'split':split,**audit});del tensors
        for seed in SEEDS:
            p=ROOT/'neural'/f'split{split}__full141__AE__s{seed}-record.json'
            record=json.loads(p.read_text(encoding='utf-8'))
            assert sha(ROOT/record['score_file'])==record['score_sha256']
            baseline.append({'split':split,'seed':seed,'record':str(p),'sha256':sha(p),'score_sha256':record['score_sha256']})
        del d;gc.collect()
    dump(OUT/'input-mask-audit.json',audits)
    dump(OUT/'source-freeze.json',{'status':'frozen_before_formal_training','sources':sources(),
         'input_mask_audit_sha256':sha(OUT/'input-mask-audit.json'),'baseline_read_only':baseline,
         'formal_fits':90,'formal_pretrains':90,'april_rows_read':0})
    print('PREPARED 30 view/split audits; 15 baseline records',flush=True)

def pilot():
    d=load(SPLITS[0]);tensors,audit=masked(d,'behavior')
    nm.seed_all(2026);m=nm.Model(d['dims'],'AE',decoder=True)
    _,pre_s,_,_,_=nm.pretrain_AE(m,tensors['fit'],epochs=1,seed=2026)
    m.dec=None
    _,sup_s,_=nm.supervised(m,tensors['fit'],tensors['yfit'],epochs=1,seed=2026)
    r={'status':'fit_only_timing_no_cal_or_jan_forward','pilot_pretrain_epochs':1,'pilot_supervised_epochs':1,
       'pretrain_seconds':pre_s,'supervised_seconds':sup_s,'extrapolated_90_training_seconds':90*(20*pre_s+50*sup_s),
       'caveat':'Linear warmup timing estimate, excludes inference/save/calibration and shared CPU contention.'}
    dump(OUT/'pilot-timing.json',r);print(json.dumps(r),flush=True)

def validate_freeze():
    freeze=json.loads((OUT/'source-freeze.json').read_text(encoding='utf-8'))
    assert freeze['sources']==sources(),'Source or plan changed since freeze'
    assert sha(OUT/'input-mask-audit.json')==freeze['input_mask_audit_sha256']
    candidate=LAB/'candidate-freeze.json'
    assert candidate.exists(),'root candidate-freeze missing'
    return freeze,sha(candidate)

def main():
    began=time.perf_counter();freeze,candidate_sha=validate_freeze();rows=[];failures=[]
    old_rows=OUT/'run-support.csv'
    if old_rows.exists(): rows=pd.read_csv(old_rows).to_dict('records')
    failure_file=OUT/'failures.json'
    if failure_file.exists(): failures=json.loads(failure_file.read_text(encoding='utf-8'))
    audits=json.loads((OUT/'input-mask-audit.json').read_text(encoding='utf-8'))
    done={r['run'] for r in rows}
    for split in SPLITS:
        d=load(split)
        for view in harness.manifest()['view_order']:
            tensors,audit=masked(d,view)
            expected=next(a for a in audits if a['split']==split and a['view']==view).copy();expected.pop('split')
            assert audit==expected
            for seed in SEEDS:
                name=run_id(split,view,seed)
                if name in done: continue
                tick=time.perf_counter()
                try:
                    nm.seed_all(seed);model=nm.Model(d['dims'],'AE',decoder=True)
                    initial=nm.shared_initialization_hash(model)
                    baseline=json.loads((ROOT/'neural'/f'split{split}__full141__AE__s{seed}-record.json').read_text(encoding='utf-8'))
                    bm=baseline['metadata'];assert initial==bm['initialization_sha256']
                    pre,pre_s,pre_order,initial_mse,final_mse=nm.pretrain_AE(model,tensors['fit'],epochs=20,seed=seed)
                    assert pre_order==bm['pretraining_order_sha256']
                    torch.save({'state_dict':model.state_dict(),'dims':d['dims'],'kind':'AE','decoder':True,'removed_view':view},PRIVATE/f'{name}-pretrained.pt')
                    model.dec=None
                    sup,sup_s,sup_order=nm.supervised(model,tensors['fit'],tensors['yfit'],epochs=50,seed=seed)
                    assert sup_order==bm['supervised_order_sha256']
                    z={part:nm.infer(model,tensors[part]) for part in PARTS}
                    model_path=PRIVATE/f'{name}-model.pt'
                    torch.save({'state_dict':model.state_dict(),'dims':d['dims'],'kind':'AE','decoder':False,'removed_view':view,'split':split,'seed':seed},model_path)
                    curves_path=PRIVATE/f'{name}-curves.json';dump(curves_path,{'pretrain':pre,'supervised':sup})
                    metadata={'followup_plan_sha256':sha(LAB/'task_plan.md'),'feature_plan_sha256':sha(OUT/'plan.md'),
                        'candidate_freeze_sha256':candidate_sha,'root_plan_field_meaning':'historical parent 155-run plan; operative followup_plan_sha256 above',
                        'removed_view':view,'mask_input_audit':audit,'initialization_sha256':initial,'supervised_order_sha256':sup_order,
                        'pretraining_order_sha256':pre_order,'paired_with_full_AE':True,'supervised_epochs':50,'pretraining_epochs':20,
                        'supervised_batch':512,'pretraining_batch':256,'Adam_lr':.001,'dropout':0,'hidden_per_view':16,'CPU_threads':2,
                        'supervised_updates':sum(r['updates'] for r in sup),'pretraining_updates':sum(r['updates'] for r in pre),
                        'supervised_client_exposures':sum(r['clients'] for r in sup),'pretraining_client_exposures':sum(r['clients'] for r in pre),
                        'supervised_seconds':sup_s,'pretraining_seconds':pre_s,'initial_fit_reconstruction_MSE':initial_mse,
                        'final_fit_reconstruction_MSE':final_mse,'reconstruction_target':'same whole-view-zero input',
                        'source_sha256':freeze['sources'],'input_dtype':'float32','saved_logits_dtype':'float64',
                        'cal_or_jan_used_for_predictive_training':False,'model_sha256':sha(model_path),'private_curves_sha256':sha(curves_path)}
                    rec=harness.write_run(OUT,name,f'AE-drop-{slug(view)}','full141',split,seed,z['fit'],z['cal'],z['jan'],metadata)
                    rows.append({'run':name,'split':split,'removed_view':view,'family':f'AE-drop-{slug(view)}','seed':seed,
                       'status':'complete','pretraining_seconds':pre_s,'supervised_seconds':sup_s,'total_seconds':time.perf_counter()-tick,
                       'initial_fit_reconstruction_MSE':initial_mse,'final_fit_reconstruction_MSE':final_mse,
                       'pretraining_updates':metadata['pretraining_updates'],'supervised_updates':metadata['supervised_updates'],
                       'record_sha256':sha(OUT/f'{name}-record.json'),'model_sha256':sha(model_path),'score_sha256':rec['score_sha256']})
                    print('DONE',len(rows),name,'seconds',round(rows[-1]['total_seconds'],2),flush=True)
                except Exception as e:
                    failures.append({'run':name,'error_type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()})
                    dump(failure_file,failures);raise
                pd.DataFrame(rows).to_csv(old_rows,index=False,lineterminator='\n');dump(failure_file,failures)
            del tensors;gc.collect()
        del d;gc.collect()
    assert len(rows)==90
    dump(OUT/'execution-verification.json',{'status':'90_complete_independent_readback_pending','supervised_models':90,'AE_pretrains':90,
        'failure_count':len(failures),'elapsed_this_process_seconds':time.perf_counter()-began,'candidate_freeze_sha256':candidate_sha,
        'sources_unchanged':sources()==freeze['sources'],'april_rows_read':0})

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');parser.add_argument('--pilot',action='store_true');args=parser.parse_args()
    torch.set_num_threads(2)
    with threadpool_limits(limits=2):
        if args.prepare: prepare()
        elif args.pilot: pilot()
        else: main()
