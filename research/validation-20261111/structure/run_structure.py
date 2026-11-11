"""Frozen P3 unsupervised diagnostics; no April reads or supervised model selection."""
import hashlib
import importlib.util
import io
import json
import math
import sys
import time
import warnings
from pathlib import Path
from zipfile import ZipFile

import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from scipy.special import softmax
from sklearn.cluster import HDBSCAN, KMeans
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (adjusted_rand_score, average_precision_score, calinski_harabasz_score,
                             davies_bouldin_score, roc_auc_score, silhouette_score)
from sklearn.mixture import GaussianMixture
from sklearn.neighbors import LocalOutlierFactor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

OUT=Path(__file__).resolve().parent
PRIVATE=OUT/'private'
PRIVATE.mkdir(parents=True,exist_ok=True)
KEY=['customer_unique_id','snapshot_date']
FEATURES=['R','F','M','average_item_rows','freight_share','recent30_orders','recent30_spend','state']
BASE=Path('E:/app-data/codex/outputs/is6400-rfm-weighted-2x2-20261110/run_rfm_2x2.py')
H05=Path('E:/app-data/codex/outputs/is6400-h05-january-handoff-20261110/validation_clusters.csv')
H05_TRAIN=Path('E:/app-data/codex/outputs/is6400-local-round2-20261110/role-04/train_clusters.csv')
H04=Path('E:/app-data/codex/outputs/is6400-h04-v02-intake-20261110/H04-role03-v02.zip')
SEEDS=[2026,2027,2028]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_json(name,obj):
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def csv(name,rows):
    pd.DataFrame(rows).to_csv(OUT/name,index=False,lineterminator='\n')

def prep(space):
    logscale=Pipeline([('log1p',FunctionTransformer(np.log1p)),('scale',StandardScaler())])
    if space=='rfm':
        return ColumnTransformer([('R',StandardScaler(),['R']),('FM',logscale,['F','M'])],sparse_threshold=0)
    return ColumnTransformer([('numeric',logscale,FEATURES[:-1]),
        ('state',OneHotEncoder(sparse_output=False,handle_unknown='ignore'),['state'])],sparse_threshold=0)

def select(frame,scores,k):
    order=frame[KEY].assign(score=scores).sort_values(['score']+KEY,ascending=[False,True,True]).index[:k]
    return frame.index.isin(order)

def metric(frame,scores,k,method,space,scope,threshold):
    chosen=select(frame,scores,k)
    y=frame.y.to_numpy()
    hits=int(y[chosen].sum())
    base=float(y.mean())
    return dict(method=method,space=space,scope=scope,threshold=threshold,n=len(frame),positives=int(y.sum()),
                k=k,hits=hits,precision=hits/k,recall=hits/y.sum(),lift=(hits/k)/base,
                random_expected_hits=k*base,ap=average_precision_score(y,scores),
                roc_auc=roc_auc_score(y,scores))

