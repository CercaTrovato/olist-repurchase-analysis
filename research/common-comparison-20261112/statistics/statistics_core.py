"""Schema-independent frozen statistics primitives; never fits a model.

The input adapter is deliberately separate and must be agreed with the producer.
Canonical probability ensembles use exactly the same score for loss/AP/policy.
"""
from __future__ import annotations
from dataclasses import dataclass
import itertools
import numpy as np
import pandas as pd

KEY=['customer_unique_id','snapshot_date']
LOWER_IS_BETTER={'logloss','brier','ece10'}
WIN_METRICS=LOWER_IS_BETTER|{'AP','AUC','hits','precision','recall'}
EPS=np.finfo(np.float64).eps

def check_cohort(frame:pd.DataFrame,expected_n:int|None=None,expected_events:int|None=None):
    required=KEY+['y','cluster_id']
    if not set(required)<=set(frame):raise ValueError('Missing canonical cohort columns')
    if frame.duplicated(KEY).any():raise ValueError('Duplicate customer snapshot keys')
    if not frame.y.isin([0,1]).all():raise ValueError('Nonbinary outcomes')
    if expected_n is not None and len(frame)!=expected_n:raise ValueError('Unexpected cohort size')
    if expected_events is not None and int(frame.y.sum())!=expected_events:raise ValueError('Unexpected event count')

def canonical_ensemble(frames:list[pd.DataFrame],probability_column='calibrated_probability'):
    """One-to-one keyed mean(p), never mean(loss) or mean(logit) for main policy."""
    if not frames:raise ValueError('Empty model cell')
    normalized=[]
    for f in frames:
        check_cohort(f)
        g=f.sort_values(KEY).reset_index(drop=True)
        p=g[probability_column].to_numpy(np.float64)
        if not np.isfinite(p).all() or ((p<0)|(p>1)).any():raise ValueError('Invalid probabilities')
        normalized.append(g)
    first=normalized[0]
    for g in normalized[1:]:
        if not first[KEY+['y','cluster_id']].equals(g[KEY+['y','cluster_id']]):raise ValueError('Ensemble keys/outcomes/group mismatch')
    result=first[KEY+['y','cluster_id']].copy()
    result['ensemble_probability']=np.mean(np.vstack([g[probability_column].to_numpy(np.float64) for g in normalized]),axis=0,dtype=np.float64)
    if all('raw_logit' in g for g in normalized):
        result['diagnostic_mean_raw_logit']=np.mean(np.vstack([g.raw_logit.to_numpy(np.float64) for g in normalized]),axis=0,dtype=np.float64)
    result.attrs.update(n_models=len(frames),main_rule='mean(calibrated probability)',diagnostic_rule='mean(raw logit), ranking-only')
    return result

