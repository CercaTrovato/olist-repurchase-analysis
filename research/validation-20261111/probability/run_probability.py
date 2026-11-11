"""Bounded Oct/Jan P1; no April snapshot/label parsing; run python -B."""
import sys
sys.dont_write_bytecode = True
import hashlib, json, math, runpy, time
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import sklearn
from scipy.special import expit, logit
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, brier_score_loss,
    confusion_matrix, f1_score, log_loss, matthews_corrcoef, precision_recall_curve,
    roc_auc_score, roc_curve)
from sklearn.model_selection import StratifiedKFold
from threadpoolctl import threadpool_limits
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path(__file__).resolve().parent
ROOT=OUT.parent.parent
OLD=ROOT/'is6400-round3-20261111'
EXT=ROOT/'is6400-round3-extension-20261111'
KEY=['customer_unique_id','snapshot_date']
SEED=20261111
EPS=np.finfo(float).eps
INPUTS={}

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def note_input(p):
    INPUTS[str(p)]=sha(p)
    return p
def read(p):
    return pd.read_csv(note_input(p),dtype={KEY[0]:'string'},float_precision='round_trip')
def dump(v,p): p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def csv(v,p): v.to_csv(p,index=False,lineterminator='\n')
def load(p): return joblib.load(note_input(p))
def align(base,extra):
    cols=[c for c in extra if c not in KEY]
    z=base[KEY+['y','cluster_id']].merge(extra,on=KEY,how='outer',validate='one_to_one',indicator=True,suffixes=('','_source'))
    assert z._merge.eq('both').all()
    for c in ['y','cluster_id']:
        if c in cols: assert z[c].eq(z[c+'_source']).all()
    return z
def rank(frame,s): return frame[KEY].assign(score=s).sort_values(['score']+KEY,ascending=[False,True,True]).index.to_numpy()
def sigmoid_logit(p,offset=0): return expit(logit(np.clip(p,EPS,1-EPS))-offset)
def maxf1(y,p):
    pr,re,th=precision_recall_curve(y,p)
    f=2*pr[:-1]*re[:-1]/np.maximum(pr[:-1]+re[:-1],EPS)
    ix=np.flatnonzero(np.isclose(f,f.max(),rtol=0,atol=1e-15))[-1]
    return float(th[ix]),float(f[ix])
def loss_rows(y,p):
    p=np.clip(p,EPS,1-EPS)
    return np.column_stack([-(y*np.log(p)+(1-y)*np.log1p(-p)),(p-y)**2])
def scopes(f):
    return [('all',np.ones(len(f),dtype=bool))]+[(f'cluster_{g}'+('_long' if g==1 else ''),f.cluster_id.eq(g).to_numpy()) for g in [0,1,2]]
def basic(y,s,proper):
    r=dict(n=len(y),events=int(y.sum()),prevalence=float(y.mean()),AP=float(average_precision_score(y,s)),AUC=float(roc_auc_score(y,s)))
    if proper: r.update(logloss=float(log_loss(y,s,labels=[0,1])),brier=float(brier_score_loss(y,s)),mean_probability=float(np.mean(s)))
    return r
def classification(y,p,t):
    pred=(p>=t).astype(int)
    tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
    return dict(threshold=float(t),accuracy=float(accuracy_score(y,pred)),F1=float(f1_score(y,pred,zero_division=0)),MCC=float(matthews_corrcoef(y,pred)),tn=int(tn),fp=int(fp),fn=int(fn),tp=int(tp),predicted_positive=int(pred.sum()))
def wilson(k,n):
    if not n:return np.nan,np.nan
    z=1.959963984540054; p=k/n; denom=1+z*z/n
    c=(p+z*z/(2*n))/denom; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/denom
    return c-h,c+h