def main():
    started=time.time()
    spec=importlib.util.spec_from_file_location('verified_read_dev',BASE)
    base=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    train,jan=base.read_dev()
    train=train.reset_index(drop=True)
    jan=jan.merge(pd.read_csv(H05,dtype={'customer_unique_id':'string'}),on=KEY,validate='one_to_one')
    tg=pd.read_csv(H05_TRAIN,dtype={'customer_unique_id':'string'})
    train=train.merge(tg,on=KEY,validate='one_to_one')
    assert jan.cluster_id.eq(1).sum()==12330 and jan.loc[jan.cluster_id.eq(1),'y'].sum()==90
    assert len(train)==21160 and len(jan)==29368
    sample=np.sort(np.random.default_rng(2026).choice(len(train),2000,replace=False))
    subsets={seed:np.sort(np.random.default_rng(seed).choice(len(train),int(.8*len(train)),replace=False)) for seed in SEEDS}
    np.savez_compressed(PRIVATE/'fixed_indices.npz',silhouette=sample,**{f'subsample_{s}':v for s,v in subsets.items()})
    train[KEY+['y','cluster_id']].to_csv(PRIVATE/'oct_keys_outcomes_h05.csv',index=False)
    jan[KEY+['y','cluster_id']].to_csv(PRIVATE/'jan_keys_outcomes_h05.csv',index=False)
    scores={}
    krows,grows,stability,density,density_subsamples,profiles,outcomes=[],[],[],[],[],[],[]
    selection={}
    with threadpool_limits(limits=2):
        for space in ['rfm','original8']:
            print('START SPACE',space,flush=True)
            transformer=prep(space)
            X=transformer.fit_transform(train[FEATURES])
            J=transformer.transform(jan[FEATURES])
            assert np.isfinite(X).all() and np.isfinite(J).all()
            joblib.dump(transformer,PRIVATE/f'{space}-transformer.joblib')
            np.savez_compressed(PRIVATE/f'{space}-transformed.npz',oct=X,jan=J)
            models={}
            for k in range(2,9):
                model=KMeans(n_clusters=k,random_state=42,n_init=20,max_iter=300,tol=1e-4,algorithm='lloyd').fit(X)
                models[k]=model
                labels=model.labels_
                sizes=np.bincount(labels,minlength=k)
                krows.append(dict(space=space,k=k,silhouette=float(silhouette_score(X[sample],labels[sample])),
                    davies_bouldin=float(davies_bouldin_score(X,labels)),calinski_harabasz=float(calinski_harabasz_score(X,labels)),
                    inertia=float(model.inertia_),smallest_cluster=int(sizes.min()),largest_cluster=int(sizes.max()),
                    smallest_share=float(sizes.min()/len(X)),n_sample=2000))
                joblib.dump(model,PRIVATE/f'{space}-kmeans-k{k}.joblib')
                print('KMEANS',space,k,krows[-1]['silhouette'],flush=True)
            rows=[r for r in krows if r['space']==space]
            best=max(r['silhouette'] for r in rows)
            winner=min(r['k'] for r in rows if best-r['silhouette']<=.001)
            selection[space]={'kmeans_silhouette_winner':winner,'kmeans_best_silhouette':best}
            for k in sorted({winner,3}):
                model=models[k]
                for name,frame,xx in [('oct',train,X),('jan',jan,J)]:
                    labs=model.predict(xx)
                    distances=model.transform(xx)
                    # Temperature 1 squared-distance affinity, descriptive only; not posterior probability.
                    weights=softmax(-.5*distances**2,axis=1)
                    np.savez_compressed(PRIVATE/f'{space}-kmeans-k{k}-{name}.npz',labels=labs,distances=distances.astype('float32'),
                        soft_distance_weights=weights.astype('float32'))
                    for label in range(k):
                        sub=frame.loc[labs==label]
                        profiles.append(dict(space=space,algorithm='kmeans',k=k,snapshot=name,cluster=label,n=len(sub),
                            R_median=float(sub.R.median()),F_median=float(sub.F.median()),M_median=float(sub.M.median())))
                        outcomes.append(dict(space=space,algorithm='kmeans',k=k,snapshot=name,cluster=label,n=len(sub),
                            positives=int(sub.y.sum()),rate=float(sub.y.mean())))
                if space=='rfm' and k==3:
                    ari=adjusted_rand_score(jan.cluster_id,model.predict(J))
                    selection[space]['h05_jan_ari']=float(ari)
                    assert ari==1.0,'Frozen RFM K3 must reproduce H05 partition'
                for seed,idx in subsets.items():
                    sampled=KMeans(n_clusters=k,random_state=42,n_init=20,max_iter=300,tol=1e-4,algorithm='lloyd').fit(X[idx])
                    stability.append(dict(space=space,algorithm='kmeans',k=k,min_cluster_size=None,seed=seed,
                        comparison='full_reference_predictions',n_reference=len(X),ari=float(adjusted_rand_score(model.labels_,sampled.predict(X)))))
                    joblib.dump(sampled,PRIVATE/f'{space}-kmeans-k{k}-sub{seed}.joblib')
            gmms={}
            for k in range(2,9):
                with warnings.catch_warnings(record=True) as caught:
                    model=GaussianMixture(n_components=k,covariance_type='diag',random_state=42,n_init=1,max_iter=300,reg_covar=1e-6).fit(X)
                gmms[k]=model
                grows.append(dict(space=space,k=k,bic=float(model.bic(X)),aic=float(model.aic(X)),
                    converged=bool(model.converged_),n_iter=int(model.n_iter_),warnings='; '.join(str(w.message) for w in caught)))
                joblib.dump(model,PRIVATE/f'{space}-gmm-k{k}.joblib')
                print('GMM',space,k,flush=True)
            gwinner=min([r for r in grows if r['space']==space],key=lambda r:r['bic'])['k']
            selection[space]['gmm_bic_winner']=gwinner
            for k in sorted({gwinner,3}):
                for name,xx in [('oct',X),('jan',J)]:
                    prob=gmms[k].predict_proba(xx)
                    np.savez_compressed(PRIVATE/f'{space}-gmm-k{k}-{name}.npz',labels=prob.argmax(axis=1),soft_posterior=prob.astype('float32'))
            for mcs in [200,500]:
                model=HDBSCAN(min_cluster_size=mcs,min_samples=20,n_jobs=2).fit(X)
                labs=model.labels_
                valid=labs>=0
                counts=pd.Series(labs).value_counts().sort_index().to_dict()
                sv=sample[labs[sample]>=0]
                sil=float(silhouette_score(X[sv],labs[sv])) if len(set(labs[sv]))>1 else None
                density.append(dict(space=space,min_cluster_size=mcs,min_samples=20,clusters=len(set(labs)-{-1}),
                    noise_n=int((~valid).sum()),noise_share=float((~valid).mean()),
                    smallest_cluster=int(pd.Series(labs[valid]).value_counts().min()) if valid.any() else 0,
                    silhouette_nonnoise_sample=sil,silhouette_n=len(sv),sizes_json=json.dumps({int(k):int(v) for k,v in counts.items()})))
                joblib.dump(model,PRIVATE/f'{space}-hdbscan-mcs{mcs}.joblib')
                np.savez_compressed(PRIVATE/f'{space}-hdbscan-mcs{mcs}-oct.npz',labels=labs,probabilities=model.probabilities_)
                for seed,idx in subsets.items():
                    sm=HDBSCAN(min_cluster_size=mcs,min_samples=20,n_jobs=2).fit(X[idx])
                    joblib.dump(sm,PRIVATE/f'{space}-hdbscan-mcs{mcs}-sub{seed}.joblib')
                    np.savez_compressed(PRIVATE/f'{space}-hdbscan-mcs{mcs}-sub{seed}.npz',indices=idx,labels=sm.labels_,probabilities=sm.probabilities_)
                    density_subsamples.append(dict(space=space,min_cluster_size=mcs,seed=seed,n=len(idx),
                        clusters=len(set(sm.labels_)-{-1}),noise_n=int((sm.labels_<0).sum()),
                        noise_share=float((sm.labels_<0).mean()),sizes_json=json.dumps({int(k):int(v) for k,v in pd.Series(sm.labels_).value_counts().sort_index().to_dict().items()})))
                    for mode in ['intersection_including_noise','intersection_both_nonnoise']:
                        keep=np.ones(len(idx),dtype=bool) if mode.endswith('including_noise') else (labs[idx]>=0)&(sm.labels_>=0)
                        ari=float(adjusted_rand_score(labs[idx][keep],sm.labels_[keep])) if keep.sum()>1 else None
                        stability.append(dict(space=space,algorithm='hdbscan',k=None,min_cluster_size=mcs,seed=seed,
                            comparison=mode,n_reference=int(keep.sum()),ari=ari))
                print('HDBSCAN',space,mcs,density[-1],flush=True)
            for neighbors in [10,30,60]:
                method=f'LOF_n{neighbors}'
                model=LocalOutlierFactor(n_neighbors=neighbors,novelty=True,contamination='auto',n_jobs=2).fit(X)
                scores[space,method]=-model.score_samples(J)
                joblib.dump(model,PRIVATE/f'{space}-{method}.joblib')
                print('ANOMALY',space,method,flush=True)
            model=IsolationForest(n_estimators=200,contamination='auto',random_state=2026,n_jobs=2).fit(X)
            scores[space,'IsolationForest']=-model.score_samples(J)
            joblib.dump(model,PRIVATE/f'{space}-IsolationForest.joblib')
            csv('kmeans_geometry.csv',krows)
            csv('gmm_bic.csv',grows)
            csv('stability.csv',stability)
            csv('density_summary.csv',density)
            csv('density_subsamples.csv',density_subsamples)
            csv('cluster_profiles.csv',profiles)
            csv('cluster_outcomes_descriptive.csv',outcomes)
            write_json('selection.json',selection)
        with ZipFile(H04) as z:
            member=next(n for n in z.namelist() if n.endswith('/validation_predictions.csv'))
            predicted=pd.read_csv(io.BytesIO(z.read(member)),dtype={'customer_unique_id':'string'})
        matched=jan[KEY+['y']].merge(predicted,on=KEY,validate='one_to_one',suffixes=('','_source'))
        assert np.array_equal(matched.y,matched.y_source)
        scores['baseline','Recency']=-jan.R.to_numpy()
        scores['baseline','WeightedLR']=matched.LogisticRegressionWeighted_score.to_numpy()
        result=[]
        long=jan.cluster_id.eq(1).to_numpy()
        for (space,method),score in scores.items():
            assert np.isfinite(score).all()
            for fraction in [.05,.1,.2]:
                result.append(metric(jan,score,math.ceil(len(jan)*fraction),method,space,'all',fraction))
            result.append(metric(jan.loc[long].reset_index(drop=True),score[long],79,method,space,'H05_cluster1',79))
        csv('anomaly_outcomes.csv',result)
        private_score=jan[KEY].copy()
        for (space,method),score in scores.items():
            private_score[f'{space}__{method}']=score
        private_score.to_csv(PRIVATE/'jan_anomaly_scores.csv',index=False,lineterminator='\n')
        basehits=[r for r in result if r['method']=='WeightedLR' and r['scope']=='all' and r['threshold']==.1][0]
        assert basehits['hits']==50
        assert [r for r in result if r['method']=='Recency' and r['scope']=='all' and r['threshold']==.1][0]['hits']==30
        mainrows=[r for r in result if r['space']=='original8' and r['scope']=='all' and r['threshold']==.1]
        weak=all(r['hits']<=50 and r['ap']<=basehits['ap'] for r in mainrows)
        write_json('stop_decision.json',dict(predefined_rule_weak=weak,action='stop_no_backend_expansion' if weak else 'signal_only_parent_review',
            reference_weighted_hits=50,reference_weighted_ap=basehits['ap'],main_space='original8',jan_seen=True))
        fig,axes=plt.subplots(1,2,figsize=(11,4))
        for space in ['rfm','original8']:
            sub=pd.DataFrame(krows).query('space == @space')
            axes[0].plot(sub.k,sub.silhouette,'o-',label=space)
            sub=pd.DataFrame(grows).query('space == @space')
            axes[1].plot(sub.k,sub.bic,'o-',label=space)
        axes[0].set(xlabel='K',ylabel='Training silhouette (fixed n=2000)',title='Geometry criterion')
        axes[1].set(xlabel='K',ylabel='Training BIC (lower is better)',title='Diagonal GMM criterion')
        for ax in axes: ax.legend(); ax.grid(alpha=.2)
        fig.tight_layout()
        for ext in ['png','svg']: fig.savefig(OUT/f'cluster_selection.{ext}',dpi=150)
        plt.close(fig)
        display=pd.DataFrame(result).query("scope == 'all' and threshold == 0.1")
        fig,ax=plt.subplots(figsize=(10,4.5))
        labels=display.space+' / '+display.method
        ax.barh(labels,display.hits,color=['#4477aa' if s=='original8' else '#aabbcc' for s in display.space])
        ax.axvline(50,color='#cc6677',linestyle='--',label='Weighted LR: 50')
        ax.axvline(2937*230/29368,color='gray',linestyle=':',label='Random expected hits')
        ax.set(xlabel='January positives in fixed top 2937',title='Anomaly rank is not repurchase probability')
        ax.legend(loc='lower right'); fig.tight_layout()
        for ext in ['png','svg']: fig.savefig(OUT/f'anomaly_top10.{ext}',dpi=150)
        plt.close(fig)
    manifest={str(p.relative_to(OUT)).replace(chr(92),'/'):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='verification.json'}
    write_json('verification.json',dict(status='complete',oct_n=len(train),oct_positives=int(train.y.sum()),jan_n=len(jan),jan_positives=int(jan.y.sum()),
        april_rows_parsed=0,fit_labels_used=False,selection_labels_used=False,h05_jan_sha256=sha(H05),h05_train_sha256=sha(H05_TRAIN),
        code_sha256=sha(Path(__file__)),plan_sha256=sha(OUT/'plan.md'),python=sys.version.split()[0],sklearn=sklearn.__version__,
        third_party_hdbscan_installed=False,sklearn_hdbscan_oos_predict=False,elapsed_seconds=time.time()-started,
        threadpool_limit=2,files_sha256=manifest))
    print('COMPLETE',time.time()-started,flush=True)

if __name__=='__main__':
    main()
