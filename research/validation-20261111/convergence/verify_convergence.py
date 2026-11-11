"""Independent seven-model readback; no fit calls."""
import hashlib,importlib.util,json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.special import expit
from sklearn.metrics import average_precision_score,brier_score_loss,log_loss,roc_auc_score
from threadpoolctl import threadpool_limits
OUT=Path(__file__).resolve().parent;P=OUT/'private';KEY=['customer_unique_id','snapshot_date']
specs=json.loads((P/'model-specs.json').read_text())
run=json.loads((OUT/'verification.json').read_text())
assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==h for path,h in run['input_sha256'].items())
readerpath=OUT.parent.parent/'is6400-rfm-weighted-2x2-20261110/run_rfm_2x2.py'
spec=importlib.util.spec_from_file_location('verify_convergence_reader',readerpath)
reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
train,jan=reader.read_dev();train=train.reset_index(drop=True)
h05=pd.read_csv(OUT.parent.parent/'is6400-h05-january-handoff-20261110/validation_clusters.csv',dtype={'customer_unique_id':'string'})
jan=jan.merge(h05,on=KEY,validate='one_to_one')
for name,frame in [('train',train),('jan',jan)]:
    saved=pd.read_csv(P/('train-keys-outcomes.csv' if name=='train' else 'jan-keys-outcomes-h05.csv'),dtype={'customer_unique_id':'string'})
    assert frame[KEY+['y']].equals(saved[KEY+['y']])
metrics=pd.read_csv(OUT/'old-new-metrics.csv');changes=pd.read_csv(OUT/'score-and-list-changes.csv')
count=0;maxscore=0.
with threadpool_limits(limits=2):
    for item in specs:
        name=item['candidate']
        if item['kind']=='original_saved_preprocessor':
            artifact=joblib.load(item['model_path']);original=artifact['pipeline'].named_steps['model']
            X=artifact['pipeline'].named_steps['preprocess'].transform(train[item['fields']]);J=artifact['pipeline'].named_steps['preprocess'].transform(jan[item['fields']])
        else:
            original=joblib.load(item['model_path']);X=sparse.load_npz(item['october_matrix']);J=sparse.load_npz(item['january_matrix'])
        new=joblib.load(P/(name+'-high-precision.joblib'))
        changed={k for k in original.get_params() if original.get_params()[k]!=new.get_params()[k]}
        assert changed=={'tol','max_iter'},(name,changed)
        saved=np.load(P/(name+'-scores.npz'))
        masks={}
        for variant,model,scorekey,logitkey in [('old',original,'old_jan','old_train_logit'),('high_precision',new,'new_jan','new_train_logit')]:
            pp=model.predict_proba(J)[:,1];maxscore=max(maxscore,float(abs(pp-saved[scorekey]).max()));assert np.array_equal(pp,saved[scorekey])
            zz=model.decision_function(X);assert np.allclose(zz,saved[logitkey],rtol=0,atol=1e-12)
            row=metrics.loc[metrics.candidate.eq(name)&metrics.variant.eq(variant)].iloc[0]
            y=train.y.to_numpy();weight=np.ones(len(y)) if model.class_weight is None else np.where(y==1,len(y)/(2*y.sum()),len(y)/(2*(len(y)-y.sum())))
            beta=model.coef_.ravel();res=(expit(zz)-y)*weight
            loss=np.dot(weight,np.logaddexp(0,zz)-y*zz)+np.dot(beta,beta)/(2*model.C)
            grad=np.r_[np.asarray(X.T@res).ravel()+beta/model.C,res.sum()]
            assert np.isclose(loss,row.objective_sum,rtol=1e-11,atol=1e-9)
            assert np.isclose(abs(grad).max(),row.gradient_inf_sum,rtol=1e-8,atol=1e-9)
            yy=jan.y.to_numpy()
            expected=[log_loss(yy,pp),brier_score_loss(yy,pp),average_precision_score(yy,pp),roc_auc_score(yy,pp)]
            assert np.allclose(expected,[row.log_loss,row.brier,row.ap,row.auc],rtol=1e-11,atol=1e-12)
            frame=jan.assign(score=pp)
            ordered=frame.sort_values(['score']+KEY,ascending=[False,True,True])
            globalids=ordered.head(2937).index.to_numpy()
            longids=ordered.loc[ordered.cluster_id.eq(1)].head(79).index.to_numpy()
            assert int(jan.loc[globalids,'y'].sum())==row.global_hits
            assert int(jan.loc[longids,'y'].sum())==row.long_hits
            masks[variant]=(set(globalids),set(longids))
            count+=1
        change=changes.loc[changes.candidate.eq(name)].iloc[0]
        assert len(masks['old'][0]^masks['high_precision'][0])==change.global_symmetric_difference
        assert len(masks['old'][1]^masks['high_precision'][1])==change.long_symmetric_difference
        assert np.isclose(abs(saved['new_jan']-saved['old_jan']).max(),change.maximum_probability_abs_change)
result=dict(status='PASS',source_hashes_unchanged=len(run['input_sha256']),only_tol_and_maxiter_changed=True,
    old_new_models_readback=count,new_models=7,exact_january_score_max_error=maxscore,
    objectives_and_gradients_recomputed=True,natural_metrics_and_fixed_lists_recomputed=True,
    january_n=len(jan),january_positive=int(jan.y.sum()),april_rows_parsed=0,
    code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(OUT/'readback-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
