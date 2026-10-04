from pathlib import Path
import os
os.environ['OMP_NUM_THREADS']='2'
os.environ['MKL_NUM_THREADS']='2'
import json,hashlib
import numpy as np,pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import adjusted_rand_score,silhouette_score
from sklearn.model_selection import train_test_split
from threadpoolctl import threadpool_limits
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'/'segmentation'
OUT.mkdir(parents=True,exist_ok=True)
DATA=ROOT/'data'/'raw'
START=pd.Timestamp('2017-10-01'); CUT=pd.Timestamp('2018-04-01'); SEED=2026
names=['olist_orders_dataset.csv','olist_order_items_dataset.csv','olist_customers_dataset.csv','olist_products_dataset.csv','product_category_name_translation.csv']
hashes={n:hashlib.sha256((DATA/n).read_bytes()).hexdigest() for n in names}
o=pd.read_csv(DATA/names[0],parse_dates=['order_purchase_timestamp','order_delivered_customer_date'])
i=pd.read_csv(DATA/names[1]);c=pd.read_csv(DATA/names[2]);prod=pd.read_csv(DATA/names[3]);trans=pd.read_csv(DATA/names[4])
total=i.groupby('order_id').price.sum().rename('amount')
window=o.order_purchase_timestamp.ge(START)&o.order_purchase_timestamp.lt(CUT)
eligible=window&o.order_status.eq('delivered')&o.order_delivered_customer_date.lt(CUT)
x=o.loc[eligible].merge(c[['customer_id','customer_unique_id']],on='customer_id',validate='one_to_one').merge(total,on='order_id',validate='one_to_one')
x=x[x.amount.gt(0)].copy()
rfm=x.groupby('customer_unique_id').agg(last=('order_purchase_timestamp','max'),F=('order_id','nunique'),M=('amount','sum'))
rfm['R']=(CUT-rfm['last'].dt.normalize()).dt.days
rfm=rfm[['R','F','M']].sort_index()
train_ids,test_ids=train_test_split(rfm.index.to_numpy(),test_size=0.30,random_state=SEED)
train=rfm.loc[train_ids];test=rfm.loc[test_ids]
threshold=float(train.M.median())
def rule(df,threshold):return (df.R.gt(30).astype(int)*2+df.M.gt(threshold).astype(int)).to_numpy()
def rule_with_f(df,threshold):
 return np.where(df.F.gt(1),3,np.where(df.R.le(30),0,np.where(df.M.gt(threshold),2,1)))
def fit_k(df,cols,seed=SEED):
 scaler=StandardScaler().fit(np.log1p(df[cols]))
 with threadpool_limits(limits=2):model=KMeans(n_clusters=4,n_init=20,random_state=seed).fit(scaler.transform(np.log1p(df[cols])))
 return scaler,model
def predict_k(df,cols,scaler,model):return model.predict(scaler.transform(np.log1p(df[cols])))
rm_s,rm_k=fit_k(train,['R','M']);rfm_s,rfm_k=fit_k(train,['R','F','M'])
labels={'Rules':rule(test,threshold),'KMeans-RM':predict_k(test,['R','M'],rm_s,rm_k),'KMeans-RFM':predict_k(test,['R','F','M'],rfm_s,rfm_k)}
labels['Rules-with-F']=rule_with_f(test,threshold)
zrm=rm_s.transform(np.log1p(test[['R','M']]))
zrfm=rfm_s.transform(np.log1p(test[['R','F','M']]))
metrics={}
for method,l in labels.items():
 metrics[method]={'silhouette_same_RM_space':float(silhouette_score(zrm,l,sample_size=min(2000,len(test)),random_state=SEED)),
 'smallest_group':int(pd.Series(l).value_counts().min()),'largest_group':int(pd.Series(l).value_counts().max())}
metrics['KMeans-RFM']['silhouette_RFM_space']=float(silhouette_score(zrfm,labels['KMeans-RFM'],sample_size=min(2000,len(test)),random_state=SEED))
stability={m:[] for m in labels}
for seed in range(5):
 sample=train.sample(frac=.8,random_state=seed)
 stability['Rules'].append(float(adjusted_rand_score(labels['Rules'],rule(test,float(sample.M.median())))))
 stability['Rules-with-F'].append(float(adjusted_rand_score(labels['Rules-with-F'],rule_with_f(test,float(sample.M.median())))))
 for name,cols in [('KMeans-RM',['R','M']),('KMeans-RFM',['R','F','M'])]:
  sc,km=fit_k(sample,cols,seed)
  stability[name].append(float(adjusted_rand_score(labels[name],predict_k(test,cols,sc,km))))
 print('Resample completed',seed+1,flush=True)
seed_stability={m:[] for m in ['KMeans-RM','KMeans-RFM']}
for seed in range(3):
 for name,cols in [('KMeans-RM',['R','M']),('KMeans-RFM',['R','F','M'])]:
  sc,km=fit_k(train,cols,seed)
  seed_stability[name].append(float(adjusted_rand_score(labels[name],predict_k(test,cols,sc,km))))
for m in labels:
 metrics[m]['resample_ARI_mean']=float(np.mean(stability[m]));metrics[m]['resample_ARI_min']=float(np.min(stability[m]))
 if m in seed_stability:metrics[m]['seed_ARI_min']=min(seed_stability[m])

