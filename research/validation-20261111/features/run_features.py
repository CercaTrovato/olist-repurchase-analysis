"""P2 frozen development-only full legal-field comparison; no April snapshot access."""
import sys
sys.dont_write_bytecode=True
import hashlib,json,runpy,time,warnings,platform
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler,OneHotEncoder,FunctionTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import log_loss,brier_score_loss,average_precision_score,roc_auc_score,precision_recall_fscore_support,confusion_matrix
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits
import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path(__file__).resolve().parent; PRIV=OUT/'private'; ROOT=OUT.parent.parent
RAW=Path('D:/上课资料/CityU/IS6400_Business_Data_Analytics/assignment/graded/A06-group-project/work/data/raw')
KEY=['customer_unique_id','snapshot_date']; DATES=['2017-10-01','2018-01-01']
BASE=['R','F','M','average_item_rows','freight_share','recent30_orders','recent30_spend','state']
LONG_CLUSTER=1
H02=BASE+['average_order_value','max_order_value','observed_history_days']
CTX=['seller_other_buyers_log_mean','seller_other_orders_log_mean','seller_other_repeat_smoothed_mean','basket_sellers_mean','basket_products_mean','basket_categories_mean','credit_order_share','boleto_order_share','installments_max_mean']
SERVICE=['delivery_known_any','known_late_rate','last_order_late','known_delivery_days_mean','review_known_any','latest_known_review_score']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(x,n): (OUT/n).write_text(json.dumps(x,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
def csv(x,n):x.to_csv(OUT/n,index=False,lineterminator='\n')
def lognum(x,raw_indices=()):
    a=np.asarray(x,dtype=float);z=np.where(a>=0,np.log1p(np.maximum(a,0)),a)
    if raw_indices:z[:,list(raw_indices)]=a[:,list(raw_indices)]
    return z

def load():
    manifest=RAW.parent/'source-manifest.json'; m=json.loads(manifest.read_text(encoding='utf-8-sig')); frames={}; hashes={}; catalog=[]
    for e in m['files']:
        p=RAW/e['name']; hashes[e['name']]=sha(p); assert hashes[e['name']]==e['sha256']
        name=e['name'].replace('olist_','').replace('_dataset.csv','').replace('.csv',''); frames[name]=pd.read_csv(p,dtype='string')
        for pos,c in enumerate(frames[name].columns,1):catalog.append(dict(table=e['name'],position=pos,field=c))
    assert len(catalog)==52
    f=frames; orders=f['orders'];items=f['order_items'];pay=f['order_payments'];prod=f['products'];reviews=f['order_reviews'];geo=f['geolocation']
    for c in orders.columns:
        if c.endswith('_at') or c.endswith('_date') or c=='order_purchase_timestamp':orders[c]=pd.to_datetime(orders[c],errors='coerce')
    for c in ['price','freight_value','order_item_id']:items[c]=pd.to_numeric(items[c],errors='coerce')
    items.shipping_limit_date=pd.to_datetime(items.shipping_limit_date,errors='coerce')
    for c in ['payment_sequential','payment_installments','payment_value']:pay[c]=pd.to_numeric(pay[c],errors='coerce')
    for c in prod.columns:
        if c not in ['product_id','product_category_name']:prod[c]=pd.to_numeric(prod[c],errors='coerce')
    for c in ['review_creation_date','review_answer_timestamp']:reviews[c]=pd.to_datetime(reviews[c],errors='coerce')
    reviews.review_score=pd.to_numeric(reviews.review_score,errors='coerce')
    for c in ['geolocation_lat','geolocation_lng']:geo[c]=pd.to_numeric(geo[c],errors='coerce')
    geo_before=len(geo);geo=geo.drop_duplicates();geo=geo.loc[geo.geolocation_lat.between(-90,90)&geo.geolocation_lng.between(-180,180)]
    # City/state are labels, never encoded as coordinates. Exact rows removed before postcode medians.
    gc=geo.groupby('geolocation_zip_code_prefix')[['geolocation_lat','geolocation_lng']].median().reset_index()
    customers=f['customers'].merge(gc.rename(columns={'geolocation_zip_code_prefix':'customer_zip_code_prefix','geolocation_lat':'buyer_lat','geolocation_lng':'buyer_lng'}),on='customer_zip_code_prefix',how='left',validate='many_to_one')
    sellers=f['sellers'].merge(gc.rename(columns={'geolocation_zip_code_prefix':'seller_zip_code_prefix','geolocation_lat':'seller_lat','geolocation_lng':'seller_lng'}),on='seller_zip_code_prefix',how='left',validate='many_to_one')
    assert not customers.customer_id.duplicated().any() and not sellers.seller_id.duplicated().any()
    orders=orders.merge(customers,on='customer_id',how='left',validate='many_to_one').merge(items.groupby('order_id').price.sum().rename('price_sum'),on='order_id',how='left',validate='one_to_one')
    orders=orders.loc[orders.order_approved_at.notna()&orders.price_sum.gt(0)&orders.customer_unique_id.notna()].copy()
    items=items.merge(prod,on='product_id',how='left',validate='many_to_one').merge(sellers,on='seller_id',how='left',validate='many_to_one')
    dump({'manifest_sha256':sha(manifest),'raw_sha256':hashes,'raw_geo_rows':geo_before,'deduplicated_valid_geo_rows':len(geo),'unique_postcodes':len(gc),'snapshot_rows_read':50528,'april_snapshot_rows_read':0},'source-audit.json')
    return orders,items,pay,reviews,catalog

def mode(s):
    s=s.dropna(); return str(s.value_counts().sort_index().idxmax()) if len(s) else np.nan

def build(orders,items,pay,reviews,date,base):
    t=pd.Timestamp(date); start=t-pd.DateOffset(months=6)
    h=orders.loc[orders.order_approved_at.ge(start)&orders.order_approved_at.lt(t)].copy()
    assert set(h.customer_unique_id)==set(base.customer_unique_id)
    ag=h.groupby('customer_unique_id').agg(F_check=('order_id','nunique'),M_check=('price_sum','sum')).reset_index()
    ck=base[KEY+['F','M']].merge(ag,on='customer_unique_id',validate='one_to_one');assert ck.F.eq(ck.F_check).all();assert np.allclose(ck.M,ck.M_check,atol=1e-8)
    z=pd.DataFrame(index=pd.Index(base.customer_unique_id,name='customer_unique_id'))
    def agg(df,col,prefix,stats=('mean','max','std')):
        g=df.groupby('customer_unique_id')[col]
        for stat in stats:z[prefix+'_'+stat]=getattr(g,stat)()
    last=h.sort_values(['order_approved_at','order_id'],kind='stable').groupby('customer_unique_id').tail(1).set_index('customer_unique_id')
    for c in ['customer_city','customer_zip_code_prefix','customer_state','buyer_lat','buyer_lng']:z['last_'+c]=last[c]
    z['buyer_cities_nunique']=h.groupby('customer_unique_id').customer_city.nunique()
    z['buyer_states_nunique']=h.groupby('customer_unique_id').customer_state.nunique()
    h['approval_delay_days']=(h.order_approved_at-h.order_purchase_timestamp).dt.total_seconds()/86400
    h.loc[h.approval_delay_days.lt(0),'approval_delay_days']=np.nan
    h['promised_delivery_days']=(h.order_estimated_delivery_date-h.order_approved_at).dt.total_seconds()/86400
    h['purchase_hour']=h.order_purchase_timestamp.dt.hour;h['purchase_weekday']=h.order_purchase_timestamp.dt.dayofweek
    for c in ['approval_delay_days','promised_delivery_days','purchase_hour','purchase_weekday']:agg(h,c,c)
    h['carrier_known']=h.order_delivered_carrier_date.lt(t)&h.order_delivered_carrier_date.ge(h.order_approved_at)
    h['delivered_known']=h.order_delivered_customer_date.lt(t)&h.order_delivered_customer_date.ge(h.order_approved_at)
    h['carrier_days']=((h.order_delivered_carrier_date-h.order_approved_at).dt.total_seconds()/86400).where(h.carrier_known)
    h['in_transit_known']=(h.carrier_known&~h.delivered_known).astype(float)
    agg(h,'carrier_days','carrier_days');agg(h,'in_transit_known','in_transit_share',('mean',))
    hi=h[['order_id','customer_unique_id','customer_state','buyer_lat','buyer_lng','order_approved_at']].merge(items,on='order_id',how='left',validate='one_to_many')
    hi['product_volume_cm3']=hi.product_length_cm*hi.product_height_cm*hi.product_width_cm
    hi['shipping_limit_days']=(hi.shipping_limit_date-hi.order_approved_at).dt.total_seconds()/86400
    for c in ['price','freight_value','product_name_lenght','product_description_lenght','product_photos_qty','product_weight_g','product_length_cm','product_height_cm','product_width_cm','product_volume_cm3','shipping_limit_days']:agg(hi,c,c)
    for c in ['product_id','seller_id']:
        # Snapshot-historical frequency is not a target encoding; no future labels or records.
        freq=hi.groupby(c).order_id.nunique();hi[c+'_historical_frequency']=hi[c].map(freq).astype(float)
        agg(hi,c+'_historical_frequency',c+'_historical_frequency')
        z[c+'_nunique']=hi.groupby('customer_unique_id')[c].nunique()
    z['historical_category_mode']=hi.groupby('customer_unique_id').product_category_name.agg(mode)
    z['categories_nunique']=hi.groupby('customer_unique_id').product_category_name.nunique()
    for c in ['seller_city','seller_state','seller_zip_code_prefix','seller_lat','seller_lng']:
        # Multiple sellers in last order: choose first item ID, a stable key rather than score.
        ls=hi.loc[hi.order_id.isin(last.order_id)].sort_values(['order_id','order_item_id']).drop_duplicates('customer_unique_id').set_index('customer_unique_id')
        z['last_'+c]=ls[c]
    for c in ['seller_city','seller_state','seller_zip_code_prefix']:z[c+'_nunique']=hi.groupby('customer_unique_id')[c].nunique()
    lat1=np.deg2rad(hi.buyer_lat.to_numpy(float,na_value=np.nan));lat2=np.deg2rad(hi.seller_lat.to_numpy(float,na_value=np.nan));dlon=np.deg2rad(hi.seller_lng.to_numpy(float,na_value=np.nan)-hi.buyer_lng.to_numpy(float,na_value=np.nan))
    a=np.sin((lat2-lat1)/2)**2+np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
    hi['distance_km']=6371.0088*2*np.arcsin(np.sqrt(np.clip(a,0,1)))
    hi['same_state']=hi.customer_state.eq(hi.seller_state).astype('Float64').mask(hi.customer_state.isna()|hi.seller_state.isna())
    # Item-weighted mean over historical purchased items; last order mean over its items.
    agg(hi,'distance_km','distance_km',('mean','max','std'));agg(hi,'same_state','same_state',('mean',))
    z['last_order_distance_km']=hi.loc[hi.order_id.isin(last.order_id)].groupby('customer_unique_id').distance_km.mean()
    z['distance_known_share']=hi.distance_km.notna().astype(float).groupby(hi.customer_unique_id).mean()
    hp=h[['order_id','customer_unique_id']].merge(pay,on='order_id',how='left',validate='one_to_many')
    pg=hp.groupby(['order_id','customer_unique_id']);po=pg.agg(payment_rows=('payment_sequential','count'),payment_value_total=('payment_value','sum'),payment_installments_max=('payment_installments','max')).reset_index()
    for kind in ['credit_card','boleto','voucher','debit_card','not_defined']:
        po=po.merge(hp.payment_type.eq(kind).groupby([hp.order_id,hp.customer_unique_id]).any().astype(float).rename('payment_'+kind+'_share').reset_index(),on=['order_id','customer_unique_id'],validate='one_to_one')
    for c in po.columns:
        if c not in ['order_id','customer_unique_id']:agg(po,c,c)
    linked=reviews.merge(h[['order_id','customer_unique_id','order_approved_at']],on='order_id',how='inner',validate='many_to_one')
    valid=linked.review_answer_timestamp.lt(t)&linked.review_creation_date.le(linked.review_answer_timestamp)&linked.review_answer_timestamp.ge(linked.order_approved_at)&linked.review_score.between(1,5)
    r=linked.loc[valid].copy();assert r.review_answer_timestamp.lt(t).all()
    r=r.sort_values(['review_answer_timestamp','review_id','order_id','review_score'],kind='stable').drop_duplicates('order_id',keep='last')
    r['review_response_days']=(r.review_answer_timestamp-r.review_creation_date).dt.total_seconds()/86400
    r['review_text']=(r.review_comment_title.fillna('')+' '+r.review_comment_message.fillna('')).str.strip()
    r['review_text_chars']=r.review_text.str.len().astype(float)
    for c in ['review_score','review_response_days','review_text_chars']:agg(r,c,c)
    z['known_review_count']=r.groupby('customer_unique_id').order_id.nunique();z['known_review_count']=z.known_review_count.fillna(0)
    z['past_review_text']=r.groupby('customer_unique_id').review_text.agg(' '.join);z.past_review_text=z.past_review_text.fillna('')
    z['review_text_present']=z.past_review_text.str.len().gt(0).astype(int)
    z=z.reset_index();z['snapshot_date']=date
    audit={'snapshot_date':date,'history_orders':len(h),'history_customers':len(z),'start_inclusive':str(start),'end_exclusive':date,'max_approval':str(h.order_approved_at.max()),'known_answer_rows':len(r),'max_known_answer':str(r.review_answer_timestamp.max()),'future_answers_excluded':int(linked.review_answer_timestamp.ge(t).sum()),'future_deliveries_excluded':int(h.order_delivered_customer_date.ge(t).sum()),'future_carrier_excluded':int(h.order_delivered_carrier_date.ge(t).sum()),'F_exact':True,'M_allclose_atol':1e-8,'M_max_abs_error':float((ck.M-ck.M_check).abs().max()),'missing_buyer_coordinate_orders':int(h.buyer_lat.isna().sum()),'missing_seller_coordinate_items':int(hi.seller_lat.isna().sum()),'missing_distance_items':int(hi.distance_km.isna().sum())}
    return z,audit

def field_catalog(rows):
    for x in rows:
        c=x['field'];t=x['table'];status='included';dest='historical summaries';reason='Observed historical fields or derived summaries only'
        if c in ['customer_id','customer_unique_id','order_id','review_id']:
            status='key';dest='join/dedup/tie-break only; never X';reason='Pure identifiers'
        elif c in ['product_id','seller_id']:
            status='included';dest=c+'_historical_frequency_{mean,max,std}, '+c+'_nunique';reason='As-of unlabeled frequency; raw ID excluded'
        elif c=='order_status':status='unknown_at_t';dest='excluded';reason='Final extract status has no status-change log'
        elif c in ['order_item_id','payment_sequential']:status='key';dest='item/payment counts; item last-order stable ordering';reason='Partition keys; raw sequence excluded'
        elif c=='product_category_name_english':status='redundant';dest='excluded; original category retained';reason='Translation repeats original category'
        elif c in ['geolocation_city','geolocation_state']:status='redundant';dest='buyer/seller table locality labels retained';reason='Geo labels excluded from coordinates; duplicate postcode labels do not multiply joins'
        elif c.startswith('product_') or c.startswith('customer_') or c.startswith('seller_') or c.startswith('payment_') or c in ['order_estimated_delivery_date','shipping_limit_date']:
            status='assumption';reason='Static extract lacks attribute/backfill/change log; assumes values known at approval'
        if c in ['review_comment_title','review_comment_message']:dest='past_review_text TFIDF (train-only vocabulary), text length/presence';reason='Only valid answered records with answer<t'
        elif c.startswith('review_') and c!='review_id':dest='valid answer<t review score/response/text summaries';reason='Creation<=answer, approval<=answer<t'
        elif c in ['order_delivered_carrier_date','order_delivered_customer_date']:dest='only event<t carrier/delivery known summaries';reason='Future actual event excluded; negative durations invalid'
        elif c in ['geolocation_zip_code_prefix','geolocation_lat','geolocation_lng']:dest='exact-dedup postcode median coordinates -> Haversine history/last-order distance';reason='Geo static mapping assumption; not individual-address truth';status='assumption'
        elif c in ['product_id','seller_id']:pass
        elif c=='product_category_name':dest='historical_category_mode, categories_nunique, basket_categories_mean'
        elif c.startswith('product_'):dest=c+'_{mean,max,std}; dimensions -> product_volume_cm3_{mean,max,std}'
        elif c in ['customer_zip_code_prefix','customer_city','customer_state','seller_zip_code_prefix','seller_city','seller_state']:dest='last_'+c+'; locality nunique; state comparison; postcode coordinate join'
        elif c=='price':dest='M/F audit, price_{mean,max,std}, H02 AOV/max'
        elif c=='freight_value':dest='freight_value_{mean,max,std}, H02 freight_share'
        elif c=='order_purchase_timestamp':dest='approval_delay_days, purchase_hour, purchase_weekday historical summaries'
        elif c=='order_approved_at':dest='6-month window, R/F/M and recency, observed days, event legality'
        elif c=='order_estimated_delivery_date':dest='promised_delivery_days; known_late_rate/last_order_late'
        elif c=='shipping_limit_date':dest='shipping_limit_days_{mean,max,std}'
        elif c.startswith('payment_') and c!='payment_sequential':dest='payment type per-order shares / total payment / installments summaries'
        x.update(status=status,derived_destination=dest,reason=reason)
    return pd.DataFrame(rows)

def prep(train,fields):
    cats=[c for c in fields if not pd.api.types.is_numeric_dtype(train[c])];nums=[c for c in fields if c not in cats]
    raw_indices=[i for i,c in enumerate(nums) if c.endswith('_lat') or c.endswith('_lng')]
    num=Pipeline([('median',SimpleImputer(strategy='median',keep_empty_features=True,add_indicator=False)),('nonnegative_log1p',FunctionTransformer(lognum,kw_args={'raw_indices':raw_indices})),('scale',StandardScaler())])
    # Fixed flags for every numeric field, train-missing or not.
    return ColumnTransformer([('numeric',num,nums),('missing',FunctionTransformer(lambda x:pd.isna(x).astype(float)),nums),('categorical',Pipeline([('fill',SimpleImputer(strategy='constant',fill_value='__MISSING__')),('ohe',OneHotEncoder(handle_unknown='infrequent_if_exist',min_frequency=20,sparse_output=True))]),cats)],sparse_threshold=1.0),cats,nums

def metrics(jan,p,name):
    y=jan.y.to_numpy();pred=p>=.5;tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel();pr,re,f1,_=precision_recall_fscore_support(y,pred,average='binary',zero_division=0)
    s={'candidate':name,'n':len(y),'positives':int(y.sum()),'logloss':log_loss(y,p,labels=[0,1]),'brier':brier_score_loss(y,p),'AP':average_precision_score(y,p),'AUC':roc_auc_score(y,p),'mean_probability':p.mean(),'TP_05':int(tp),'FP_05':int(fp),'FN_05':int(fn),'TN_05':int(tn),'precision_05':pr,'recall_05':re,'F1_05':f1}
    order=np.lexsort((jan.customer_unique_id.astype(str).to_numpy(),-p));caps=[]
    for label,k in [('global_K2937',2937),('global_5pct',int(np.ceil(.05*len(y)))),('global_20pct',int(np.ceil(.2*len(y))))]:
        ids=order[:k];hits=int(y[ids].sum());caps.append(dict(candidate=name,policy=label,k=k,hits=hits,precision=hits/k,recall=hits/y.sum()))
    mask=jan.cluster_id.eq(LONG_CLUSTER).to_numpy();ids=order[mask[order]][:79];hits=int(y[ids].sum());caps.append(dict(candidate=name,policy='long_fixed79',k=79,hits=hits,precision=hits/79,recall=hits/y[mask].sum()))
    return s,caps

def main():
    start=time.time();assert (OUT/'feature-spec-frozen.md').exists()
    reader=runpy.run_path(str(ROOT/'is6400-rfm-weighted-2x2-20261110/run_rfm_2x2.py'));train,jan=reader['read_dev']();orders,items,pay,reviews,cat=load()
    csv(field_catalog(cat),'field-catalog-52.csv');built=[];audits=[]
    for date,b in zip(DATES,[train,jan]):
        f,a=build(orders,items,pay,reviews,date,b);built.append(f);audits.append(a)
    extra=pd.concat(built,ignore_index=True)
    contextpath=ROOT/'is6400-round3-extension-20261111/context/private/context-features.csv'
    context=pd.read_csv(contextpath,dtype={'customer_unique_id':'string'},usecols=KEY+CTX);assert set(context.snapshot_date)==set(DATES)
    services=[];cachepaths=[]
    for path in [ROOT/'is6400-round3-20261111/features/internal-october-features.csv',ROOT/'is6400-round3-20261111/features/internal-january-row-scores.csv']:
        services.append(pd.read_csv(path,dtype={'customer_unique_id':'string'},usecols=KEY+SERVICE));cachepaths.append(path)
    svc=pd.concat(services,ignore_index=True);assert set(svc.snapshot_date)==set(DATES)
    full=pd.concat([train[KEY+H02+['y']],jan[KEY+H02+['y']]],ignore_index=True)
    for f in [extra,context,svc]:full=full.merge(f,on=KEY,how='left',validate='one_to_one',indicator=True);assert full._merge.eq('both').all();full=full.drop(columns='_merge')
    # Restore numeric categories deliberately as strings (postcodes are categories).
    categorical=['state','historical_category_mode']+[c for c in full if c.startswith('last_') and any(c.endswith(v) for v in ['city','state','zip_code_prefix'])]
    excluded=KEY+['y','past_review_text'];structure=[c for c in full if c not in excluded]
    for c in structure:
        if c in categorical:full[c]=full[c].astype(object).where(full[c].notna(),np.nan)
        else:full[c]=pd.to_numeric(full[c],errors='raise').astype(float)
    train=full.loc[full.snapshot_date.eq(DATES[0])].reset_index(drop=True);jan=full.loc[full.snapshot_date.eq(DATES[1])].reset_index(drop=True)
    h05=ROOT/'is6400-h05-january-handoff-20261110/validation_clusters.csv';assert sha(h05)==reader['H05_SHA']
    jan=jan.merge(pd.read_csv(h05,dtype={'customer_unique_id':'string'}),on=KEY,validate='one_to_one');assert jan.cluster_id.eq(LONG_CLUSTER).sum()==12330;assert int(jan.loc[jan.cluster_id.eq(LONG_CLUSTER),'y'].sum())==90
    geo=[c for c in structure if c.startswith('last_customer_') or c.startswith('last_seller_') or c.startswith('last_buyer_') or c in ['buyer_cities_nunique','buyer_states_nunique','seller_city_nunique','seller_state_nunique','seller_zip_code_prefix_nunique','distance_km_mean','distance_km_max','distance_km_std','same_state_mean','last_order_distance_km','distance_known_share']]
    views={'lr8':BASE,'lr8-geo':BASE+geo,'full-structure':structure,'structure-text':structure,'structure-catboost':structure}
    dump({'keys':KEY,'target':'y','never_X':['y','cluster_id','cluster_version','split','data_version','scores','past_review_text except text view'],'views':views,'text_column':'past_review_text','categorical_columns':categorical,'note':'Raw aligned fields, fit transforms on training side only; full structure includes documented static/backfill assumptions. All tables private.'},'feature-views.json')
    csv(train,'private/october-features.csv');csv(jan,'private/january-features.csv')
    dump({'time_audit':audits,'reuse_sha256':{str(p):sha(p) for p in [contextpath]+cachepaths},'cache_allowlist':CTX+SERVICE,'cache_score_y_never_loaded':True,'geo_feature_count':len(geo),'structural_raw_columns':len(structure),'categorical_raw_columns':len(categorical),'assumptions':['Static product/customer/seller/geolocation attributes assumed valid historically; no change logs','Payments/estimated dates/shipping limit assumed known at approval without subsequent rewrites','As-of frequency uses unlabeled snapshot history including customer own events','Postcode median location is approximate; distances item-weighted and last-order item mean']},'feature-audit.json')
    missing=[]
    for d in [train,jan]:
        for c in structure:missing.append(dict(snapshot_date=d.snapshot_date.iloc[0],field=c,n=len(d),missing=int(d[c].isna().sum()),distinct=int(d[c].nunique(dropna=True)),all_missing=bool(d[c].isna().all())))
    csv(pd.DataFrame(missing),'missing-schema-audit.csv')
    print('BUILT',len(train),len(jan),len(structure),len(geo),flush=True)
    res=[];caps=[];runs=[];scores=jan[KEY+['y','cluster_id']].copy();cal=[]
    for name,fields in views.items():
        tick=time.time();print('FIT',name,flush=True)
        if name=='structure-catboost':
            from catboost import CatBoostClassifier
            cats=[c for c in fields if c in categorical];a=train[fields].copy();b=jan[fields].copy()
            nums=[c for c in fields if c not in cats]
            for c in cats:a[c]=a[c].fillna('__MISSING__').astype(str);b[c]=b[c].fillna('__MISSING__').astype(str)
            med=a[nums].median().fillna(0);a[nums]=a[nums].fillna(med);b[nums]=b[nums].fillna(med)
            model=CatBoostClassifier(depth=3,iterations=300,learning_rate=.03,l2_leaf_reg=10,random_seed=2026,loss_function='Logloss',verbose=False,allow_writing_files=False,thread_count=4)
            model.fit(a,train.y,cat_features=cats);p=model.predict_proba(b)[:,1];model.save_model(str(PRIV/'structure-catboost.cbm'));dim=len(fields);warning=[]
            dump({'training_numeric_median':med.to_dict(),'categorical_missing':'__MISSING__','raw_fields':fields,'categorical_fields':cats},'private/catboost-preprocess.json')
        else:
            transform,cats,nums=prep(train,fields)
            a=transform.fit_transform(train[fields]);b=transform.transform(jan[fields]);vocab=0
            if name=='structure-text':
                text=TfidfVectorizer(max_features=2000,min_df=5,dtype=np.float64)
                at=text.fit_transform(train.past_review_text);bt=text.transform(jan.past_review_text);vocab=at.shape[1]
                a=sparse.hstack([a,at],format='csr');b=sparse.hstack([b,bt],format='csr')
                joblib.dump(text,PRIV/'tfidf.joblib');dump({'terms':list(text.get_feature_names_out()),'train_text_present':int(train.review_text_present.sum()),'jan_text_present':int(jan.review_text_present.sum()),'vocabulary_fit':'October only'},'private/text-vocabulary.json')
            model=LogisticRegression(C=1,max_iter=2000,solver='lbfgs',class_weight=None,random_state=2026)
            with warnings.catch_warnings(record=True) as ws:
                warnings.simplefilter('always');model.fit(a,train.y);warning=[str(w.message) for w in ws]
            p=model.predict_proba(b)[:,1];dim=a.shape[1]
            # Lambda in ColumnTransformer is not pickleable by standard joblib; serialize explicit matrices and fitted LR.
            joblib.dump(model,PRIV/(name+'-lr.joblib'))
            sparse.save_npz(PRIV/(name+'-october-matrix.npz'),sparse.csr_matrix(a));sparse.save_npz(PRIV/(name+'-january-matrix.npz'),sparse.csr_matrix(b))
            dump({'fields':fields,'cats':cats,'nums':nums,'numeric_median':transform.named_transformers_['numeric'].named_steps['median'].statistics_.tolist(),'numeric_mean':transform.named_transformers_['numeric'].named_steps['scale'].mean_.tolist(),'numeric_scale':transform.named_transformers_['numeric'].named_steps['scale'].scale_.tolist(),'ohe_categories':[list(x) for x in transform.named_transformers_['categorical'].named_steps['ohe'].categories_],'ohe_min_frequency':20,'text_terms':vocab},'private/'+name+'-preprocess.json')
            joblib.dump(transform.named_transformers_['categorical'],PRIV/(name+'-categorical-transform.joblib'))
        assert np.isfinite(p).all() and len(p)==len(jan)
        scores[name+'_score']=p;m,c=metrics(jan,p,name);res.append(m);caps.extend(c)
        bins=np.minimum((p*10).astype(int),9)
        for v in range(10):
            mask=bins==v
            cal.append(dict(candidate=name,bin=v,n=int(mask.sum()),pred_mean=float(p[mask].mean()) if mask.any() else np.nan,observed_rate=float(jan.y.to_numpy()[mask].mean()) if mask.any() else np.nan))
        runs.append(dict(candidate=name,raw_columns=len(fields),encoded_columns=dim,seconds=time.time()-tick,warnings=warning,iterations=getattr(model,'n_iter_',[]).tolist() if hasattr(model,'n_iter_') else 300))
        print('DONE',name,json.dumps(m),runs[-1]['seconds'],flush=True)
        csv(pd.DataFrame(res),'january-metrics.csv');csv(pd.DataFrame(caps),'january-capacity.csv');csv(scores,'private/january-scores.csv');dump(runs,'run-audit.json')
    csv(pd.DataFrame(cal),'calibration-bins.csv')
    rm=pd.DataFrame(res).set_index('candidate');cp=pd.DataFrame(caps);fig,axs=plt.subplots(1,3,figsize=(15,4.4))
    for ax,key,title in zip(axs,['logloss','AP','AUC'],['Natural log loss (lower better)','Average precision','ROC AUC']):
        ax.barh(rm.index,rm[key]);ax.set_title(title);ax.grid(axis='x',alpha=.2)
    fig.tight_layout();fig.savefig(OUT/'feature-comparison.png',dpi=160);fig.savefig(OUT/'feature-comparison.svg');plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4.7));pivot=cp.pivot(index='candidate',columns='policy',values='hits');pivot.plot.barh(ax=ax);ax.set_xlabel('January positives captured');ax.grid(axis='x',alpha=.2);fig.tight_layout();fig.savefig(OUT/'capacity-comparison.png',dpi=160);fig.savefig(OUT/'capacity-comparison.svg');plt.close(fig)
    dump({'completed_candidates':list(views),'same_y':True,'train_rows':len(train),'train_positive':int(train.y.sum()),'january_rows':len(jan),'january_positive':int(jan.y.sum()),'raw_field_positions':52,'april_snapshot_rows_read':0,'feature_spec_sha256':sha(OUT/'feature-spec-frozen.md'),'elapsed_seconds':time.time()-start,'python':platform.python_version(),'models_adopted':False},'verification.json')
    print('COMPLETE',time.time()-start,flush=True)

if __name__=='__main__':
    with threadpool_limits(limits=4):main()
