"""Read back saved outputs and independently recompute ranking counts and model arrays."""
import hashlib
import importlib.util
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

OUT=Path(__file__).resolve().parent
P=OUT/'private'
spec=importlib.util.spec_from_file_location('read_dev_verifier',Path('E:/app-data/codex/outputs/is6400-rfm-weighted-2x2-20261110/run_rfm_2x2.py'))
base=importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
train,jan=base.read_dev()
train=train.reset_index(drop=True)
jan=jan.reset_index(drop=True)
keys=['customer_unique_id','snapshot_date']
octkeys=pd.read_csv(P/'oct_keys_outcomes_h05.csv',dtype={'customer_unique_id':'string'})
jankeys=pd.read_csv(P/'jan_keys_outcomes_h05.csv',dtype={'customer_unique_id':'string'})
assert train[keys].equals(octkeys[keys]) and jan[keys].equals(jankeys[keys])
scores=pd.read_csv(P/'jan_anomaly_scores.csv',dtype={'customer_unique_id':'string'})
assert scores[keys].equals(jankeys[keys])
metrics=pd.read_csv(OUT/'anomaly_outcomes.csv')
verified_rows=0
for _,row in metrics.iterrows():
    keep=np.ones(len(jan),dtype=bool) if row.scope=='all' else jankeys.cluster_id.eq(1).to_numpy()
    frame=jan.loc[keep,keys+['y']].assign(score=scores.loc[keep,f'{row.space}__{row.method}'].to_numpy())
    selected=frame.sort_values(['score']+keys,ascending=[False,True,True]).head(int(row.k))
    assert int(selected.y.sum())==row.hits
    assert np.isclose(row.precision,row.hits/row.k)
    assert np.isclose(row.recall,row.hits/frame.y.sum())
    verified_rows+=1
selection=json.loads((OUT/'selection.json').read_text())
composition=[]
arrays_verified=[]
with threadpool_limits(limits=2):
    for space in ['rfm','original8']:
        data=np.load(P/f'{space}-transformed.npz')
        transformer=joblib.load(P/f'{space}-transformer.joblib')
        assert np.array_equal(data['oct'],transformer.transform(train))
        assert np.array_equal(data['jan'],transformer.transform(jan))
        assert data['oct'].dtype==np.float64
        for k in sorted({3,selection[space]['kmeans_silhouette_winner']}):
            model=joblib.load(P/f'{space}-kmeans-k{k}.joblib')
            for snapshot,frame in [('oct',train),('jan',jan)]:
                saved=np.load(P/f'{space}-kmeans-k{k}-{snapshot}.npz')
                assert np.array_equal(saved['labels'],model.predict(data[snapshot]))
                assert np.allclose(saved['distances'],model.transform(data[snapshot]),rtol=1e-6,atol=1e-6)
                assert np.allclose(saved['soft_distance_weights'].sum(axis=1),1,atol=1e-6)
                arrays_verified.append(f'{space}-kmeans-k{k}-{snapshot}')
                for label in range(k):
                    sub=frame.loc[saved['labels']==label]
                    states=sub.state.value_counts(normalize=True)
                    composition.append(dict(space=space,algorithm='kmeans',k=k,snapshot=snapshot,cluster=label,n=len(sub),
                        single_purchase_share=float(sub.F.eq(1).mean()),dominant_state=states.index[0],dominant_state_share=float(states.iloc[0])))
        for k in sorted({3,selection[space]['gmm_bic_winner']}):
            model=joblib.load(P/f'{space}-gmm-k{k}.joblib')
            for snapshot in ['oct','jan']:
                saved=np.load(P/f'{space}-gmm-k{k}-{snapshot}.npz')
                assert np.array_equal(saved['labels'],model.predict(data[snapshot]))
                assert np.allclose(saved['soft_posterior'],model.predict_proba(data[snapshot]),rtol=1e-5,atol=1e-6)
                assert np.allclose(saved['soft_posterior'].sum(axis=1),1,atol=1e-6)
                arrays_verified.append(f'{space}-gmm-k{k}-{snapshot}')
        for mcs in [200,500]:
            saved=np.load(P/f'{space}-hdbscan-mcs{mcs}-oct.npz')
            for label in sorted(set(saved['labels'])):
                sub=train.loc[saved['labels']==label]
                states=sub.state.value_counts(normalize=True)
                composition.append(dict(space=space,algorithm='hdbscan',k=mcs,snapshot='oct',cluster=label,n=len(sub),
                    single_purchase_share=float(sub.F.eq(1).mean()),dominant_state=states.index[0],dominant_state_share=float(states.iloc[0])))
pd.DataFrame(composition).to_csv(OUT/'cluster_composition.csv',index=False,lineterminator='\n')
ver=json.loads((OUT/'verification.json').read_text())
bad=[name for name,h in ver['files_sha256'].items() if hashlib.sha256((OUT/name).read_bytes()).hexdigest()!=h]
assert not bad,bad
result=dict(status='PASS',ranking_metric_rows_recomputed=verified_rows,selected_model_arrays_verified=arrays_verified,
    rows_order_verified={'oct':len(train),'jan':len(jan)},soft_weight_sums_verified=True,
    exact_float64_transforms_verified=True,manifest_existing_files_verified=len(ver['files_sha256']),
    no_april_read=True,code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(OUT/'readback_verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
