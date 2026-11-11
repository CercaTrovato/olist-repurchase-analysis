"""Predeclared seven-model numerical stopping-precision control; no new information or April reads."""
import hashlib,importlib.util,json,time,warnings
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.special import expit
from sklearn.base import clone
from sklearn.metrics import average_precision_score,brier_score_loss,log_loss,roc_auc_score
from threadpoolctl import threadpool_limits
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path(__file__).resolve().parent
P=OUT/'private';P.mkdir(parents=True,exist_ok=True)
ROOT=OUT.parent
OLD=ROOT.parent/'is6400-round3-20261111/baselines/private'
FEAT=ROOT/'features/private'
KEY=['customer_unique_id','snapshot_date']
INPUTS={}

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def track(p): INPUTS[str(p)]=sha(p);return p
def dump(name,obj): (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')

def objective_gradient(model,X,y):
    beta=model.coef_.ravel();b=model.intercept_[0]
    z=np.asarray(X@beta).ravel()+b
    n=len(y)
    if model.class_weight=='balanced':
        weight=np.where(y==1,n/(2*y.sum()),n/(2*(n-y.sum())))
    elif isinstance(model.class_weight,dict): weight=np.array([model.class_weight[int(v)] for v in y])
    else: weight=np.ones(n)
    residual=(expit(z)-y)*weight
    gradbeta=np.asarray(X.T@residual).ravel()+beta/model.C
    grad=np.r_[gradbeta,residual.sum()]
    bce=float(np.sum(weight*(np.logaddexp(0,z)-y*z)))
    l2=float(.5*np.sum(beta**2)/model.C)
    return dict(sum_weighted_BCE=bce,l2=l2,objective_sum=bce+l2,gradient_inf_sum=float(abs(grad).max()),
                gradient_inf_div_weight_sum=float(abs(grad).max()/weight.sum()),weight_sum=float(weight.sum())),z

def rank(frame,p,k):
    order=frame[KEY].assign(score=p).sort_values(['score']+KEY,ascending=[False,True,True]).index[:k]
    return frame.index.isin(order)

def metrics(frame,p):
    y=frame.y.to_numpy()
    long=frame.cluster_id.eq(1).to_numpy()
    chosen=rank(frame,p,2937)
    lf=frame.loc[long].reset_index(drop=True)
    lc=rank(lf,p[long],79)
    return dict(n=len(frame),positive=int(y.sum()),log_loss=log_loss(y,p),brier=brier_score_loss(y,p),
        ap=average_precision_score(y,p),auc=roc_auc_score(y,p),mean_probability=float(p.mean()),
        global_k=2937,global_hits=int(y[chosen].sum()),long_n=len(lf),long_positive=int(lf.y.sum()),
        long_k=79,long_hits=int(lf.y.to_numpy()[lc].sum())),chosen,lc

def main():
    started=time.time()
    assert (OUT/'plan.md').exists()
    readerpath=ROOT.parent/'is6400-rfm-weighted-2x2-20261110/run_rfm_2x2.py'
    spec=importlib.util.spec_from_file_location('convergence_read_dev',track(readerpath))
    reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    train,jan=reader.read_dev(); train=train.reset_index(drop=True)
    h05=track(ROOT.parent/'is6400-h05-january-handoff-20261110/validation_clusters.csv')
    jan=jan.merge(pd.read_csv(h05,dtype={'customer_unique_id':'string'}),on=KEY,validate='one_to_one')
    assert (len(train),int(train.y.sum()),len(jan),int(jan.y.sum()))==(21160,211,29368,230)
    assert (int(jan.cluster_id.eq(1).sum()),int(jan.loc[jan.cluster_id.eq(1),'y'].sum()))==(12330,90)
    y=train.y.to_numpy(float)
    train[KEY+['y']].to_csv(P/'train-keys-outcomes.csv',index=False,lineterminator='\n')
    jan[KEY+['y','cluster_id']].to_csv(P/'jan-keys-outcomes-h05.csv',index=False,lineterminator='\n')
    p1=pd.read_csv(track(ROOT/'probability/private/january-all-scores.csv'),dtype={'customer_unique_id':'string'},float_precision='round_trip')
    p2=pd.read_csv(track(FEAT/'january-scores.csv'),dtype={'customer_unique_id':'string'},float_precision='round_trip')
    assert p1[KEY].equals(jan[KEY]) and p2[KEY].equals(jan[KEY])
    assert np.array_equal(p1.y,jan.y) and np.array_equal(p2.y,jan.y)
    rows=[];changes=[];specs=[]
    with threadpool_limits(limits=2):
        for source,name in [('baseline','LR3'),('baseline','LR8'),('baseline','weightedLR'),
                            ('features','lr8'),('features','lr8-geo'),('features','full-structure'),('features','structure-text')]:
            candidate=source+'__'+name
            if source=='baseline':
                path=track(OLD/(name+'.joblib'));artifact=joblib.load(path)
                original=artifact['pipeline'].named_steps['model']
                transform=artifact['pipeline'].named_steps['preprocess']
                X=transform.transform(train[artifact['fields']]);J=transform.transform(jan[artifact['fields']])
                expected=p1['score_'+name].to_numpy()
                inputs=dict(kind='original_saved_preprocessor',model_path=str(path),fields=artifact['fields'])
            else:
                path=track(FEAT/(name+'-lr.joblib'));original=joblib.load(path)
                xp=track(FEAT/(name+'-october-matrix.npz'));jp=track(FEAT/(name+'-january-matrix.npz'))
                X=sparse.load_npz(xp);J=sparse.load_npz(jp);expected=p2[name+'_score'].to_numpy()
                inputs=dict(kind='saved_sparse_matrices',model_path=str(path),october_matrix=str(xp),january_matrix=str(jp))
            assert original.solver=='lbfgs' and original.penalty=='l2' and original.fit_intercept
            assert X.shape[0]==21160 and J.shape[0]==29368 and X.shape[1]==J.shape[1]
            old_score=original.predict_proba(J)[:,1]
            assert np.max(abs(old_score-expected))<1e-12
            old_objective,oldz=objective_gradient(original,X,y)
            model=clone(original).set_params(tol=1e-10,max_iter=5000)
            tick=time.time()
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always')
                model.fit(X,y)
            seconds=time.time()-tick
            new_objective,newz=objective_gradient(model,X,y)
            new_score=model.predict_proba(J)[:,1]
            modelpath=P/(candidate+'-high-precision.joblib')
            joblib.dump(model,modelpath)
            np.savez_compressed(P/(candidate+'-scores.npz'),old_jan=old_score,new_jan=new_score,old_train_logit=oldz,new_train_logit=newz)
            for variant,estimator,p,obj in [('old',original,old_score,old_objective),('high_precision',model,new_score,new_objective)]:
                met,_,_=metrics(jan,p)
                iterations=int(estimator.n_iter_.max())
                warningtexts=[] if variant=='old' else [str(w.message) for w in caught]
                rows.append(dict(candidate=candidate,source=source,method=name,variant=variant,dimension=X.shape[1],
                    train_n=len(train),train_positive=int(y.sum()),C=estimator.C,class_weight=str(estimator.class_weight),
                    tol=estimator.tol,max_iter=estimator.max_iter,n_iter=iterations,
                    warning=' | '.join(warningtexts),hit_iteration_cap=iterations>=estimator.max_iter,
                    gradient_at_requested_tolerance=obj['gradient_inf_div_weight_sum']<=estimator.tol,
                    fit_seconds=seconds if variant=='high_precision' else None,
                    **obj,**met))
            _,oldmask,oldlong=metrics(jan,old_score);_,newmask,newlong=metrics(jan,new_score)
            changes.append(dict(candidate=candidate,maximum_probability_abs_change=float(abs(new_score-old_score).max()),
                mean_probability_abs_change=float(abs(new_score-old_score).mean()),
                global_symmetric_difference=int(np.sum(oldmask!=newmask)),global_replacements=int(np.sum(newmask&~oldmask)),
                long_symmetric_difference=int(np.sum(oldlong!=newlong)),long_replacements=int(np.sum(newlong&~oldlong)),
                objective_change=new_objective['objective_sum']-old_objective['objective_sum'],
                new_warning=' | '.join(str(w.message) for w in caught),new_n_iter=int(model.n_iter_.max()),
                cap_reached=bool(model.n_iter_.max()>=5000)))
            specs.append(dict(candidate=candidate,original_params=original.get_params(),high_precision_params=model.get_params(),**inputs))
            pd.DataFrame(rows).to_csv(OUT/'old-new-metrics.csv',index=False,lineterminator='\n')
            pd.DataFrame(changes).to_csv(OUT/'score-and-list-changes.csv',index=False,lineterminator='\n')
            print(candidate,'old/new niter',int(original.n_iter_.max()),int(model.n_iter_.max()),
                  'grad',old_objective['gradient_inf_sum'],new_objective['gradient_inf_sum'],
                  'sec',seconds,'hits',rows[-2]['global_hits'],rows[-1]['global_hits'],flush=True)
    dump('private/model-specs.json',specs)
    df=pd.DataFrame(rows);old=df.loc[df.variant.eq('old')].set_index('candidate');new=df.loc[df.variant.eq('high_precision')].set_index('candidate')
    fig,axes=plt.subplots(1,3,figsize=(15,5.5))
    for ax,key,title in zip(axes,['log_loss','ap','global_hits'],['January Log loss delta','January AP delta','Top2937 hits delta']):
        value=new[key]-old[key];ax.barh(value.index,value,color='#4477aa');ax.axvline(0,c='gray',lw=.8)
        ax.set(xlabel='High precision minus original',title=title)
    fig.suptitle('Numerical stopping control: fixed features, C and training rows; seen January')
    fig.tight_layout()
    for ext in ['png','svg']:fig.savefig(OUT/f'numerical-control-deltas.{ext}',dpi=150)
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,5));position=np.arange(len(old))
    ax.barh(position-.18,old.gradient_inf_sum,.36,label='Original');ax.barh(position+.18,new.gradient_inf_sum,.36,label='tol1e-10/max_iter5000')
    ax.set_yticks(position,old.index);ax.set_xscale('log');ax.set(xlabel='Infinity norm of gradient, sum objective',title='Training optimization diagnostic')
    ax.legend();fig.tight_layout()
    for ext in ['png','svg']:fig.savefig(OUT/f'training-gradient.{ext}',dpi=150)
    plt.close(fig)
    assert all(sha(Path(path))==h for path,h in INPUTS.items())
    dump('verification.json',dict(status='execution_complete_readback_pending',candidates=7,seed_repetitions=1,
        train_n=len(train),train_positive=int(y.sum()),jan_n=len(jan),jan_positive=int(jan.y.sum()),
        long_n=12330,long_positive=90,april_rows_parsed=0,cpu_threads=2,
        C_feature_weight_and_preprocessing_changes=False,only_solver_stopping_parameters_changed=True,
        elapsed_seconds=time.time()-started,plan_sha256=sha(OUT/'plan.md'),code_sha256=sha(Path(__file__)),
        sklearn=__import__('sklearn').__version__,input_sha256=INPUTS,
        new_models_at_iteration_cap=[r['candidate'] for r in changes if r['cap_reached']],
        new_models_with_warnings=[r['candidate'] for r in changes if r['new_warning']]))
    print('COMPLETE',time.time()-started,flush=True)

if __name__=='__main__':main()
