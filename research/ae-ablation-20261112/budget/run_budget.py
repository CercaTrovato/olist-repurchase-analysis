"""Frozen budget ablations. Private outputs; no source or prior-run mutation."""
import argparse, gc, hashlib, importlib.util, json, sys, time, traceback
from pathlib import Path
sys.dont_write_bytecode=True
import numpy as np
import pandas as pd
import torch
from torch import nn
from threadpoolctl import threadpool_limits

OUT=Path(__file__).resolve().parent
LAB=OUT.parent
ROOT=LAB.parent
PRIVATE=OUT/'private'
SPLITS=list(range(20261111,20261116))
SEEDS=[2026,2027,2028]
CASES=['mean70','mean3040','AE-shuffled']
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
old=module('original_neural_models',ROOT/'neural/neural_models.py')
h=module('original_eval_harness',ROOT/'eval_harness.py')
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,value): h.dump(OUT/path,value)
def files_to_freeze():
    paths=[Path(__file__),OUT/'plan.md',OUT/'verify_budget.py',LAB/'task_plan.md',LAB/'candidate-freeze.json',ROOT/'task_plan.md',ROOT/'eval_harness.py',ROOT/'neural/neural_models.py',ROOT/'shared/data-manifest.json']
    for split in SPLITS:
        paths += [ROOT/'shared/private'/f'split-{split}'/name for name in ['indices.npz','base8-mask.npy','fit.npz','cal.npz','jan.npz']]
    return paths
def freeze():
    path=OUT/'source-freeze.json'
    assert not path.exists(),'Freeze already exists; never silently overwrite frozen inputs'
    hashes={str(p):sha(p) for p in files_to_freeze()}
    dump('source-freeze.json',dict(status='frozen_before_real_training_and_jan_scoring',sha256=hashes,cases=CASES,splits=SPLITS,seeds=SEEDS))
def assert_freeze():
    data=json.loads((OUT/'source-freeze.json').read_text())
    for p,digest in data['sha256'].items(): assert sha(p)==digest,('frozen input changed',p)
    return data
def init_model(dims,case,seed):
    old.seed_all(seed)
    return old.Model(dims,'AE' if case=='AE-shuffled' else 'mean',decoder=case=='AE-shuffled')
def derangement(n,generator):
    assert n>1
    original=torch.arange(n)
    while True:
        perm=torch.randperm(n,generator=generator)
        if torch.all(perm!=original):return perm
def shuffled_loss(model,q,perm):
    _,views,_=model.encode(q,True)
    targets=torch.split(q[perm],model.dims,dim=1)
    return sum(nn.functional.mse_loss(dec(views[:,i]),part) for i,(dec,part) in enumerate(zip(model.dec,targets)))/len(model.dims)
def pretrain(model,x,seed,epochs=20):
    inputs=torch.Generator().manual_seed(seed+901)
    targets=torch.Generator().manual_seed(seed+1901)
    opt=torch.optim.Adam(model.parameters(),lr=.001)
    orderhash=hashlib.sha256();targethash=hashlib.sha256();history=[]
    initial=old.final_reconstruction(model,x)
    start=time.perf_counter()
    for epoch in range(epochs):
        model.train();order=torch.randperm(len(x),generator=inputs);orderhash.update(order.numpy().tobytes());total=0.;updates=0
        for indices in order.split(256):
            q=x[indices];perm=derangement(len(q),targets);targethash.update(perm.numpy().tobytes())
            opt.zero_grad(set_to_none=True);loss=shuffled_loss(model,q,perm)
            assert torch.isfinite(loss);loss.backward();opt.step()
            total+=float(loss.detach())*len(q);updates+=1
        history.append(dict(epoch=epoch+1,online_view_mean_MSE=total/len(x),updates=updates,clients=len(x)))
    seconds=time.perf_counter()-start
    return history,dict(pretraining_seconds=seconds,pretraining_order_sha256=orderhash.hexdigest(),target_permutation_sha256=targethash.hexdigest(),initial_aligned_fit_MSE=initial,final_aligned_fit_MSE=old.final_reconstruction(model,x),pretraining_updates=sum(r['updates'] for r in history),pretraining_clients=sum(r['clients'] for r in history),target_fixed_points=0)
