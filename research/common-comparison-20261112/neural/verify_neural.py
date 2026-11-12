"""Independent saved-state/array replay; no fitting, labels used only for final fit BCE check."""
import hashlib,importlib.util,json
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from threadpoolctl import threadpool_limits

OUT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('neural_shared_adapter',OUT/'run_neural.py')
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)

def replay(state,x,dims,kind,batch=2048):
    values=[]
    with torch.no_grad():
        for q in x.split(batch):
            if kind=='column-gate':q=q*torch.sigmoid(state['gate_a']*q+state['gate_b'])
            views=torch.stack([torch.relu(torch.nn.functional.linear(part,state[f'enc.{i}.weight'],state[f'enc.{i}.bias']))
                               for i,part in enumerate(torch.split(q,dims,dim=1))],dim=1)
            # Exact declared weighted-mean arithmetic, independent from Model.encode().
            w=torch.full((len(q),len(dims)),1/len(dims),device=q.device)
            latent=(views*w.unsqueeze(-1)).sum(1)
            prediction=torch.nn.functional.linear(latent,state['head.weight'],state['head.bias']).squeeze(1)
            values.append(prediction.numpy().astype(np.float64))
    return np.concatenate(values)

def main():
    torch.set_num_threads(2)
    rows=pd.read_csv(OUT/'run-support.csv')
    assert len(rows)==90
    assert rows.status.eq('complete').all()
    assert rows.groupby(['split','information','family']).size().eq(3).all()
    assert set(rows.split)==set(driver.SPLITS)
    assert set(rows.family)=={'mean','column-gate','AE'}
    assert set(rows.information)=={'base8','full141'}
    assert rows.groupby(['split','seed']).shared_initialization_sha256.nunique().eq(1).all()
    assert rows.groupby('seed').supervised_order_sha256.nunique().eq(1).all()
    assert rows.loc[rows.family.eq('AE')].groupby('seed').pretraining_order_sha256.nunique().eq(1).all()
    assert pd.read_csv(OUT/'supervised-curves.csv').shape[0]==4500
    assert pd.read_csv(OUT/'pretrain-curves.csv').shape[0]==600
    errors=[]
    with threadpool_limits(limits=2):
        for split in driver.SPLITS:
            for information in ['base8','full141']:
                shared=driver.load_shared(split,information)
                tensors=driver.prepare_tensors(shared,information)
                for row in rows.loc[rows.split.eq(split)&rows.information.eq(information)].itertuples():
                    artifact=torch.load(OUT/'private'/(row.run+'-model.pt'),map_location='cpu',weights_only=False)
                    assert artifact['split']==split and artifact['information']==information
                    assert artifact['dims']==shared['dims'] and not artifact['decoder']
                    arrays=np.load(OUT/row.logits_file)
                    record=json.loads((OUT/row.common_record_file).read_text(encoding='utf-8'))
                    common_arrays=np.load(OUT.parent/record['score_file'])
                    maxdiff=0.
                    for part in ['fit','cal','jan']:
                        assert arrays[part].dtype==np.float64
                        assert np.array_equal(arrays[part],common_arrays[part+'_logit'])
                        recomputed=replay(artifact['state_dict'],tensors[part],shared['dims'],row.family)
                        diff=float(abs(recomputed-arrays[part]).max())
                        assert np.array_equal(recomputed,arrays[part]),(row.run,part,diff)
                        maxdiff=max(maxdiff,diff)
                    bce=float(np.mean(np.logaddexp(0,arrays['fit'])-shared['yfit']*arrays['fit']))
                    assert np.isclose(bce,row.final_fit_BCE,rtol=1e-12,atol=1e-14)
                    assert hashlib.sha256((OUT/row.logits_file).read_bytes()).hexdigest()==row.logits_sha256
                    errors.append(dict(run=row.run,maximum_logit_abs_error=maxdiff,fit_BCE_recomputed=bce))
                del tensors,shared
            print('VERIFIED SPLIT',split,flush=True)
    pd.DataFrame(errors).to_csv(OUT/'model-replay.csv',index=False,lineterminator='\n')
    result=dict(status='PASS',supervised_runs_verified=len(errors),AE_pretraining_runs=30,
        inference_arrays_verified=270,all_saved_logits_exact=True,float64_container_verified=True,
        paired_initialization_and_batch_orders_verified=True,final_model_fit_BCE_recomputed=True,
        no_fit_calls=True,april_rows_read=0,eval_metrics_delegated_to_root_common_harness=True,
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT/'readback-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
