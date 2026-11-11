import sys
sys.dont_write_bytecode=True
import hashlib,json,time
from pathlib import Path
import joblib,numpy as np,pandas as pd
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss,brier_score_loss,average_precision_score,roc_auc_score
from threadpoolctl import threadpool_limits
OUT=Path(__file__).resolve().parent;ROOT=OUT.parent;A=ROOT/'group-learning';B=ROOT/'objectives';KEY=['customer_unique_id','snapshot_date']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def objective(t,x,y):
    z=t[0]+x@t[1:];r=expit(z)-y;g=np.r_[r.sum(),x.T@r+t[1:]]
    return dict(sum_objective=float(np.sum(np.logaddexp(0,z)-y*z))+.5*float(t[1:]@t[1:]),sum_gradient_max=float(np.abs(g).max()),mean_gradient_max=float(np.abs(g).max()/len(y)))
def rank(f,p):return f[KEY].assign(s=p).sort_values(['s']+KEY,ascending=[False,True,True]).index.to_numpy()
def main():
    paths=[A/'private/features.npz',B/'private/fit-transformed-original.npz',A/'private/lr_unweighted-linear.npz',B/'private/LR-unweighted.joblib',A/'private/fit-keys-outcomes.csv',A/'private/cal-keys-outcomes.csv',A/'private/jan-keys-outcomes.csv',OUT/'plan.md',Path(__file__)]
    before={str(p):sha(p) for p in paths};x=np.load(B/'private/fit-transformed-original.npz');a=np.load(A/'private/features.npz')
    assert np.array_equal(x['X'],a['fit']);fit=x['X'];y=x['y'];assert (fit.shape,int(y.sum()))==((16928,34),169)
    ta=np.load(A/'private/lr_unweighted-linear.npz')['theta'];oldb=joblib.load(B/'private/LR-unweighted.joblib');tb=np.r_[oldb['model'].intercept_,oldb['model'].coef_.ravel()]
    began=time.perf_counter();model=LogisticRegression(C=1,solver='lbfgs',tol=1e-10,max_iter=2000,random_state=2026).fit(fit,y);seconds=time.perf_counter()-began
    t=np.r_[model.intercept_,model.coef_.ravel()];assert model.n_iter_[0]<2000
    joblib.dump(dict(model=model,preprocessor=oldb['preprocess'],features=oldb['fields'],purpose='single numerical convergence audit, not new model selection',parameters=model.get_params()),OUT/'private/strict-unweighted-LR.joblib',compress=3)
    result=dict(status='complete',single_new_fit=1,fit_n=16928,fit_events=169,train_seconds=seconds,n_iter=int(model.n_iter_[0]),parameters=model.get_params(),A_objective=objective(ta,fit,y),B_default_objective=objective(tb,fit,y),strict_objective=objective(t,fit,y),max_theta_diff_vs_A=float(np.max(np.abs(t-ta))),max_theta_diff_vs_B=float(np.max(np.abs(t-tb))),periods={},april_rows_parsed=0,input_sha256=before)
    for period in ['cal','jan']:
        f=pd.read_csv(A/f'private/{period}-keys-outcomes.csv',dtype={KEY[0]:'string'});xx=a[period];p=model.predict_proba(xx)[:,1];pa=expit(ta[0]+xx@ta[1:]);pb=expit(tb[0]+xx@tb[1:]);ys=f.y.to_numpy()
        score=f.copy();score['strict_probability']=p;score['P4A_probability']=pa;score['P4B_default_probability']=pb;score.to_csv(OUT/f'private/{period}-scores.csv',index=False,lineterminator='\n')
        rr=dict(logloss=float(log_loss(ys,p,labels=[0,1])),brier=float(brier_score_loss(ys,p)),AP=float(average_precision_score(ys,p)),AUC=float(roc_auc_score(ys,p)),max_prob_diff_vs_A=float(np.max(np.abs(p-pa))),max_prob_diff_vs_B=float(np.max(np.abs(p-pb))))
        k=2937 if period=='jan' else int(np.ceil(len(f)*.1));order=rank(f,p);sa=set(rank(f,pa)[:k]);sb=set(rank(f,pb)[:k]);ss=set(order[:k]);rr.update(k=k,hits=int(ys[order[:k]].sum()),selection_changed_vs_A=len(ss.symmetric_difference(sa)),selection_changed_vs_B=len(ss.symmetric_difference(sb)))
        if period=='jan':
            mask=f.cluster_id.eq(1).to_numpy();ff=f.loc[mask].reset_index(drop=True);rr['long79_hits']=int(ff.y.iloc[rank(ff,p[mask])[:79]].sum())
        result['periods'][period]=rr
    assert all(sha(p)==h for p,h in before.items())
    result['output_sha256']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='verification.json'}
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':
    with threadpool_limits(limits=2):main()