def supervised(model,x,y,seed,max_updates):
    model.train();opt=torch.optim.Adam(model.parameters(),lr=.001)
    generator=torch.Generator().manual_seed(seed)
    history=[];orderhash=hashlib.sha256();consumedhash=hashlib.sha256();count=0;epoch=0;first50=None;first50state=None
    started=time.perf_counter()
    while count<max_updates:
        epoch+=1;order=torch.randperm(len(x),generator=generator);orderhash.update(order.numpy().tobytes());total=0.;clients=0;updates=0
        for indices in order.split(512):
            if count==max_updates:break
            consumedhash.update(indices.numpy().tobytes());opt.zero_grad(set_to_none=True)
            loss=nn.functional.binary_cross_entropy_with_logits(model(x[indices]),y[indices]);assert torch.isfinite(loss)
            loss.backward();opt.step();total+=float(loss.detach())*len(indices);clients+=len(indices);updates+=1;count+=1
        history.append(dict(epoch=epoch,online_mean_BCE=total/clients,updates=updates,clients=clients,complete_epoch=clients==len(x)))
        if epoch==50 and clients==len(x):first50=orderhash.hexdigest();first50state=old.shared_initialization_hash(model)
    return history,dict(supervised_seconds=time.perf_counter()-started,supervised_order_sha256=orderhash.hexdigest(),supervised_first50_order_sha256=first50,supervised_first50_encoder_head_state_sha256=first50state,supervised_consumed_batch_order_sha256=consumedhash.hexdigest(),supervised_updates=count,supervised_clients=sum(r['clients'] for r in history),supervised_complete_epochs=sum(r['complete_epoch'] for r in history),supervised_partial_epoch_batches=history[-1]['updates'] if not history[-1]['complete_epoch'] else 0,Adam_reset_during_supervised=False)
def synthetic():
    torch.set_num_threads(2)
    x=torch.arange(31*12,dtype=torch.float32).reshape(31,12)/100;y=(torch.arange(31)%5==0).float();dims=[2]*6
    a=init_model(dims,'mean70',2026);b=init_model(dims,'mean70',2026)
    old.supervised(a,x,y,epochs=3,seed=2026);trace,meta=supervised(b,x,y,2026,3)
    assert all(torch.equal(a.state_dict()[k],b.state_dict()[k]) for k in a.state_dict())
    g=torch.Generator().manual_seed(3927)
    for n in [2,3,32,256]:
        for _ in range(20):assert (derangement(n,g)!=torch.arange(n)).all()
    print('synthetic exact old-supervised match and derangement checks PASS',flush=True)
def pilot():
    assert_freeze();d=h.load_split(SPLITS[0],'full141',dense=True,dtype=np.float32)
    x=torch.from_numpy(d['X_fit']);y=torch.tensor(d['y_fit'],dtype=torch.float32);result=[]
    for case in CASES:
        m=init_model(d['dims'],case,2026)
        pre={}
        if case=='AE-shuffled':_,pre=pretrain(m,x,2026,epochs=2);m.dec=None
        _,sup=supervised(m,x,y,2026,68)
        result.append(dict(case=case,discarded_timing_fit=True,pretraining=pre,supervised=sup))
    dump('pilot-timing.json',dict(status='fit_only_no_calibration_or_Jan_scoring',extra_discarded_supervised_fits=3,extra_discarded_pretraining_fits=1,runs=result))
    print(json.dumps(result),flush=True)
