"""Independent saved-state forward and parent-metric readback, no training."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import gc,json,hashlib
import numpy as np
import pandas as pd
import torch
from threadpoolctl import threadpool_limits
OUT=Path(__file__).resolve().parent;ROOT=OUT.parent.parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'neural'))
import eval_harness as h
from neural_models import Model,infer,final_reconstruction
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    rows=pd.read_csv(OUT/'run-support.csv');assert len(rows)==90
    checks=[];metrics=[];capacities=[]
    for split in h.manifest()['split_ids']:
        d=h.load_split(split,'full141',dense=True,dtype=np.float32)
        original={p:hashlib.sha256(d['X_'+p].tobytes()).hexdigest() for p in ['fit','cal','jan']}
        for view in h.manifest()['view_order']:
            idx=h.manifest()['view_order'].index(view);offset=np.cumsum([0]+d['dims']);lo,hi=offset[idx:idx+2]
            x={}
            for p in ['fit','cal','jan']:
                q=d['X_'+p].copy();q[:,lo:hi]=0;x[p]=torch.tensor(q,dtype=torch.float32)
                assert np.count_nonzero(q[:,lo:hi])==0
                assert np.array_equal(q[:,:lo],d['X_'+p][:,:lo]) and np.array_equal(q[:,hi:],d['X_'+p][:,hi:])
            for seed in h.manifest()['model_seeds']:
                name=f'split{split}__full141__AE-drop-{view.replace("_","-")}__s{seed}'
                rec=json.loads((OUT/f'{name}-record.json').read_text(encoding='utf-8'));md=rec['metadata']
                modelpath=OUT/'private'/f'{name}-model.pt';assert sha(modelpath)==md['model_sha256']
                assert sha(OUT/'private'/f'{name}-curves.json')==md['private_curves_sha256']
                saved=torch.load(modelpath,map_location='cpu',weights_only=True)
                model=Model(saved['dims'],'AE',decoder=False);model.load_state_dict(saved['state_dict'])
                scorepath=ROOT/rec['score_file'];assert sha(scorepath)==rec['score_sha256']
                scores=np.load(scorepath);maxdiff={}
                for p in ['fit','cal','jan']:
                    replay=infer(model,x[p]);maxdiff[p]=float(np.max(np.abs(replay-scores[p+'_logit'])))
                    assert np.array_equal(replay,scores[p+'_logit'])
                    p2=h.apply_calibration(replay,rec['calibration']);assert np.array_equal(p2,scores[p+'_calibrated'])
                    assert hashlib.sha256(d['X_'+p].tobytes()).hexdigest()==original[p]
                tags={k:rec[k] for k in ['run_id','family','information','split_id','seed']}
                recomputed=[];caps=[]
                for period in ['cal','jan']:
                    for variant,key in [('raw','raw'),('calibrated','calibrated')]:
                        recomputed.extend(tags|r for r in h.metric_rows(d['frames'][period],scores[period+'_'+key],variant,period))
                        if period=='jan': caps.extend(tags|r for r in h.capacity_rows(d['frames'][period],scores['jan_'+key],variant))
                assert h.jsonable(recomputed)==rec['metrics'];assert h.jsonable(caps)==rec['capacities']
                pre_saved=torch.load(OUT/'private'/f'{name}-pretrained.pt',map_location='cpu',weights_only=True)
                pre=Model(pre_saved['dims'],'AE',decoder=True);pre.load_state_dict(pre_saved['state_dict'])
                mse=final_reconstruction(pre,x['fit']);assert abs(mse-md['final_fit_reconstruction_MSE'])<1e-12
                c=h.fit_monotone_platt(scores['cal_logit'],d['y_cal'])
                assert abs(c['a']-rec['calibration']['a'])<1e-10 and abs(c['b']-rec['calibration']['b'])<1e-10
                metrics.extend(recomputed);capacities.extend(caps)
                checks.append({'run':name,'model_forward_max_abs_diff':max(maxdiff.values()),'calibrated_max_abs_diff':0.,
                   'parent_metrics_exact_equal':True,'capacities_exact_equal':True,'fit_reconstruction_abs_diff':abs(mse-md['final_fit_reconstruction_MSE']),
                   'calibration_parameters_reproduced':True,'full_source_matrices_unchanged':True})
                print('VERIFIED',len(checks),name,flush=True)
            del x;gc.collect()
        del d;gc.collect()
    freeze=json.loads((OUT/'source-freeze.json').read_text(encoding='utf-8'))
    for p,expected in freeze['sources'].items():assert sha(p)==expected
    for r in freeze['baseline_read_only']:
        assert sha(r['record'])==r['sha256']
        rec=json.loads(Path(r['record']).read_text(encoding='utf-8'));assert sha(ROOT/rec['score_file'])==r['score_sha256']
    pd.DataFrame(checks).to_csv(OUT/'model-readback.csv',index=False,lineterminator='\n')
    pd.DataFrame(metrics).to_csv(OUT/'common-metrics.csv',index=False,lineterminator='\n')
    pd.DataFrame(capacities).to_csv(OUT/'common-capacities.csv',index=False,lineterminator='\n')
    h.dump(OUT/'readback-verification.json',{'status':'independent_saved_state_forward_and_metrics_pass','models_checked':len(checks),
        'max_logit_abs_diff':max(c['model_forward_max_abs_diff'] for c in checks),'input_source_unchanged':True,
        'parent_15_baseline_records_and_scores_unchanged':True,'failures':json.loads((OUT/'failures.json').read_text()),
        'verification_code_sha256':sha(__file__),'april_rows_read':0})
if __name__=='__main__':
    torch.set_num_threads(2)
    with threadpool_limits(limits=2):main()
