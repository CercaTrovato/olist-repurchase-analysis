from pathlib import Path
from zipfile import ZipFile
import json,hashlib,math
import pandas as pd
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq
O=Path('E:/app-data/codex/outputs/is6400-round3-team-intake-20261112');A=O/'audit';E=O/'private/extracted'
D={r:next((E/r).iterdir()) for r in ['role01','role02','role03','role04']}
RAW=Path('D:/上课资料/CityU/IS6400_Business_Data_Analytics/assignment/graded/A06-group-project/work/data/raw')
KEY=['customer_unique_id','snapshot_date']
def rd(p,**kw):return pd.read_csv(p,encoding='utf-8-sig',**kw)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def savej(v,n):(A/n).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
orders=rd(RAW/'olist_orders_dataset.csv',parse_dates=['order_purchase_timestamp','order_approved_at','order_delivered_customer_date','order_estimated_delivery_date'])
cust=rd(RAW/'olist_customers_dataset.csv',usecols=['customer_id','customer_unique_id'])
items=rd(RAW/'olist_order_items_dataset.csv',usecols=['order_id','product_id','price'])
products=rd(RAW/'olist_products_dataset.csv',usecols=['product_id','product_category_name'])
reviews=rd(RAW/'olist_order_reviews_dataset.csv',usecols=['order_id','review_id','review_score','review_creation_date','review_answer_timestamp'],parse_dates=['review_creation_date','review_answer_timestamp'])
amount=items.groupby('order_id').price.sum(min_count=1).rename('amount')
fact=orders.merge(amount,on='order_id',how='left',validate='one_to_one').merge(cust,on='customer_id',validate='one_to_one')
q=fact[fact.order_approved_at.notna()&fact.amount.gt(0)].copy()
sourcehash={n:sha(RAW/n) for n in ['olist_orders_dataset.csv','olist_customers_dataset.csv','olist_order_items_dataset.csv','olist_products_dataset.csv','olist_order_reviews_dataset.csv']}
asof=rd(D['role01']/'snapshot-asof-features.csv',dtype={'customer_unique_id':'string'})
groups=pd.concat([rd(D['role03']/n,dtype={'customer_unique_id':'string'}) for n in ['training_clusters.csv','validation_clusters.csv']])
catgiven=rd(D['role04']/'results/category-support.csv')
fields=['delivered_known_n','delivery_days_mean','delivery_promise_known_n','late_delivery_share','review_known_n','review_score_mean','low_review_share']
fieldchecks=[];catchecks=[];missing=[]
for date in ['2017-10-01','2018-01-01']:
 t=pd.Timestamp(date);hist=q[(q.order_approved_at>=t-pd.DateOffset(months=6))&(q.order_approved_at<t)].copy()
 v=reviews[reviews.order_id.isin(hist.order_id)].drop_duplicates().merge(hist[['order_id','order_purchase_timestamp']],on='order_id',validate='many_to_one')
 ok=v.review_answer_timestamp.notna()&v.review_answer_timestamp.ge(v.order_purchase_timestamp)&(v.review_creation_date.isna()|v.review_answer_timestamp.ge(v.review_creation_date))&v.review_score.isin([1,2,3,4,5])&v.review_answer_timestamp.lt(t)
 last=v[ok].sort_values(['review_answer_timestamp','review_creation_date','review_id','review_score'],na_position='first').groupby('order_id',sort=False).tail(1)
 h=hist.merge(last[['order_id','review_score']],on='order_id',how='left',validate='one_to_one')
 valid_delivery=h.order_delivered_customer_date.notna()&h.order_delivered_customer_date.ge(h.order_approved_at)&h.order_delivered_customer_date.ge(h.order_purchase_timestamp)&h.order_delivered_customer_date.lt(t)
 promise=valid_delivery&h.order_estimated_delivery_date.notna()&h.order_estimated_delivery_date.dt.normalize().ge(h.order_purchase_timestamp.dt.normalize())
 h['dur']=((h.order_delivered_customer_date-h.order_approved_at).dt.total_seconds()/86400).where(valid_delivery)
 h['late']=h.order_delivered_customer_date.dt.normalize().gt(h.order_estimated_delivery_date.dt.normalize()).astype(float).where(promise)
 h['low']=h.review_score.le(2).astype(float).where(h.review_score.notna())
 rebuilt=h.groupby('customer_unique_id').agg(delivered_known_n=('dur','count'),delivery_days_mean=('dur','mean'),delivery_promise_known_n=('late','count'),late_delivery_share=('late','mean'),review_known_n=('review_score','count'),review_score_mean=('review_score','mean'),low_review_share=('low','mean')).reset_index()
 rebuilt['snapshot_date']=date
 j=asof[asof.snapshot_date.eq(date)].merge(rebuilt,on=KEY,how='outer',validate='one_to_one',suffixes=('_got','_raw'),indicator=True)
 assert j['_merge'].eq('both').all()
 for f in fields:
  a=j[f+'_got'];b=j[f+'_raw'];nan=int(a.isna().ne(b.isna()).sum());diff=float(abs(a-b).max())
  assert nan==0 and diff<1e-10,(date,f,diff,nan)
  fieldchecks.append({'snapshot_date':date,'field':f,'rows':len(j),'nan_mismatches':nan,'max_abs_diff':diff})
 missing.append({'snapshot_date':date,'delivery_mean_missing':int(j.delivery_days_mean_got.isna().sum()),'review_mean_missing':int(j.review_score_mean_got.isna().sum())})
 # Category cache independently rebuilt from raw products/items/orders/customer joins.
 pairs=items.merge(hist[['order_id','customer_unique_id']],on='order_id',validate='many_to_one').merge(products,on='product_id',how='left',validate='many_to_one')
 pairs['category']=pairs.product_category_name.fillna('UNKNOWN')
 pairs=pairs[['customer_unique_id','category']].drop_duplicates()
 pool=groups[groups.snapshot_date.eq(date)]
 assert set(pairs.customer_unique_id)==set(pool.customer_unique_id)
 paired=pairs.merge(pool[['customer_unique_id','cluster_id']],on='customer_unique_id',validate='many_to_one')
 counts=paired.groupby(['cluster_id','category']).size()
 allcounts=pairs.groupby('category').size()
 for _,r in catgiven[catgiven.snapshot_date.eq(date)].iterrows():
  k=int(counts.get((r.cluster_id,r.category),0));n=int(pool.cluster_id.eq(r.cluster_id).sum());ak=int(allcounts.get(r.category,0));an=len(pool)
  otherk=ak-k;othern=an-n;se=(1-n/an)*math.sqrt((k/n)*(1-k/n)/n+(otherk/othern)*(1-otherk/othern)/othern)
  vals={'buyers':k,'denominator':n,'all_buyers':ak,'all_denominator':an,'share':k/n,'all_share':ak/an,'gap_pp':100*(k/n-ak/an),'gap_low_pp':100*(k/n-ak/an-1.96*se),'gap_high_pp':100*(k/n-ak/an+1.96*se)}
  diff=max(abs(float(r[a])-b) for a,b in vals.items());assert diff<1e-9,(date,r.cluster_id,r.category,diff)
  catchecks.append({'snapshot_date':date,'cluster_id':int(r.cluster_id),'category':r.category,'max_abs_diff':diff})