def main():
    assert_freeze();assert (OUT/'pilot-timing.json').exists();PRIVATE.mkdir(parents=True,exist_ok=True)
    assert not list(OUT.glob('*-record.json')),'Refuse accidental retraining/overwriting; inspect interrupted run first'
    rows=[];curves=[];precurves=[];records=[];failures=[];start=time.perf_counter()
    for split in SPLITS:
        d=h.load_split(split,'full141',dense=True,dtype=np.float32)
        tensors={part:torch.from_numpy(d['X_'+part]) for part in ['fit','cal','jan']};y=torch.tensor(d['y_fit'],dtype=torch.float32)
        assert (len(y),int(y.sum()),len(tensors['cal']),len(tensors['jan']))==(16928,169,4232,29368)
        for case in CASES:
            for seed in SEEDS:
                run=f'split{split}__full141__{case}__s{seed}';tick=time.perf_counter()
                try:
                    assert_freeze();m=init_model(d['dims'],case,seed);initial=old.shared_initialization_hash(m)
                    oldcase='AE' if case=='AE-shuffled' else 'mean'
                    prior=json.loads((ROOT/'neural'/f'split{split}__full141__{oldcase}__s{seed}-record.json').read_text())
                    assert initial==prior['metadata']['initialization_sha256']
                    pre=dict(pretraining_seconds=0.,pretraining_updates=0,pretraining_clients=0)
                    if case=='AE-shuffled':
                        trace,pre=pretrain(m,tensors['fit'],seed)
                        precurves.extend(dict(run=run,split=split,case=case,seed=seed,**r) for r in trace)
                        torch.save(dict(state_dict=m.state_dict(),dims=d['dims'],kind='AE',decoder=True),PRIVATE/f'{run}-pretrained.pt');m.dec=None
                    steps={'mean70':2380,'mean3040':3040,'AE-shuffled':1700}[case]
                    trace,sup=supervised(m,tensors['fit'],y,seed,steps)
                    curves.extend(dict(run=run,split=split,case=case,seed=seed,**r) for r in trace)
                    assert sup['supervised_first50_order_sha256']==prior['metadata']['supervised_order_sha256']
                    if case in ['mean70','mean3040']:
                        oldstate=torch.load(ROOT/'neural/private'/f'split{split}__full141__mean__s{seed}-model.pt',map_location='cpu',weights_only=True)['state_dict']
                        digest=hashlib.sha256()
                        for key,value in oldstate.items():
                            if key.startswith(('enc.','head.')):digest.update(key.encode('ascii'));digest.update(value.numpy().tobytes())
                        sup['old_mean50_encoder_head_state_sha256']=digest.hexdigest()
                        sup['supervised_first50_state_exact_old_mean50']=sup['supervised_first50_encoder_head_state_sha256']==digest.hexdigest()
                    if case=='AE-shuffled':assert pre['pretraining_order_sha256']==prior['metadata']['pretraining_order_sha256']
                    logits={part:old.infer(m,tensors[part]) for part in ['fit','cal','jan']}
                    np.savez_compressed(PRIVATE/f'{run}-logits.npz',**logits)
                    torch.save(dict(state_dict=m.state_dict(),dims=d['dims'],kind=m.kind,decoder=False,split=split,seed=seed,case=case),PRIVATE/f'{run}-model.pt')
                    np.savez_compressed(PRIVATE/f'{run}-curves.npz',supervised_online_BCE=np.array([r['online_mean_BCE'] for r in trace],dtype=np.float64),pretraining_online_MSE=np.array([r['online_view_mean_MSE'] for r in precurves if r['run']==run],dtype=np.float64))
                    fit_losses=np.logaddexp(0,logits['fit'])-d['y_fit']*logits['fit']
                    metadata=dict(followup_plan_sha256=sha(LAB/'task_plan.md'),candidate_freeze_sha256=sha(LAB/'candidate-freeze.json'),budget_plan_sha256=sha(OUT/'plan.md'),source_freeze_sha256=sha(OUT/'source-freeze.json'),code_sha256=sha(Path(__file__)),case=case,new_followup_not_original_155=True,information='full141',initialization_sha256=initial,old_reference_record_sha256=sha(ROOT/'neural'/f'split{split}__full141__{oldcase}__s{seed}-record.json'),**pre,**sup,final_fit_BCE=float(fit_losses.mean()),final_fit_BCE_sum=float(fit_losses.sum()),supervised_parameters=sum(p.numel() for p in m.parameters()),pretraining_batch=256 if case=='AE-shuffled' else None,supervised_batch=512,Adam_lr=.001,dropout=0,input_dtype='float32',logit_execution_dtype='float32',saved_logit_container='float64',cal_or_Jan_used_for_training=False,total_optimizer_updates=pre['pretraining_updates']+sup['supervised_updates'],total_input_client_presentations=pre['pretraining_clients']+sup['supervised_clients'],total_seconds_before_calibration=time.perf_counter()-tick)
                    rec=h.write_run(OUT,run,case,'full141',split,seed,logits['fit'],logits['cal'],logits['jan'],metadata=metadata);records.append(rec)
                    rows.append(dict(run=run,split=split,seed=seed,status='complete',**metadata,calibration_success=rec['calibration']['success'],calibration_projected_gradient_inf=rec['calibration']['projected_gradient_inf'],total_seconds=time.perf_counter()-tick))
                    pd.DataFrame(rows).to_csv(OUT/'run-support.csv',index=False)
                    pd.DataFrame(curves).to_csv(OUT/'supervised-curves.csv',index=False)
                    pd.DataFrame(precurves).to_csv(OUT/'pretrain-curves.csv',index=False)
                    dump('failures.json',failures)
                    print('DONE',len(rows),run,'seconds',rows[-1]['total_seconds'],flush=True)
                except Exception as error:
                    failures.append(dict(run=run,error_type=type(error).__name__,message=str(error),traceback=traceback.format_exc()));dump('failures.json',failures);raise
        del d,tensors,y;gc.collect()
    assert len(rows)==45
    pd.DataFrame([r for rec in records for r in rec['metrics']]).to_csv(OUT/'common-metrics.csv',index=False)
    pd.DataFrame([r for rec in records for r in rec['capacities']]).to_csv(OUT/'common-capacities.csv',index=False)
    ensemble_metrics=[];ensemble_capacities=[]
    for split in SPLITS:
        frames=h.load_frames(split)
        for case in CASES:
            for part in ['cal','jan']:
                p=np.mean([np.load(PRIVATE/f'split{split}__full141__{case}__s{seed}-scores.npz')[part+'_calibrated'] for seed in SEEDS],axis=0)
                tags=dict(split_id=split,family=case,information='full141',seed='probability_ensemble_3')
                ensemble_metrics.extend(tags|r for r in h.metric_rows(frames[part],p,'calibrated_probability_ensemble3',part))
                if part=='jan':ensemble_capacities.extend(tags|r for r in h.capacity_rows(frames[part],p,'calibrated_probability_ensemble3'))
    pd.DataFrame(ensemble_metrics).to_csv(OUT/'ensemble-metrics.csv',index=False)
    pd.DataFrame(ensemble_capacities).to_csv(OUT/'ensemble-capacities.csv',index=False)
    dump('execution.json',dict(status='45_runs_complete_independent_replay_pending',supervised_fits=45,AE_pretraining_fits=15,elapsed_seconds=time.perf_counter()-start,failure_count=len(failures),CPU_threads=2,torch=torch.__version__,input_hashes=assert_freeze()))
    print('COMPLETE 45',time.perf_counter()-start,flush=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['synthetic','freeze','pilot','run']);args=parser.parse_args()
    torch.set_num_threads(2)
    with threadpool_limits(limits=2):globals()[{'run':'main'}.get(args.mode,args.mode)]()