@dataclass
class FixedScoreEvaluator:
    """Exact weighted empirical metrics and top-K under replicated customers.

    Counts represent resampled copies, not independent newly observed people.
    AP/AUC preserve probability ties; top-K uses the frozen key tie-break.
    """
    frame:pd.DataFrame
    probability:np.ndarray

    def __post_init__(self):
        self.frame=self.frame.reset_index(drop=True)
        check_cohort(self.frame)
        self.p=np.asarray(self.probability,dtype=np.float64)
        if self.p.shape!=(len(self.frame),):raise ValueError('Score length mismatch')
        if not np.isfinite(self.p).all() or ((self.p<0)|(self.p>1)).any():raise ValueError('Score is not a probability')
        self.y=self.frame.y.to_numpy(np.int64)
        self.long=self.frame.cluster_id.eq(1).to_numpy(np.int64)
        self.order=np.lexsort((self.frame.snapshot_date.astype(str).to_numpy(),self.frame.customer_unique_id.astype(str).to_numpy(),-self.p))
        ordered=self.p[self.order]
        self.group_starts=np.r_[0,1+np.flatnonzero(ordered[1:]!=ordered[:-1])]
        clipped=np.clip(self.p,EPS,1-EPS)
        self.loss=-self.y*np.log(clipped)-(1-self.y)*np.log1p(-clipped)
        self.brier=(self.p-self.y)**2

    def empirical_metrics(self,counts:np.ndarray|None=None):
        w=np.ones(len(self.y),dtype=np.int64) if counts is None else np.asarray(counts,dtype=np.int64)
        if w.shape!=self.y.shape or (w<0).any():raise ValueError('Invalid replicate counts')
        n=int(w.sum());positive=int(w@self.y);negative=n-positive
        if n==0:raise ValueError('Empty empirical replicate')
        ordered_w=w[self.order];ordered_y=self.y[self.order]
        group_n=np.add.reduceat(ordered_w,self.group_starts)
        group_pos=np.add.reduceat(ordered_w*ordered_y,self.group_starts)
        group_neg=group_n-group_pos
        cum_n=np.cumsum(group_n);cum_pos=np.cumsum(group_pos);cum_neg=np.cumsum(group_neg)
        prec=np.divide(cum_pos,cum_n,out=np.zeros_like(cum_pos,dtype=float),where=cum_n>0)
        ap=float(np.sum(group_pos*prec)/positive) if positive else np.nan
        concordance=np.sum(group_pos*(negative-cum_neg)+.5*group_pos*group_neg)
        auc=float(concordance/(positive*negative)) if positive and negative else np.nan
        return dict(n=n,events=positive,prevalence=positive/n,logloss=float(w@self.loss/n),brier=float(w@self.brier/n),AP=ap,AUC=auc)

    def topk(self,k:int,counts:np.ndarray|None=None):
        w=np.ones(len(self.y),dtype=np.int64) if counts is None else np.asarray(counts,dtype=np.int64)
        if w.shape!=self.y.shape or (w<0).any() or not 0<k<=w.sum():raise ValueError('Invalid counts or K')
        ordered_w=w[self.order];cum=np.cumsum(ordered_w)
        boundary=int(np.searchsorted(cum,k,side='left'));before=int(cum[boundary-1]) if boundary else 0
        chosen_last=k-before;prefix=self.order[:boundary];last=self.order[boundary]
        hits=int(w[prefix]@self.y[prefix]+chosen_last*self.y[last])
        long_selected=int(w[prefix]@self.long[prefix]+chosen_last*self.long[last])
        long_hits=int(w[prefix]@(self.y[prefix]*self.long[prefix])+chosen_last*self.y[last]*self.long[last])
        events=int(w@self.y)
        return dict(k=int(k),hits=hits,precision=hits/k,recall=hits/events if events else np.nan,
                    global_long_selected=long_selected,global_long_hits=long_hits,global_long_share=long_selected/k)

    def selected_key_set(self,k:int):
        if not 0<k<=len(self.y):raise ValueError('Invalid unique-customer K')
        f=self.frame.iloc[self.order[:k]]
        return set(map(tuple,f[KEY].to_numpy()))

def paired_customer_bootstrap(cohort:pd.DataFrame,probabilities:dict[str,np.ndarray],scope:str,
                              k:int,replicates=2000,seed=2026111201):
    """Same multinomial counts for all models in each fixed-scope replicate.

    This reranks a pool of empirical customer copies. It does not deduplicate
    repeated people or retrain models. The long scope is bootstrapped separately.
    """
    check_cohort(cohort)
    mask=np.ones(len(cohort),dtype=bool) if scope=='all' else cohort.cluster_id.eq(1).to_numpy() if scope=='long' else None
    if mask is None:raise ValueError('Scope must be all or long')
    frame=cohort.loc[mask].reset_index(drop=True)
    evaluators={name:FixedScoreEvaluator(frame,np.asarray(p,dtype=float)[mask]) for name,p in probabilities.items()}
    n=len(frame);rng=np.random.default_rng(seed);population_probability=np.full(n,1/n)
    observed=[]
    for name,ev in evaluators.items():observed.append(dict(scope=scope,model=name,**ev.empirical_metrics(),**ev.topk(k)))
    rows=[]
    for b in range(replicates):
        counts=rng.multinomial(n,population_probability)
        for name,ev in evaluators.items():
            rows.append(dict(scope=scope,replicate=b+1,model=name,seed=seed,**ev.empirical_metrics(counts),**ev.topk(k,counts)))
    return pd.DataFrame(observed),pd.DataFrame(rows)