# Category profiles are not clustering inputs. Choose 5 categories on training customers only.
cat=i[['order_id','product_id']].merge(x[['order_id','customer_unique_id']],on='order_id',validate='many_to_one')
cat=cat.merge(prod[['product_id','product_category_name']],on='product_id',validate='many_to_one').merge(trans,on='product_category_name',how='left',validate='many_to_one')
known=cat.dropna(subset=['product_category_name_english'])[['customer_unique_id','product_category_name_english']].drop_duplicates()
top=known[known.customer_unique_id.isin(train_ids)].product_category_name_english.value_counts().head(5).index.tolist()
profiles={};lifts={};supports={}
for m,l in labels.items():
 df=test.assign(group=l)
 pr=df.groupby('group').agg(n=('R','size'),R_median=('R','median'),F_median=('F','median'),M_median=('M','median'),F_gt1_share=('F',lambda a:float(a.gt(1).mean())))
 profiles[m]=pr.reset_index().to_dict('records')
 lift_rows=[];support_rows=[]
 for category in top:
  buyer_set=set(known.loc[known.product_category_name_english.eq(category),'customer_unique_id'])
  flag=pd.Series(test.index.isin(buyer_set),index=test.index)
  base=float(flag.mean())
  for g in sorted(set(l)):
   mask=l==g;n=int(mask.sum());ncat=int(flag.to_numpy()[mask].sum());share=ncat/n
   lift_rows.append({'group':int(g),'category':category,'group_n':n,'category_buyers':ncat,'share':share,'overall_share':base,'lift':share/base})
 lifts[m]=lift_rows
 pd.DataFrame(lift_rows).to_csv(OUT/(m+'-category-lift.csv'),index=False)

report={'design':{'start':str(START.date()),'cutoff':str(CUT.date()),'valid_orders':'purchased in window, delivered before cutoff, current status delivered, positive summed item value','window_orders_before_filter':int(window.sum()),'included_orders':len(x),'customers':len(rfm),'train_customers':len(train),'test_customers':len(test),'R_threshold_days':30,'M_threshold_BRL':threshold,'K':4,'seed':SEED,'resamples':'5 x 80% training sample, without replacement; refit scaler, model and monetary threshold','future_validation':False,'single_order_share':float(rfm.F.eq(1).mean()),'unknown_category_item_rows':int(cat.product_category_name_english.isna().sum())},'metrics':metrics,'resample_ARI':stability,'seed_ARI':seed_stability,'profiles':profiles,'top5_categories_training':top,'category_lifts':lifts}
report['design']['posthoc_diagnostic']='Rules-with-F was added after observing the RFM repeat-buyer cluster. Diagnostic only, not an independent confirmatory test; fresh holdout is needed for formal selection.'
(OUT/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
pd.DataFrame(metrics).T.to_csv(OUT/'comparison.csv')
print(json.dumps({k:report[k] for k in ['design','metrics','profiles','top5_categories_training']},ensure_ascii=False,indent=2),flush=True)

# Scientific plots of actual observations; no illustrative or synthetic values.
from matplotlib import font_manager
available_fonts={font.name for font in font_manager.fontManager.ttflist}
chosen_font=next((name for name in ['Microsoft YaHei','Noto Sans CJK SC','SimHei'] if name in available_fonts),'DejaVu Sans')
plt.rcParams.update({'font.family':chosen_font,'axes.unicode_minus':False,'font.size':11})
palette=['#2964a3','#cf5b45','#328577','#9b619e']
fig,axes=plt.subplots(1,2,figsize=(14,5.3),sharex=True,sharey=True)
draw=test.sample(n=min(3000,len(test)),random_state=SEED)
for ax,method,title in zip(axes,['Rules','KMeans-RM'],['简单规则：固定阈值分四组','K-means：用相同 R、M 自动分四组']):
 lab=pd.Series(labels[method],index=test.index).loc[draw.index]
 for g in sorted(lab.unique()):
  d=draw.loc[lab.eq(g)]
  ax.scatter(d.R,d.M,s=9,alpha=.55,color=palette[int(g)],label=f'组 {g+1}')
 if method=='Rules':ax.axvline(30,c='#222',ls='--',lw=1);ax.axhline(threshold,c='#222',ls='--',lw=1)
 ax.set_yscale('log');ax.set_xlabel('距最近购买的天数 R');ax.set_title(title,loc='left',fontsize=14)
 ax.grid(alpha=.15);ax.legend(ncol=2,fontsize=9)
axes[0].set_ylabel('历史商品消费金额 M（BRL，对数坐标）')
fig.suptitle('同一批留出客户，两种分群边界｜点为真实客户；最多展示 3,000 人',fontsize=15,y=1.01)
fig.text(.5,.005,'注意：两图的组号／颜色不表示相同人群；K-means 输入为 log1p 变换并标准化后的 R、M。',ha='center',fontsize=10,color='#555')
fig.tight_layout(rect=[0,.035,1,.98]);fig.savefig(OUT/'comparison.png',dpi=170,bbox_inches='tight');plt.close(fig)
for n in names:assert hashlib.sha256((DATA/n).read_bytes()).hexdigest()==hashes[n]
print('SOURCE HASHES UNCHANGED',flush=True)
