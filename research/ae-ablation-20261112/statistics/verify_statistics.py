"""Read-only source scores; independent means, sklearn metrics and interval quantiles."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json,itertools
import numpy as np,pandas as pd
from sklearn.metrics import log_loss,brier_score_loss,average_precision_score,roc_auc_score
from threadpoolctl import threadpool_limits
import run_statistics as run
OUT=Path(__file__).resolve().parent
def main():
    records=run.load();points=pd.read_csv(OUT/'ensemble-primary-by-split.csv').set_index(['split_id','model','scope']);checks=[]
    groups={}
    for i,r,a in records:groups.setdefault((i['split_id'],i['model']),[]).append((i,r,a))
    for split in run.SPLITS:
        frames=run.h.load_frames(split);jan=frames['jan'].sort_values(run.KEY).reset_index(drop=True);original=frames['jan'];order=original.sort_values(run.KEY).index.to_numpy();saved=np.load(OUT/'private'/f'split{split}-ensemble-probabilities.npz')
        recorded=pd.read_csv(OUT/'private'/f'split{split}-jan-cohort.csv',dtype={k:'string' for k in run.KEY})
        assert jan[run.KEY].astype('string').equals(recorded[run.KEY]);assert np.array_equal(jan.y,recorded.y)
        for model in run.SYSTEMS:
            members=groups[split,model];p=np.mean(np.stack([a['jan_calibrated'][order] for i,r,a in members]),axis=0,dtype=np.float64)
            error=float(np.abs(p-saved['jan__'+model]).max());assert error==0.
            for scope,mask in run.masks(jan):
                f=jan.loc[mask].reset_index(drop=True);q=p[mask];y=f.y.to_numpy();ix=np.lexsort((f.snapshot_date.astype(str),f.customer_unique_id.astype(str),-q));k=2937 if scope=='all' else 79
                actual=dict(logloss=log_loss(y,q,labels=[0,1]),brier=brier_score_loss(y,q),AP=average_precision_score(y,q),AUC=roc_auc_score(y,q),hits=int(y[ix[:k]].sum()),precision=float(y[ix[:k]].mean()),recall=float(y[ix[:k]].sum()/y.sum()))
                expected=points.loc[split,model,scope]
                for metric,value in actual.items():assert abs(value-expected[metric])<1e-11,(split,model,scope,metric,value,expected[metric])
                checks.append(dict(split_id=split,model=model,scope=scope,ensemble_mean_max_abs=error,**actual))
    run.csv(pd.DataFrame(checks),'independent-ensemble-replay.csv')
    reps=pd.read_csv(OUT/'private/canonical-bootstrap-replicates.csv.gz');observed=pd.read_csv(OUT/'canonical-bootstrap-observed.csv');intervals=pd.read_csv(OUT/'canonical-paired-bootstrap-intervals.csv')
    assert len(reps)==56000 and len(intervals)==350 and len(observed)==28
    assert not reps.duplicated(['scope','replicate','model']).any()
    for (scope,model),part in reps.groupby(['scope','model']):
        assert len(part)==2000 and set(part.replicate)==set(range(1,2001));assert (part.k==(2937 if scope=='all' else 79)).all();assert (part.n==(29368 if scope=='all' else 12330)).all()
    wide={}
    for scope in ['all','long']:
        for metric in run.METRICS:wide[scope,metric]=reps[reps.scope==scope].pivot(index='replicate',columns='model',values=metric)
    for row in intervals.itertuples():
        difference=wide[row.scope,row.metric][row.candidate]-wide[row.scope,row.metric][row.reference];low,high=np.percentile(difference,[2.5,97.5]);assert abs(low-row.percentile_2_5)<1e-11 and abs(high-row.percentile_97_5)<1e-11
        a=observed[(observed.scope==row.scope)&(observed.model==row.candidate)].iloc[0];b=observed[(observed.scope==row.scope)&(observed.model==row.reference)].iloc[0]
        assert abs((a[row.metric]-b[row.metric])-row.observed_difference)<1e-11
        assert abs(points.loc[20261111,row.candidate,row.scope][row.metric]-a[row.metric])<1e-11
    directions=pd.read_csv(OUT/'five-overlapping-split-directions.csv');assert len(directions)==350 and (directions.n_overlapping_splits==5).all();assert ((directions.wins+directions.ties+directions.losses)==5).all()
    calibration=pd.read_csv(OUT/'calibration-optimization-audit.csv');assert len(calibration)==200
    run.dump('readback-verification.json',dict(status='all_200_scores_70_ensembles_350_intervals_replayed',records=200,ensemble_cells=70,independent_metric_rows=140,bootstrap_rows=56000,interval_rows=350,direction_rows=350,ensemble_mean_max_abs=max(x['ensemble_mean_max_abs'] for x in checks),source_score_changes=0,source_freeze_unchanged=True,calibration_successes=int(calibration.success.sum()),calibration_residual_max=float(calibration.projected_gradient_inf.max()),review_identity='implementation validation only; not independent review of author budget runs',conditional_intervals=True,formal_team_adoption=False))
    files=[p for p in OUT.rglob('*') if p.is_file() and p.name!='deliverable-manifest.json']
    run.dump('deliverable-manifest.json',dict(files=[dict(path=p.relative_to(OUT).as_posix(),sha256=run.sha(p),bytes=p.stat().st_size,private='private' in p.parts) for p in files]))
    print(json.dumps(json.loads((OUT/'readback-verification.json').read_text())),flush=True)
if __name__=='__main__':
    with threadpool_limits(limits=2):main()