def main():
    start=time.perf_counter()
    assert (OUT/'frozen-plan.md').is_file()
    source=runpy.run_path(str(note_input(ROOT/'is6400-rfm-weighted-2x2-20261110/run_rfm_2x2.py')))
    note_input(source['TEAM']/'H02_candidate_v2.zip')
    train,jan=source['read_dev']()
    for which,path in [('train',ROOT/'is6400-local-round2-20261110/role-04/train_clusters.csv'),('jan',source['H05'])]:
        f=train if which=='train' else jan
        g=read(path)
        z=f.merge(g[KEY+['cluster_id']],on=KEY,how='outer',validate='one_to_one',indicator='_g')
        assert z._g.eq('both').all()
        z=z.drop(columns='_g').reset_index(drop=True)
        if which=='train':train=z
        else:jan=z
    assert (len(train),int(train.y.sum()),len(jan),int(jan.y.sum()))==(21160,211,29368,230)
    y=train.y.to_numpy(int); yj=jan.y.to_numpy(int)
    scores={}; oct_scores={}; kinds={}; artifacts={}; sources={}
    def import_scores(path,mapping,kind):
        z=align(jan,read(path))
        for old,new in mapping.items():
            value=z['score_'+old].to_numpy(float)
            assert np.isfinite(value).all()
            scores[new]=value; kinds[new]=kind.get(old,'probability');sources[new]=str(path)
    import_scores(OLD/'baselines/private/january-scores.csv',{m:m for m in ['recency','simpleMulti','LR3','LR8','weightedLR','groupOnly']},{'recency':'rank_only','simpleMulti':'rank_only'})
    import_scores(EXT/'context/private/january-scores.csv',{m:'context_'+m for m in ['seller','commerce','both']},{})
    import_scores(EXT/'nonlinear/private/january-scores.csv',{m:m for m in ['CB8-unweighted','CB8-balanced','CB14-unweighted','CB14-balanced']},{})
    import_scores(EXT/'strategies/private/january-scores.csv',{m:m for m in ['rank-W-LR3','rank-W-groupOnly','rank-W-delivery-review','group-shrink100']},{m:'rank_only' for m in ['rank-W-LR3','rank-W-groupOnly','rank-W-delivery-review']}|{'group-shrink100':'logit_only'})
    assert len(scores)==17
    existing=list(scores)
    # Recover Oct scores from Oct-fitted artifacts only, for display bin edges.
    for m in ['LR3','LR8','weightedLR']:
        a=load(OLD/f'baselines/private/{m}.joblib'); artifacts[m]=a
        oct_scores[m]=a['pipeline'].predict_proba(train[a['fields']])[:,1]
        assert np.max(np.abs(a['pipeline'].predict_proba(jan[a['fields']])[:,1]-scores[m]))<1e-12
    a=load(OLD/'baselines/private/groupOnly.joblib')
    def group_score(f,a):
        x=a['preprocessor'].transform(f[a['fields']]);x=np.column_stack([x,f.cluster_id.eq(1),f.cluster_id.eq(2)])
        return a['model'].predict_proba(x)[:,1]
    oct_scores['groupOnly']=group_score(train,a)
    assert np.max(np.abs(group_score(jan,a)-scores['groupOnly']))<1e-12
    ctx=read(EXT/'context/private/context-features.csv')
    tctx=train.merge(ctx,on=KEY,how='left',validate='one_to_one')
    jctx=jan.merge(ctx,on=KEY,how='left',validate='one_to_one')
    for name in ['seller','commerce','both']:
        a=load(EXT/f'context/private/{name}.joblib')
        def score_ctx(f):
            x=a['base_preprocessor'].transform(f[a['fields8']]);fields=a['context_fields']
            xx=a['imputer'].transform(f[fields]);xx=np.column_stack([xx,f[fields].isna().to_numpy(float)])
            x=np.column_stack([x,a['context_scaler'].transform(xx)])
            return a['model'].predict_proba(x)[:,1]
        oct_scores['context_'+name]=score_ctx(tctx)
        assert np.max(np.abs(score_ctx(jctx)-scores['context_'+name]))<1e-12
    cb=runpy.run_path(str(note_input(EXT/'nonlinear/run_nonlinear.py')))
    from catboost import CatBoostClassifier
    extras={}
    for period,f in [('october',train),('january',jan)]:
        path=OLD/('features/internal-october-features.csv' if period=='october' else 'features/internal-january-row-scores.csv')
        extra=read(path)
        extras[period]=f.merge(extra[KEY+cb['NEW']],on=KEY,how='left',validate='one_to_one')
    med=json.loads(note_input(EXT/'nonlinear/private/training-imputation-values.json').read_text())
    for m in cb['METHODS']:
        model=CatBoostClassifier().load_model(str(note_input(EXT/f'nonlinear/private/{m}.cbm')))
        fields=cb['OLD']+(cb['NEW'] if m.startswith('CB14') else [])
        xt,_=cb['prep'](extras['october'],fields,med[m]);xj,_=cb['prep'](extras['january'],fields,med[m])
        oct_scores[m]=model.predict_proba(xt)[:,1]
        assert np.max(np.abs(model.predict_proba(xj)[:,1]-scores[m]))<1e-12
    shrink=load(EXT/'strategies/private/group-shrink100.joblib')
    def shrink_logit(f):
        a=shrink;out=np.empty(len(f));glob=a['global_pipeline'].decision_function(f[a['fields']])-a['global_offset']
        for g,b in a['groups'].items():
            mask=f.cluster_id.eq(g).to_numpy()
            loc=b['pipeline'].decision_function(f.loc[mask,a['fields']])-b['log_prior_weight_ratio']
            out[mask]=(1-b['lambda'])*glob[mask]+b['lambda']*loc
        return out
    assert np.max(np.abs(shrink_logit(jan)-scores['group-shrink100']))<1e-12
    scores['group-shrink100-sigmoid']=expit(scores['group-shrink100'])
    oct_scores['group-shrink100-sigmoid']=expit(shrink_logit(train))
    kinds['group-shrink100-sigmoid']='probability_transformed_logit'
    sources['group-shrink100-sigmoid']='explicit sigmoid of saved corrected logit; no Jan fitting'
    # New controlled internal OOF comparison. Fold preprocessing is cloned and fitted inside folds.
    folds=np.full(len(train),-1,dtype=int);oof={m:np.empty(len(train)) for m in ['LR3','LR8','weightedLR']}
    fold_rows=[];skf=StratifiedKFold(n_splits=3,shuffle=True,random_state=SEED)
    for fold,(it,iv) in enumerate(skf.split(train,y)):
        folds[iv]=fold
        counts=dict(fold=fold,fit_n=len(it),fit_events=int(y[it].sum()),heldout_n=len(iv),heldout_events=int(y[iv].sum()))
        for m in ['LR3','LR8','weightedLR']:
            a=artifacts[m];model=clone(a['pipeline']);fields=a['fields']
            model.fit(train.iloc[it][fields],y[it]);oof[m][iv]=model.predict_proba(train.iloc[iv][fields])[:,1]
            joblib.dump({'pipeline':model,'fields':fields,'fold':fold,'train_indices':it,'validation_indices':iv},OUT/f'private/{m}-fold{fold}.joblib',compress=3)
            fold_rows.append(counts|dict(method=m,iterations=int(model.named_steps['model'].n_iter_.max())))
        print('OOF fold',fold,'done',flush=True)
    assert (folds>=0).all()
    offset=math.log((len(train)-y.sum())/y.sum())
    corrected_oof=np.empty(len(train))
    for fold,(it,iv) in enumerate(skf.split(train,y)):
        fold_offset=math.log((len(it)-y[it].sum())/y[it].sum())
        corrected_oof[iv]=sigmoid_logit(oof['weightedLR'][iv],fold_offset)
    oof['weightedLR-prior-corrected']=corrected_oof
    scores['weightedLR-prior-corrected']=sigmoid_logit(scores['weightedLR'],offset)
    kinds['weightedLR-prior-corrected']='probability_prior_corrected'
    sources['weightedLR-prior-corrected']='Oct class-weight ratio analytic correction'
    z=logit(np.clip(oof['weightedLR'],EPS,1-EPS)).reshape(-1,1)
    platt=LogisticRegression(C=1e6,max_iter=2000,random_state=SEED,class_weight=None,solver='lbfgs').fit(z,y)
    oof['weightedLR-oof-Platt']=platt.predict_proba(z)[:,1]
    scores['weightedLR-oof-Platt']=platt.predict_proba(logit(np.clip(scores['weightedLR'],EPS,1-EPS)).reshape(-1,1))[:,1]
    kinds['weightedLR-oof-Platt']='probability_oof_calibrated'
    sources['weightedLR-oof-Platt']='Oct OOF natural-prevalence Platt; Jan untouched'
    prevalence=float(y.mean())
    scores['constant-Oct']=np.full(len(jan),prevalence);oof['constant-Oct']=np.full(len(train),prevalence)
    kinds['constant-Oct']='probability_constant';sources['constant-Oct']='211/21160'
    # Constant OOF display uses common Oct baseline; no model learning and not used as CV skill claim.
    for m in oof:oct_scores[m]=oof[m]
    proper=[m for m in scores if kinds[m].startswith('probability')]
    assert len(scores)==21 and len(proper)==15
    thresholds={m:maxf1(y,p) for m,p in oof.items()}
    csv(pd.DataFrame([dict(method=m,threshold=v[0],oct_oof_development_F1=v[1],rule='maximum F1; highest threshold on tie',platt_same_oof_labels=m=='weightedLR-oof-Platt') for m,v in thresholds.items()]),OUT/'thresholds-october.csv')
    csv(pd.DataFrame(fold_rows),OUT/'october-fold-audit.csv')
    predictor=dict(kind='P1-LR-probability-suite',base_models=artifacts,platt=platt,prior_log_weight_ratio=offset,constant=prevalence,
        thresholds={m:v[0] for m,v in thresholds.items()},features={m:a['fields'] for m,a in artifacts.items()},calibration_input='logit(clipped weightedLR predict_proba)',clip_epsilon=EPS,
        cv={'n_splits':3,'shuffle':True,'random_state':SEED},train_snapshot='2017-10-01',validation_snapshot='2018-01-01')
    joblib.dump(predictor,OUT/'private/lr-probability-predictors.joblib',compress=3)
    ps=jan[KEY+['cluster_id','y']].copy()
    for m,p in scores.items():ps['score_'+m]=p
    csv(ps,OUT/'private/january-all-scores.csv')
    ot=train[KEY+['cluster_id','y']].assign(fold=folds)
    for m,p in oof.items():ot['score_'+m]=p
    csv(ot,OUT/'private/october-oof-scores.csv')
    csv(pd.DataFrame([dict(method=m,score_kind=kinds[m],probability_eligible=m in proper,original17=m in existing,source=sources[m],oct_bin_source='Oct OOF' if m in oof else ('Oct full-fit, bin edges only' if m in proper else 'not probability')) for m in scores]),OUT/'method-schema.csv')
    # All methods get ranking; only actual probability candidates get proper and class metrics.
    metrics=[];classes=[];strategy=[];curves=[];bins=[];edges_rows=[]
    for scope,mask in scopes(jan):
        frame=jan.loc[mask].reset_index(drop=True);ys=yj[mask]
        for m,s in scores.items():
            p=s[mask];isprob=m in proper
            metrics.append(dict(scope=scope,method=m,probability_eligible=isprob,**basic(ys,p,isprob)))
            if isprob:
                classes.append(dict(scope=scope,method=m,rule='fixed_0.5',**classification(ys,p,.5)))
                if m in thresholds:classes.append(dict(scope=scope,method=m,rule='Oct_OOF_maxF1',**classification(ys,p,thresholds[m][0])))
                edge=np.quantile(oct_scores[m],np.linspace(0,1,11))
                assigned=np.searchsorted(edge[1:-1],p,side='right')
                for b in range(10):
                    ib=assigned==b;n=int(ib.sum());ev=int(ys[ib].sum());lo,hi=wilson(ev,n)
                    bins.append(dict(scope=scope,method=m,bin=b+1,oct_quantile_lower=float(edge[b]),oct_quantile_upper=float(edge[b+1]),assignment_lower='-inf' if b==0 else float(edge[b]),assignment_upper='+inf' if b==9 else float(edge[b+1]),n=n,events=ev,mean_probability=float(p[ib].mean()) if n else np.nan,observed_rate=ev/n if n else np.nan,wilson_low=lo,wilson_high=hi))
                assert sum(r['n'] for r in bins[-10:])==len(ys) and sum(r['events'] for r in bins[-10:])==ys.sum()
            if scope=='all' or scope=='cluster_1_long':
                k=2937 if scope=='all' else 79
                chosen=rank(frame,p)[:k];h=int(ys[chosen].sum())
                strategy.append(dict(scope=scope,method=m,n=len(ys),events=int(ys.sum()),k=k,hits=h,precision=h/k,recall=h/ys.sum(),AP=float(average_precision_score(ys,p)),probability_eligible=isprob))
            # Complete PR/ROC thresholds per method and scope, including rank-only controls.
            pr,re,th=precision_recall_curve(ys,p,drop_intermediate=False)
            curves.extend(dict(scope=scope,method=m,curve='PR',x=float(r),y=float(q),threshold=float(t) if np.isfinite(t) else np.nan) for q,r,t in zip(pr,re,np.r_[th,np.nan]))
            fpr,tpr,th=roc_curve(ys,p,drop_intermediate=False)
            curves.extend(dict(scope=scope,method=m,curve='ROC',x=float(a),y=float(b),threshold=float(t) if np.isfinite(t) else np.nan) for a,b,t in zip(fpr,tpr,th))
        print('metrics scope',scope,'done',flush=True)
    metrics=pd.DataFrame(metrics);bins=pd.DataFrame(bins)
    csv(metrics,OUT/'january-metrics-all-scopes.csv');csv(pd.DataFrame(classes),OUT/'january-threshold-classification.csv')
    csv(pd.DataFrame(strategy),OUT/'strategy-top10-long79.csv');csv(bins,OUT/'calibration-all-bins.csv')
    csv(pd.DataFrame(curves),OUT/'all-pr-roc-curves.csv')
    # Internal OOF metrics are development diagnostics; Platt is not nested CV.
    om=[]
    for scope,mask in scopes(train):
        for m,p in oof.items():om.append(dict(scope=scope,method=m,platt_nested_cv=False,**basic(y[mask],p[mask],True)))
    csv(pd.DataFrame(om),OUT/'october-oof-development-metrics.csv')
    # Conditional paired fixed-score bootstrap. Common counts per scope across every comparison.
    candidates=['LR3','LR8','weightedLR','weightedLR-prior-corrected','weightedLR-oof-Platt','group-shrink100-sigmoid','CB8-unweighted','CB14-unweighted']
    references=['constant-Oct','LR8','weightedLR']
    intervals=[];rep_frames=[]
    for si,(scope,mask) in enumerate(scopes(jan)):
        ys=yj[mask];n=len(ys);rng=np.random.default_rng(SEED+si)
        pairs=[(m,r) for m in candidates for r in references if m!=r]
        errors={m:loss_rows(ys,scores[m][mask]) for m in set(candidates+references)}
        d=np.column_stack([(errors[m]-errors[r])[:,j] for m,r in pairs for j in [0,1]])
        reps=np.empty((2000,d.shape[1]))
        for b in range(0,2000,50):
            cnt=rng.multinomial(n,np.full(n,1/n),size=min(50,2000-b))
            reps[b:b+len(cnt)]=cnt@d/n
        for pi,(m,r) in enumerate(pairs):
            for j,metric in enumerate(['logloss','brier']):
                x=reps[:,pi*2+j];low,high=np.percentile(x,[2.5,97.5])
                intervals.append(dict(scope=scope,method=m,reference=r,metric=metric,n=n,events=int(ys.sum()),observed_difference=float(d[:,pi*2+j].mean()),bootstrap_mean=float(x.mean()),ci_low=float(low),ci_high=float(high),replicates=2000,seed=SEED+si))
        rf=pd.DataFrame(reps,columns=[m+'__minus__'+r+'__'+metric for m,r in pairs for metric in ['logloss','brier']]);rf.insert(0,'replicate',np.arange(1,2001));rf.insert(0,'scope',scope);rep_frames.append(rf)
        print('bootstrap',scope,'done',flush=True)
    csv(pd.DataFrame(intervals),OUT/'bootstrap-loss-differences.csv');csv(pd.concat(rep_frames,ignore_index=True),OUT/'bootstrap-loss-replicates.csv')
    # Public figures show only aggregate information; full curves/bins stay inspectable in CSV.
    selected=['constant-Oct','LR8','weightedLR','weightedLR-prior-corrected','weightedLR-oof-Platt','CB14-unweighted']
    colors=dict(zip(selected,['#777777','#2166ac','#b2182b','#ef8a62','#1b7837','#762a83']))
    fig,axes=plt.subplots(2,2,figsize=(13,10))
    for ax,(scope,mask) in zip(axes.ravel(),scopes(jan)):
        for m in selected:
            b=bins.loc[(bins.scope==scope)&(bins.method==m)&(bins.n>0)]
            ax.plot(b.mean_probability,b.observed_rate,'o-',label=m,color=colors[m],lw=1,ms=4)
        ax.plot([0,1],[0,1],'k--',lw=.7);ax.set(title=f'{scope}: N={mask.sum()}, events={yj[mask].sum()}',xlabel='Mean predicted probability (Oct-defined bins)',ylabel='Observed January event rate');ax.set_xlim(-.01,.9);ax.set_ylim(-.003,.15);ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=8);fig.suptitle('Natural-distribution calibration: all customers, no top-K filtering')
    fig.text(.05,.015,'Each point uses an Oct-defined decile. Empty bins retained in CSV. Bin N/events and Wilson intervals: calibration-all-bins.csv.\nJanuary was already seen; fixed models; this is not a new unseen-time test.',fontsize=9);fig.tight_layout(rect=[0,.05,1,.96])
    for ext in ['png','svg']:fig.savefig(OUT/f'figures/calibration-probability-zoom.{ext}',dpi=170)
    for ax in axes.ravel():ax.set_xlim(-.01,1.01);ax.set_ylim(-.01,1.01)
    for ext in ['png','svg']:fig.savefig(OUT/f'figures/calibration-probability.{ext}',dpi=170)
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(13,5))
    for ax,metric in zip(axes,['logloss','brier']):
        x=np.arange(len(selected));width=.18
        for i,(scope,mask) in enumerate(scopes(jan)):
            tab=metrics.loc[metrics.scope.eq(scope)].set_index('method')
            ax.bar(x+(i-1.5)*width,[tab.loc[m,metric] for m in selected],width,label=scope)
        ax.set_xticks(x,selected,rotation=25,ha='right');ax.set(title=metric+' (lower is better)',ylabel='Natural-distribution loss');ax.grid(axis='y',alpha=.2)
    axes[0].legend(fontsize=8);fig.tight_layout()
    for ext in ['png','svg']:fig.savefig(OUT/f'figures/proper-loss-comparison.{ext}',dpi=170)
    plt.close(fig)
    input_after={p:sha(p) for p in INPUTS}
    assert INPUTS==input_after,'source changed during run'
    metadata=dict(status='complete',elapsed_seconds=time.perf_counter()-start,april_snapshot_rows_parsed=0,april_label_rows_parsed=0,train={'n':len(train),'events':int(y.sum())},january={'n':len(jan),'events':int(yj.sum())},original_methods=17,total_methods=21,probability_methods=15,
        seed=SEED,bootstrap_replicates=2000,cv={'folds':3,'preprocess_fit_inside_fold':True},jan_used_for_fitting_calibrator_or_threshold=False,
        platt={'coef':float(platt.coef_[0,0]),'intercept':float(platt.intercept_[0]),'C':1e6,'class_weight':None,'input':'Oct OOF raw weightedLR logit','oof_metric_caveat':'calibrator fit on same OOF labels; not nested validation'},prior_log_weight_ratio=offset,
        probability_clip_epsilon=EPS,calibration_bin_edges='new LR family: Oct OOF; existing artifacts: Oct full-fit scores, for boundaries only; 10 bins including empty',bootstrap_unit='paired customer within January scope, fixed models/scores, not retraining or new time generalization',
        package_versions={'python':sys.version.split()[0],'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__},input_sha256=INPUTS,script_sha256=sha(Path(__file__)),plan_sha256=sha(OUT/'frozen-plan.md'))
    metadata['output_sha256']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name not in ['verification.json','README.md']}
    dump(metadata,OUT/'verification.json')
    print(metrics.loc[metrics.scope.eq('all')].to_string(index=False),flush=True)
    print('COMPLETE seconds',metadata['elapsed_seconds'],flush=True)

if __name__=='__main__':
    with threadpool_limits(limits=2):main()
