"""Shared-data adapter is bound only after root freezes its schema; no feature creation or splitting."""
import argparse
import gc
import hashlib
import importlib.util
import json
import time
import traceback
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from threadpoolctl import threadpool_limits
from neural_models import Model,seed_all,shared_initialization_hash,infer,supervised,pretrain_AE

OUT=Path(__file__).resolve().parent
P=OUT/'private';P.mkdir(parents=True,exist_ok=True)
_harness_spec=importlib.util.spec_from_file_location('common_evaluation_harness',OUT.parent/'eval_harness.py')
harness=importlib.util.module_from_spec(_harness_spec)
_harness_spec.loader.exec_module(harness)
SPLITS=[20261111,20261112,20261113,20261114,20261115]
SEEDS=[2026,2027,2028]
FAMILIES=['mean','column-gate','AE']

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(name,value): (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')

def load_shared(split,information):
    """Only normalize names from root API; all loading, masking and row selection are root-owned."""
    data=harness.load_split(split,information,dense=True,dtype=np.float32)
    return {**{part:data['X_'+part] for part in ['fit','cal','jan']},
        'yfit':data['y_fit'],'ycal':data['y_cal'],'yjan':data['y_jan'],
        'dims':data['dims'],'base8_mask':data['base8_mask'],'frames':data['frames'],
        'provenance':dict(split=split,information=information,description=data['description'],
                          manifest_sha256=harness.sha(harness.SH/'data-manifest.json'),
                          eval_harness_sha256=harness.sha(OUT.parent/'eval_harness.py'),
                          source='root load_split(dense=True,dtype=float32); no local masking/preprocessing')}

def prepare_tensors(shared,information):
    dims=shared['dims']
    tensors={}
    for part in ['fit','cal','jan']:
        original=shared[part]
        if original.dtype!=np.float32: raise TypeError(f'{part} root-loaded matrix must be float32')
        if original.ndim!=2 or original.shape[1]!=sum(dims): raise ValueError(f'{part} dimension mismatch')
        if not np.isfinite(original).all(): raise FloatingPointError(f'{part} inputs contain NaN/Inf')
        tensors[part]=torch.from_numpy(original)
    tensors['yfit']=torch.tensor(shared['yfit'],dtype=torch.float32)
    assert (len(tensors['fit']),int(tensors['yfit'].sum()),len(tensors['cal']),len(tensors['jan']))==(16928,169,4232,29368)
    return tensors

def pilot():
    shared=load_shared(SPLITS[0],'full141')
    x=prepare_tensors(shared,'full141')
    seed_all(2026)
    model=Model(shared['dims'],'mean')
    _,seconds,_=supervised(model,x['fit'],x['yfit'],epochs=2,seed=2026)
    result=dict(status='timing_only_no_cal_or_jan_scoring',split=SPLITS[0],seed=2026,family='mean',epochs=2,
        fit_n=len(x['fit']),dims=shared['dims'],seconds=seconds,linear_extrapolation_mean50_seconds=seconds*25,
        caveat='Mean timing excludes AE pretraining, input load, inference, I/O; not a measured total runtime')
    dump('pilot-timing.json',result)
    print(json.dumps(result),flush=True)

def main():
    began=time.perf_counter()
    rows=[];curve=[];precurve=[];failures=[];input_records=[];pairing={}
    for split in SPLITS:
        for information in ['base8','full141']:
            shared=load_shared(split,information)
            input_records.append(shared['provenance'])
            tensors=prepare_tensors(shared,information)
            prevalence=float(tensors['yfit'].double().mean())
            constant_bce=float(-prevalence*np.log(prevalence)-(1-prevalence)*np.log1p(-prevalence))
            for family in FAMILIES:
                for seed in SEEDS:
                    name=f'split{split}__{information}__{family}__s{seed}'
                    tick=time.perf_counter()
                    try:
                        seed_all(seed)
                        model=Model(shared['dims'],family,decoder=family=='AE')
                        init_hash=shared_initialization_hash(model)
                        key=(split,seed)
                        if key in pairing: assert pairing[key]==init_hash,'Shared encoder/head initialization pairing failed'
                        else: pairing[key]=init_hash
                        pre_seconds=0.;initial_mse=None;final_mse=None;pre_order=None
                        pre_parameters=sum(p.numel() for p in model.parameters())
                        if family=='AE':
                            trace,pre_seconds,pre_order,initial_mse,final_mse=pretrain_AE(model,tensors['fit'],epochs=20,seed=seed)
                            precurve.extend(dict(run=name,split=split,information=information,family=family,seed=seed,**r) for r in trace)
                            torch.save(dict(state_dict=model.state_dict(),dims=shared['dims'],kind=family,decoder=True,
                                            split=split,seed=seed,information=information),P/(name+'-pretrained.pt'))
                            model.dec=None
                        history,seconds,super_order=supervised(model,tensors['fit'],tensors['yfit'],epochs=50,seed=seed)
                        curve.extend(dict(run=name,split=split,information=information,family=family,seed=seed,**r) for r in history)
                        saved={part:infer(model,tensors[part]) for part in ['fit','cal','jan']}
                        fit_bce=float(np.mean(np.logaddexp(0,saved['fit'])-shared['yfit']*saved['fit']))
                        scorepath=P/(name+'-logits.npz')
                        np.savez_compressed(scorepath,**saved)
                        torch.save(dict(state_dict=model.state_dict(),dims=shared['dims'],kind=family,decoder=False,
                            split=split,seed=seed,information=information,shared_provenance=shared['provenance']),P/(name+'-model.pt'))
                        np.savez_compressed(P/(name+'-curves.npz'),supervised_online_BCE=np.array([r['online_mean_BCE'] for r in history],dtype=np.float64),
                            pretrain_online_MSE=np.array([] if family!='AE' else [r['online_view_mean_MSE'] for r in trace],dtype=np.float64))
                        common_record=harness.write_run(OUT,name,family,information,split,seed,
                            saved['fit'],saved['cal'],saved['jan'],metadata=dict(
                                shared_provenance=shared['provenance'],supervised_parameters=sum(p.numel() for p in model.parameters()),
                                pretraining_total_parameters=pre_parameters if family=='AE' else 0,
                                supervised_epochs=50,supervised_batch=512,pretraining_epochs=20 if family=='AE' else 0,
                                pretraining_batch=256 if family=='AE' else None,Adam_lr=.001,
                                final_fit_BCE=fit_bce,constant_fit_BCE=constant_bce,supervised_seconds=seconds,
                                pretraining_seconds=pre_seconds,initialization_sha256=init_hash,
                                supervised_order_sha256=super_order,pretraining_order_sha256=pre_order,
                                code_sha256=sha(Path(__file__)),model_code_sha256=sha(OUT/'neural_models.py')))
                        rows.append(dict(run=name,split=split,information=information,family=family,seed=seed,status='complete',
                            fit_n=len(tensors['fit']),fit_positive=169,cal_n=4232,cal_positive=42,jan_n=29368,
                            total_input_columns=sum(shared['dims']),active_information_columns=int(np.sum(shared['base8_mask'])) if information=='base8' else sum(shared['dims']),
                            view_dims_json=json.dumps(shared['dims']),supervised_parameters=sum(p.numel() for p in model.parameters()),
                            pretraining_parameters=pre_parameters if family=='AE' else 0,supervised_epochs=50,pretraining_epochs=20 if family=='AE' else 0,
                            pretraining_active_parameters=(pre_parameters-sum(p.numel() for p in model.head.parameters())) if family=='AE' else 0,
                            supervised_seconds=seconds,pretraining_seconds=pre_seconds,total_seconds=time.perf_counter()-tick,
                            final_fit_BCE=fit_bce,constant_fit_BCE=constant_bce,fit_BCE_minus_constant=fit_bce-constant_bce,
                            initial_fit_reconstruction_MSE=initial_mse,final_fit_reconstruction_MSE=final_mse,
                            shared_initialization_sha256=init_hash,supervised_order_sha256=super_order,pretraining_order_sha256=pre_order,
                            logits_file=scorepath.relative_to(OUT).as_posix(),logits_sha256=sha(scorepath),
                            common_record_file=name+'-record.json',common_score_sha256=common_record['score_sha256'],
                            input_dtype='float32',saved_logit_container='float64',cal_or_jan_used_for_training=False))
                        print('DONE',len(rows),name,'fitBCE',fit_bce,'seconds',rows[-1]['total_seconds'],flush=True)
                    except Exception as error:
                        failures.append(dict(run=name,error_type=type(error).__name__,message=str(error),traceback=traceback.format_exc()))
                        dump('failures.json',failures)
                        print('FAILED',name,type(error).__name__,str(error),flush=True)
                        raise
                    pd.DataFrame(rows).to_csv(OUT/'run-support.csv',index=False,lineterminator='\n')
                    pd.DataFrame(curve).to_csv(OUT/'supervised-curves.csv',index=False,lineterminator='\n')
                    pd.DataFrame(precurve).to_csv(OUT/'pretrain-curves.csv',index=False,lineterminator='\n')
                    dump('failures.json',failures)
            del tensors,shared
            gc.collect()
    assert len(rows)==90 and len(precurve)==600 and len(curve)==4500
    dump('input-audit.json',input_records)
    dump('verification.json',dict(status='execution_complete_readback_pending',supervised_models=len(rows),AE_pretraining_runs=30,
        supervised_epoch_rows=len(curve),pretraining_epoch_rows=len(precurve),CPU_threads=2,april_rows_read=0,
        code_sha256=sha(Path(__file__)),model_code_sha256=sha(OUT/'neural_models.py'),plan_sha256=sha(OUT/'plan.md'),
        elapsed_seconds=time.perf_counter()-began,torch=torch.__version__,failure_count=len(failures),
        no_matrix_construction_or_split_generation=True))
    print('COMPLETE',len(rows),'seconds',time.perf_counter()-began,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--pilot',action='store_true');args=parser.parse_args()
    torch.set_num_threads(2)
    with threadpool_limits(limits=2):
        if args.pilot:pilot()
        else:main()