pd.DataFrame(fieldchecks).to_csv(A/'raw-asof-readback.csv',index=False)
pd.DataFrame(catchecks).to_csv(A/'raw-category-readback.csv',index=False)
calendar=[]
w=rd(D['role01']/'time-window-audit.csv')
for _,r in w.iterrows():
 t=pd.Timestamp(r.snapshot_date);end=t+pd.Timedelta(days=90)
 overlaps=[max(0,(min(end,pd.Timestamp(v)+pd.Timedelta(days=90))-max(t,pd.Timestamp(v))).days) for v in ['2018-01-01','2018-04-01']]
 beyond=max(0,(end-max(t,pd.Timestamp(r.H02_working_observation_end_exclusive))).days)
 assert str(end.date())==r.target_end_exclusive and sum(overlaps)==int(r.target_overlap_seen_union_days) and beyond==int(r.target_days_beyond_H02_bound)
 calendar.append({'snapshot_date':r.snapshot_date,'target_end_exclusive':str(end.date()),'overlap_seen_days':sum(overlaps),'days_beyond_working_bound':beyond,'matches':True})
pd.DataFrame(calendar).to_csv(A/'calendar-readback.csv',index=False)
mde=rd(D['role04']/'results/available-pool-mde.csv');p0=90/12330;mdechecks=[]
def ncalc(d):
 p1=p0+d;pbar=(p0+p1)/2
 return (norm.ppf(.975)*math.sqrt(2*pbar*(1-pbar))+norm.ppf(.8)*math.sqrt(p0*(1-p0)+p1*(1-p1)))**2/d**2
for _,r in mde.iterrows():
 root=brentq(lambda d:ncalc(d)-r.n_per_arm,1e-6,.5)
 assert abs(root*100-r.mde_pp)<1e-10
 mdechecks.append({'reachable_fraction':float(r.reachable_fraction_assumed),'n_per_arm':int(r.n_per_arm),'mde_pp':root*100,'matches':True})
savej({'status':'PASS','raw_source_sha256':sourcehash,'raw_asof_compares':len(fieldchecks),'category_rows_independently_rebuilt':len(catchecks),'missing':missing,'calendar_windows':len(calendar),'mde':mdechecks,'new_model_fits':0,'new_april_labels_or_scores':0,'scope':'Oct/Jan as-of and categories rebuilt only; future windows calendar arithmetic only; no new target scoring'},'raw-readback-summary.json')
print(json.dumps({'asof_compares':len(fieldchecks),'raw_category_rows':len(catchecks),'calendar_windows':len(calendar),'missing':missing,'MDE_scenarios':len(mdechecks),'new_fits':0},ensure_ascii=False))