def paired_intervals(observed:pd.DataFrame,replicates:pd.DataFrame,
                     contrasts:list[tuple[str,str,str]],metrics:list[str]):
    """Differences are candidate-reference; lower loss is a negative difference."""
    rows=[]
    for scope in observed.scope.unique():
        obs=observed.loc[observed.scope.eq(scope)].set_index('model')
        wide={m:replicates.loc[replicates.scope.eq(scope)].pivot(index='replicate',columns='model',values=m) for m in metrics}
        for candidate,reference,kind in contrasts:
            if candidate not in obs.index or reference not in obs.index:raise ValueError('Unknown planned contrast')
            for metric in metrics:
                d=(wide[metric][candidate]-wide[metric][reference]).to_numpy(float)
                finite=d[np.isfinite(d)]
                if not len(finite):raise ValueError('No finite bootstrap differences')
                lo,hi=np.percentile(finite,[2.5,97.5])
                rows.append(dict(scope=scope,candidate=candidate,reference=reference,contrast=kind,metric=metric,
                    observed_difference=float(obs.loc[candidate,metric]-obs.loc[reference,metric]),bootstrap_mean=float(finite.mean()),
                    percentile_2_5=float(lo),percentile_97_5=float(hi),requested_replicates=len(d),finite_replicates=len(finite),
                    interpretation='lower_is_better' if metric in LOWER_IS_BETTER else 'higher_is_better' if metric in WIN_METRICS else 'descriptive_no_preferred_direction'))
    return pd.DataFrame(rows)

def seed_aggregate(rows:pd.DataFrame,identity_columns:list[str],metric_columns:list[str]):
    """Aggregate within one split first. n=1 deterministic LR has SD=NaN."""
    out=[]
    for group,part in rows.groupby(identity_columns,dropna=False,sort=True):
        values=group if isinstance(group,tuple) else (group,)
        row=dict(zip(identity_columns,values));row['n_models']=len(part)
        for metric in metric_columns:
            p=part[metric].to_numpy(float)
            row.update({metric+'_mean':float(np.mean(p)),metric+'_sd':float(np.std(p,ddof=1)) if len(p)>1 else np.nan,
                        metric+'_min':float(np.min(p)),metric+'_max':float(np.max(p))})
        out.append(row)
    return pd.DataFrame(out)

def split_direction_summary(split_means:pd.DataFrame,identity_columns:list[str],metric_column:str,
                            metric_name:str,expected_splits=5,tolerance=1e-12):
    """Descriptive counts only; never a binomial or independent-time test."""
    rows=[]
    for group,part in split_means.groupby(identity_columns,dropna=False,sort=True):
        if part.split_id.duplicated().any():raise ValueError('Aggregate seeds inside split before counting splits')
        if len(part)!=expected_splits:raise ValueError('Incomplete split cell: record failure rather than silently drop it')
        d=part[metric_column].to_numpy(float)
        if not np.isfinite(d).all():raise ValueError('Nonfinite split effect')
        improvement=-d if metric_name in LOWER_IS_BETTER else d
        tol=0 if metric_name=='hits' else tolerance
        win=int((improvement>tol).sum());tie=int((np.abs(improvement)<=tol).sum());loss=len(d)-win-tie
        values=group if isinstance(group,tuple) else (group,)
        rows.append(dict(zip(identity_columns,values))|dict(metric=metric_name,n_overlapping_splits=len(d),
            difference_min=float(d.min()),difference_median=float(np.median(d)),difference_max=float(d.max()),
            wins=win,ties=tie,losses=loss,win_fraction=win/expected_splits,
            uncertainty='descriptive overlapping training perturbations, not independent periods'))
    return pd.DataFrame(rows)

def selection_pair_diagnostic(a:FixedScoreEvaluator,b:FixedScoreEvaluator,k:int):
    sa=a.selected_key_set(k);sb=b.selected_key_set(k)
    aa=a.topk(k);bb=b.topk(k)
    return dict(k=k,jaccard=len(sa&sb)/len(sa|sb),symmetric_difference=len(sa^sb),
                hits_a=aa['hits'],hits_b=bb['hits'],hits_difference=bb['hits']-aa['hits'],
                global_long_selected_a=aa['global_long_selected'],global_long_selected_b=bb['global_long_selected'])

def unique_pair_indices(labels):
    return itertools.combinations(sorted(labels,key=str),2)
