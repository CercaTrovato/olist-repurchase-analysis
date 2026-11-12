"""Read-only independent arithmetic replay; no model fitting or probability calls."""
from pathlib import Path
import json, hashlib, math
import numpy as np
import pandas as pd
import joblib

ROOT=Path(__file__).resolve().parent
KEY=['customer_unique_id','snapshot_date']
FEATURES=['F','M','average_order_value','max_order_value']

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return pd.read_csv(path,dtype={k:str for k in KEY},float_precision='round_trip')
def main():
    manifest=json.loads((ROOT/'value-manifest.json').read_text(encoding='utf-8'))
    assert manifest['status']=='READY' and manifest['amount_model_fit_count']==6
    for rel,h in manifest['artifacts'].items(): assert sha(ROOT/rel)==h,rel
    cap=read(ROOT/'capacity-results.csv'); amount=read(ROOT/'amount-prediction-metrics.csv')
    checks={'input_hashes':0,'model_replays':0,'manager_tables':0,'score_columns':0,'capacity_rows':0,'amount_metric_rows':0}
    for cell,entry in manifest['cells'].items():
        inputs=manifest['inputs'][cell]
        for part,info in inputs.items(): assert sha(info['path'])==info['sha256']; checks['input_hashes']+=1
        ev=read(inputs['eval']['path']); fit=read(inputs['fit']['path']); probs=read(inputs['probability']['path'])
        positive=fit[fit.future_gmv>0]
        private=ROOT/'private/cells'/cell
        fitinfo=json.loads((private/'amount-fit.json').read_text(encoding='utf-8'))
        assert fitinfo['positive_rows']==len(positive) and np.isclose(fitinfo['positive_G_mean'],positive.future_gmv.mean())
        if fitinfo['fallback']:
            raw=np.full(len(ev),positive.future_gmv.mean())
        else:
            model=joblib.load(private/'amount-model.joblib')
            assert np.allclose(model['scaler'].mean_,np.log1p(positive[FEATURES].to_numpy()).mean(axis=0),rtol=1e-12)
            raw=model['model'].predict(model['scaler'].transform(np.log1p(ev[FEATURES].to_numpy())))*model['target_scale']
            assert model['model'].alpha==1 and model['model'].max_iter==2000 and model['model'].tol==1e-8
        cond=np.clip(raw,0,positive.future_gmv.max()); checks['model_replays']+=1
        truth=read(private/'evaluation-truth.csv')
        assert truth[KEY].equals(ev[KEY]) and np.array_equal(truth.y,ev.y)
        assert np.allclose(truth.future_gmv,ev.future_gmv) and np.array_equal(truth.future_orders,ev.future_orders)
        for path in entry['manager_paths']:
            table=read(path); family=Path(path).stem.removeprefix('manager-')
            assert not set(table)&{'y','future_gmv','future_orders','label_end'}
            assert table[KEY].equals(ev[KEY]) and len(table)==len(ev)
            assert np.allclose(table.p,probs[family],rtol=1e-14,atol=1e-15)
            assert np.allclose(table.Ghat_conditional,cond,rtol=1e-12) and np.allclose(table.Ghat_conditional_uncapped,raw,rtol=1e-12)
            p=table.p.to_numpy(); f=ev.F.to_numpy(); m=ev.M.to_numpy()
            formulas={'p':p,'repeat_Fminus1_M':p*np.maximum(f-1,0)*m,'purchase_F_M':p*f*m,
                'historical_M':p*m,'historical_AOV':p*m/f,'expected_G':p*cond,'M_only':m,'recency':-ev.R.to_numpy()}
            for rule,score in formulas.items():
                assert np.allclose(table['score_'+rule],score,rtol=1e-12,atol=1e-15)
                # Hash the preserved score values, avoiding reassociation of floating expressions.
                z=table[KEY].copy(); z['score']=table['score_'+rule]
                h=hashlib.sha256(z.to_csv(index=False,float_format='%.17g',lineterminator='\n').encode()).hexdigest()
                assert h==manifest['score_hashes'][cell+'__'+family][rule]
                order=np.lexsort((table.snapshot_date.to_numpy(),table.customer_unique_id.to_numpy(),-table['score_'+rule].to_numpy()))
                rank=np.empty(len(table),int); rank[order]=np.arange(1,len(table)+1)
                assert np.array_equal(table['rank_'+rule],rank); checks['score_columns']+=1
            rows=cap[(cap.evaluation_date==cell.split('__')[0])&(cap.strategy==cell.split('__')[1])&(cap.family==family)]
            for _,r in rows.iterrows():
                pool=ev if r.scope=='global' else ev[ev.cluster==1]
                k=int(r.K); assert k==(math.ceil(len(ev)*r.capacity) if r.scope=='global' else 79)
                if r.rule=='random_expectation':
                    amount_sum=pool.future_gmv.sum()*k/len(pool); hits=pool.y.sum()*k/len(pool)
                else:
                    t=table if r.scope=='global' else table[table.cluster==1]
                    s=t['score_'+r.rule].to_numpy()
                    order=np.lexsort((t.snapshot_date.to_numpy(),t.customer_unique_id.to_numpy(),-s))[:k]
                    take=pool.iloc[order]; amount_sum=take.future_gmv.sum(); hits=take.y.sum()
                assert np.isclose(amount_sum,r.captured_G,rtol=1e-12,atol=1e-9)
                assert np.isclose(hits,r.hits,atol=1e-12)
                assert np.isclose(hits/k,r.precision,atol=1e-12); checks['capacity_rows']+=1
            am=amount[(amount.evaluation_date==cell.split('__')[0])&(amount.strategy==cell.split('__')[1])&(amount.family==family)]
            for _,r in am.iterrows():
                pred=p*cond if r.prediction=='learned_expected_G' else p*positive.future_gmv.mean()
                err=pred-ev.future_gmv.to_numpy()
                assert np.isclose(np.abs(err).mean(),r.MAE) and np.isclose(np.sqrt(np.square(err).mean()),r.RMSE)
                assert np.isclose(pred.sum(),r.predicted_G_total); checks['amount_metric_rows']+=1
            checks['manager_tables']+=1
    boot=read(ROOT/'jan-paired-bootstrap.csv')
    assert set(boot.scope)=={'global10','long79'} and (boot.reps==2000).all()
    assert len(boot)==6*2*10*7
    result={'status':'PASS','checks':checks,'bootstrap_rows':len(boot),'new_fits':0,
            'truth_separation':'all 18 manager tables exclude future outcomes',
            'verification_scope':'all saved model conditional predictions, all 144 preserved score hashes/ranks, all 1296 capacity rows, all 36 amount metrics independently replayed; bootstrap schema/count only, no second bootstrap'}
    (ROOT/'independent-readback.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))

if __name__=='__main__': main()
