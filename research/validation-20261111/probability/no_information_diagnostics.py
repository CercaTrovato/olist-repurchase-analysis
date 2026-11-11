"""Predeclared single-order/long information check, and portable-bundle verification."""
import sys
sys.dont_write_bytecode=True
import json,runpy
from pathlib import Path
import joblib,numpy as np,pandas as pd
from threadpoolctl import threadpool_limits

OUT=Path(__file__).resolve().parent
ROOT=OUT.parent.parent
def main():
    util=runpy.run_path(str(OUT/'run_probability.py'))
    source=runpy.run_path(str(ROOT/'is6400-rfm-weighted-2x2-20261110/run_rfm_2x2.py'))
    train,jan=source['read_dev']()
    scores=pd.read_csv(OUT/'private/january-all-scores.csv',dtype={'customer_unique_id':'string'},float_precision='round_trip')
    oof=pd.read_csv(OUT/'private/october-oof-scores.csv',dtype={'customer_unique_id':'string'},float_precision='round_trip')
    key=util['KEY']
    jan=jan.merge(scores[key+['cluster_id']],on=key,validate='one_to_one')
    train=train.merge(oof[key+['cluster_id']],on=key,validate='one_to_one')
    assert jan[key].equals(scores[key])
    candidates=['LR3','LR8','weightedLR','weightedLR-prior-corrected','weightedLR-oof-Platt','CB8-unweighted','CB14-unweighted','group-shrink100-sigmoid']
    partitions=util['scopes'](jan)+[('single_order_F1',jan.F.eq(1).to_numpy())]
    rows=[];intervals=[];supports=[]
    y=jan.y.to_numpy(int);yt=train.y.to_numpy(int)
    for si,(scope,mask) in enumerate(partitions):
        tm=np.ones(len(train),bool) if scope=='all' else (train.F.eq(1).to_numpy() if scope=='single_order_F1' else train.cluster_id.eq(int(scope.split('_')[1])).to_numpy())
        ys=y[mask];n=len(ys);prior=float(yt[tm].mean());oracle=float(ys.mean())
        supports.append(dict(scope=scope,oct_n=int(tm.sum()),oct_events=int(yt[tm].sum()),jan_n=n,jan_events=int(ys.sum()),oct_scoped_prior=prior,jan_event_rate=oracle,jan_F1=int(jan.loc[mask,'F'].eq(1).sum())))
        for name,p in [('constant_Oct_global',float(yt.mean())),('constant_Oct_scoped',prior),('constant_Jan_oracle_DIAGNOSTIC_ONLY',oracle)]:
            rows.append(dict(scope=scope,method=name,**util['basic'](ys,np.full(n,p),True),**util['classification'](ys,np.full(n,p),.5)))
        rows.append(dict(scope=scope,method='always_negative_classification',n=n,events=int(ys.sum()),**util['classification'](ys,np.zeros(n),.5)))
        for m in candidates:
            p=scores.loc[mask,'score_'+m].to_numpy()
            rows.append(dict(scope=scope,method=m,**util['basic'](ys,p,True),**util['classification'](ys,p,.5)))
        baseline=util['loss_rows'](ys,np.full(n,prior))
        d=np.column_stack([(util['loss_rows'](ys,scores.loc[mask,'score_'+m].to_numpy())-baseline)[:,j] for m in candidates for j in [0,1]])
        rng=np.random.default_rng(20261121+si);reps=np.empty((2000,d.shape[1]))
        for b in range(0,2000,50):
            cnt=rng.multinomial(n,np.full(n,1/n),size=min(50,2000-b));reps[b:b+len(cnt)]=cnt@d/n
        for i,m in enumerate(candidates):
            for j,metric in enumerate(['logloss','brier']):
                r=reps[:,i*2+j];lo,hi=np.percentile(r,[2.5,97.5])
                intervals.append(dict(scope=scope,method=m,reference='constant_Oct_scoped',metric=metric,observed_difference=float(d[:,i*2+j].mean()),ci_low=float(lo),ci_high=float(hi),replicates=2000,seed=20261121+si))
    util['csv'](pd.DataFrame(rows),OUT/'no-information-and-single-order.csv')
    util['csv'](pd.DataFrame(intervals),OUT/'bootstrap-vs-scoped-no-information.csv')
    util['csv'](pd.DataFrame(supports),OUT/'information-support.csv')
    # Verify loaded bundle is portable and exactly replays January scores; no fit invocation.
    pred=runpy.run_path(str(OUT/'predict_lr_suite.py'))['predict'](jan,joblib.load(OUT/'private/lr-probability-predictors.joblib'))
    errors={c:float(np.max(np.abs(pred[c]-scores[c]))) for c in pred if c.startswith('score_')}
    assert max(errors.values())<1e-15
    (OUT/'supplement-verification.json').write_text(json.dumps(dict(portable_predictor_max_errors=errors,april_rows_parsed=0,all_january_customers_scored=len(jan),bootstrap_replicates=2000,oracle_baseline='Jan event rate is an explanatory minimum constant loss only; not a deployable model'),indent=2)+'\n',encoding='utf-8')
    print(pd.DataFrame(supports).to_string(index=False))
    print('Portable predictor checked',errors)
if __name__=='__main__':
    with threadpool_limits(limits=2):main()
