from pathlib import Path
import os
os.environ['OMP_NUM_THREADS']='2'
import json,hashlib,math,time
import numpy as np,pandas as pd
import catboost
from catboost import CatBoostClassifier
from sklearn.metrics import average_precision_score,roc_auc_score
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'/'classification'
OUT.mkdir(parents=True,exist_ok=True)
DATA=ROOT/'data'/'raw'
if not DATA.is_dir():
 raise FileNotFoundError('Run python scripts/extract_data.py first.')
names=['olist_orders_dataset.csv','olist_order_items_dataset.csv','olist_customers_dataset.csv']
hashes={n:hashlib.sha256((DATA/n).read_bytes()).hexdigest() for n in names}
o=pd.read_csv(DATA/names[0],parse_dates=['order_purchase_timestamp','order_approved_at'])
i=pd.read_csv(DATA/names[1]);c=pd.read_csv(DATA/names[2])
item=i.groupby('order_id').agg(amount=('price','sum'),item_rows=('order_item_id','size'),freight=('freight_value','sum')).reset_index()
orders=o.merge(item,on='order_id',how='left',validate='one_to_one').merge(c[['customer_id','customer_unique_id','customer_state']],on='customer_id',validate='one_to_one')
orders=orders.loc[orders.order_approved_at.notna() & orders.amount.gt(0)].copy()
# Final status is deliberately NOT used: approval-based target, not retained net sales.
orders=orders.sort_values(['order_approved_at','order_id'])
features=['R','F','M','average_order_value','max_order_value','average_item_rows','freight_share','observed_history_days','recent30_orders','recent30_spend','state']
def snapshot(cutstr):
 cut=pd.Timestamp(cutstr);start=cut-pd.DateOffset(months=6);end=cut+pd.Timedelta(days=90)
 assert end < orders.order_approved_at.max(), 'Insufficient calendar coverage'
 hist=orders.loc[orders.order_approved_at.ge(start)&orders.order_approved_at.lt(cut)].copy()
 g=hist.groupby('customer_unique_id')
 df=g.agg(last=('order_approved_at','max'),first=('order_approved_at','min'),F=('order_id','nunique'),M=('amount','sum'),max_order_value=('amount','max'),average_item_rows=('item_rows','mean'),freight_sum=('freight','sum'))
 df['R']=(cut-df['last']).dt.total_seconds()/86400
 df['observed_history_days']=(cut-df['first']).dt.total_seconds()/86400
 df['average_order_value']=df.M/df.F
 df['freight_share']=df.freight_sum/(df.M+df.freight_sum)
 recent=hist.loc[hist.order_approved_at.ge(cut-pd.Timedelta(days=30))].groupby('customer_unique_id').agg(recent30_orders=('order_id','nunique'),recent30_spend=('amount','sum'))
 df=df.join(recent).fillna({'recent30_orders':0,'recent30_spend':0})
 df['state']=g.customer_state.last().fillna('UNKNOWN')
 future=orders.loc[orders.order_approved_at.ge(cut)&orders.order_approved_at.lt(end),'customer_unique_id']
 df['y']=df.index.isin(future).astype(int)
 assert np.isfinite(df[features[:-1]].to_numpy()).all()
 meta={'snapshot':str(cut.date()),'history_start':str(start.date()),'outcome_end_exclusive':str(end.date()),'customers':len(df),'repeaters':int(df.y.sum()),'prevalence':float(df.y.mean()),'history_orders':len(hist)}
 return df,meta
train,tm=snapshot('2017-10-01');val,vm=snapshot('2018-01-01');test,sm=snapshot('2018-04-01')
assert pd.Timestamp(tm['outcome_end_exclusive'])<=pd.Timestamp(vm['snapshot'])
assert pd.Timestamp(vm['outcome_end_exclusive'])<=pd.Timestamp(sm['snapshot'])
print('COHORTS',json.dumps([tm,vm,sm],ensure_ascii=False),flush=True)
def evaluate(df,scores):
 y=df.y.to_numpy();scores=np.asarray(scores);k=math.ceil(.1*len(y))
 ranked=np.lexsort((df.index.astype(str).to_numpy(),-scores))[:k]
 hits=int(y[ranked].sum())
 return {'AP':float(average_precision_score(y,scores)),'ROC_AUC':float(roc_auc_score(y,scores)),
 'Precision_at_10pct':hits/k,'Recall_at_10pct':hits/int(y.sum()),'selected':k,'hits':hits}
