"""Independent raw three-table outcome and rolling-split readback verification."""
import hashlib,json
from pathlib import Path
import numpy as np,pandas as pd
OUT=Path(__file__).resolve().parent
RAW=Path('D:/上课资料/CityU/IS6400_Business_Data_Analytics/assignment/graded/A06-group-project/work/data/raw')
KEY=['customer_unique_id','snapshot_date']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    m=json.loads((OUT/'data-manifest.json').read_text());assert m['status']=='READY'
    dtypes={c:'string' for c in KEY+m['categorical_fields']}
    # Independently derive eligible order amounts from raw prices and match customers.
    o=pd.read_csv(RAW/'olist_orders_dataset.csv',dtype='string',usecols=['order_id','customer_id','order_approved_at'])
    c=pd.read_csv(RAW/'olist_customers_dataset.csv',dtype='string',usecols=['customer_id','customer_unique_id'])
    i=pd.read_csv(RAW/'olist_order_items_dataset.csv',dtype={'order_id':'string'},usecols=['order_id','price'])
    o.order_approved_at=pd.to_datetime(o.order_approved_at,errors='coerce')
    amounts=i.groupby('order_id').price.sum().rename('independent_amount')
    e=o.merge(c,on='customer_id',validate='many_to_one').merge(amounts,on='order_id',validate='one_to_one')
    e=e.loc[e.order_approved_at.notna()&e.independent_amount.gt(0)&e.customer_unique_id.notna()]
    assert e.order_id.is_unique
    snap={};outcomes=[];split_checks=[]
    for date,s in m['snapshots'].items():
        p=OUT/s['path'];assert sha(p)==s['sha256']
        f=pd.read_csv(p,dtype=dtypes,float_precision='round_trip');snap[date]=f
        t=pd.Timestamp(date);end=t+pd.Timedelta(days=90)
        hist=e.loc[e.order_approved_at.ge(t-pd.DateOffset(months=6))&e.order_approved_at.lt(t)]
        assert set(hist.customer_unique_id)==set(f.customer_unique_id)
        target=e.loc[e.order_approved_at.ge(t)&e.order_approved_at.lt(end)&e.customer_unique_id.isin(f.customer_unique_id)]
        assert target.order_approved_at.lt(pd.Timestamp('2018-04-01')).all()
        a=target.groupby('customer_unique_id').agg(G=('independent_amount','sum'),N=('order_id','nunique'))
        z=f.merge(a,on='customer_unique_id',how='left',validate='one_to_one').fillna({'G':0,'N':0})
        assert np.allclose(z.future_gmv,z.G,rtol=1e-12,atol=1e-9)
        assert z.future_orders.eq(z.N).all() and z.y.eq(z.N.gt(0).astype(int)).all()
        outcomes.append(dict(snapshot_date=date,rows=len(z),positive_rows=int(z.y.sum()),target_orders=len(target),target_gmv=float(target.independent_amount.sum()),max_gmv_abs_error=float((z.future_gmv-z.G).abs().max()),all_targets_before_2018_04_01=True))
    for cell,v in m['cells'].items():
        dfs={}
        for role in ['fit','cal','eval']:
            p=OUT/v[role]['path'];assert sha(p)==v[role]['sha256']
            dfs[role]=pd.read_csv(p,dtype=dtypes,float_precision='round_trip')
        a,b,c=dfs['fit'],dfs['cal'],dfs['eval'];t=pd.Timestamp(v['eval_date'])
        assert set(a.customer_unique_id).isdisjoint(set(b.customer_unique_id))
        assert pd.to_datetime(a.label_end).le(t).all() and pd.to_datetime(b.label_end).le(t).all()
        assert c.equals(snap[v['eval_date']])
        assert b.snapshot_date.eq(v['latest_mature_snapshot']).all()
        for date,g in a.groupby('snapshot_date'):
            ref=snap[date];expected=ref.loc[~ref.customer_unique_id.isin(b.customer_unique_id)]
            assert set(g.customer_unique_id)==set(expected.customer_unique_id)
        assert set(a.snapshot_date)==set([v['latest_mature_snapshot']] if v['strategy']=='single' else v['allowed_mature_snapshots'])
        split_checks.append(dict(cell=cell,fit_rows=len(a),cal_rows=len(b),eval_rows=len(c),fit_cal_customer_overlap=0,label_maturity_pass=True,exact_eval_snapshot_readback=True,all_T_cal_customers_excluded_from_every_fit_snapshot=True))
    result=dict(status='PASS',verification='Independent raw 3-table outcomes and serialized six-cell split checks',source_paths_sha256={str(RAW/name):sha(RAW/name) for name in ['olist_orders_dataset.csv','olist_customers_dataset.csv','olist_order_items_dataset.csv']},source_code_sha256=sha(__file__),outcome_checks=outcomes,split_checks=split_checks,no_april_target_dates=True)
    (OUT/'independent-readback.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
