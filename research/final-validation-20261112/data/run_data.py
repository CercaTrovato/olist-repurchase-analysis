"""Frozen rolling datasets. No predictive-model fit; no April snapshot/label access."""
import sys
sys.dont_write_bytecode = True
import ast, hashlib, itertools, json, warnings
from pathlib import Path
from zipfile import ZipFile
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

OUT=Path(__file__).resolve().parent
ROOT=OUT.parent.parent
OLD=ROOT/'is6400-common-comparison-20261112'
AUDIT=OLD/'ae-followup/time-audit'
P2=ROOT/'is6400-validation-20261111/features/run_features.py'
CONTEXT=ROOT/'is6400-round3-extension-20261111/context/run_context.py'
SERVICE=ROOT/'is6400-round3-20261111/features/run_features.py'
READER=ROOT/'is6400-rfm-weighted-2x2-20261110/run_rfm_2x2.py'
ZIP=ROOT/'is6400-team-intake-20261110/H02_candidate_v2.zip'
RAW=Path('D:/上课资料/CityU/IS6400_Business_Data_Analytics/assignment/graded/A06-group-project/work/data/raw')
SPEC=P2.parent/'feature-views.json'
KEY=['customer_unique_id','snapshot_date']
DATES=['2017-07-01','2017-08-01','2017-09-01','2017-10-01','2017-11-01','2017-12-01','2018-01-01']
EVALS=['2017-11-01','2017-12-01','2018-01-01']
BASE=['R','F','M','average_item_rows','freight_share','recent30_orders','recent30_spend','state']
FEATURES=['R','F','M','average_order_value','max_order_value','average_item_rows','freight_share','observed_history_days','recent30_orders','recent30_spend','state']
CTX=['seller_other_buyers_log_mean','seller_other_orders_log_mean','seller_other_repeat_smoothed_mean','basket_sellers_mean','basket_products_mean','basket_categories_mean','credit_order_share','boleto_order_share','installments_max_mean']
SVC=['delivery_known_any','known_late_rate','last_order_late','known_delivery_days_mean','review_known_any','latest_known_review_score']
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):
    p=OUT/p;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2,default=str,allow_nan=False)+'\n',encoding='utf-8')
def csv(p,x):
    p=OUT/p;p.parent.mkdir(parents=True,exist_ok=True)
    x.to_csv(p,index=False,lineterminator='\n')
def selected(source,names,env):
    tree=ast.parse(source);nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes}==set(names)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<frozen-allowlist>','exec'),env)
    return env
def customer_sha(df):
    return hashlib.sha256(('\n'.join(sorted(df.customer_unique_id.astype(str)))+'\n').encode()).hexdigest()

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    dump('data-manifest.json',{'status':'BUILDING','schema_version':1,'warning':'Do not consume incomplete artifacts'})
    spec=json.loads(SPEC.read_text());fields=spec['views']['full-structure'];cats=spec['categorical_columns']
    assert len(fields)==141 and len(cats)==8
    dtype={c:'string' for c in KEY+cats}
    sourcepaths=[AUDIT/'run_time_audit.py',P2,CONTEXT,SERVICE,READER,ZIP,SPEC,RAW.parent/'source-manifest.json',OUT.parent/'task_plan.md',Path(__file__)]
    hashes={str(p):sha(p) for p in sourcepaths}
    with ZipFile(ZIP) as z:
        name='H02_candidate_v2/reproduce/notebooks/03-role01-h02-coverage-features-labels.ipynb'
        bb=z.read(name);nb=json.loads(bb)
    hashes[name]=hashlib.sha256(bb).hexdigest()
    base=selected(''.join(nb['cells'][7]['source']),['make_snapshot'],dict(pd=pd,np=np,OBS_START=pd.Timestamp('2017-01-01'),OBS_END=pd.Timestamp('2018-09-01'),FEATURES=FEATURES))
    raw_audit=[]
    p2=selected(P2.read_text(),['load','build','mode'],dict(pd=pd,np=np,json=json,Path=Path,RAW=RAW,KEY=KEY,sha=sha,dump=lambda x,n:raw_audit.append(x)))
    orders,items,pay,reviews,catalog=p2['load']()
    assert orders.order_id.is_unique
    io=items.groupby('order_id').agg(freight=('freight_value','sum'),item_rows=('order_item_id','size'))
    events=orders.rename(columns={'price_sum':'amount'}).merge(io,on='order_id',validate='one_to_one')
    for c in ['amount','freight','item_rows']: events[c]=events[c].astype(float)
    ctx=selected(CONTEXT.read_text(),['build_context'],dict(pd=pd,np=np,KEY=KEY,SELLER=CTX[:3],COMMERCE=CTX[3:]))
    svc=selected(SERVICE.read_text(),['make_new'],dict(pd=pd,np=np,NULLABLE=['known_late_rate','last_order_late','known_delivery_days_mean','latest_known_review_score']))
    snapshots={};history={};future={};summary=[];checks=[];timeaudit=[];readback=[]
    for date in DATES:
        x,y,h,f=base['make_snapshot'](events,date);x['snapshot_date']=date
        x=x.merge(y,on='customer_unique_id',validate='one_to_one')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',pd.errors.PerformanceWarning)
            more,pa=p2['build'](orders,items,pay,reviews,date,x)
        context,ca,coverage,exclusion=ctx['build_context'](orders,items,pay,date)
        service,sa,sh=svc['make_new'](orders.assign(amount=orders.price_sum),reviews,date)
        full=x.copy()
        for add in [more,context,service[KEY+SVC]]:
            full=full.merge(add,on=KEY,how='left',validate='one_to_one',indicator=True)
            assert full._merge.eq('both').all();full=full.drop(columns='_merge')
        for c in fields:
            full[c]=full[c].astype('string') if c in cats else pd.to_numeric(full[c],errors='raise').astype(float)
        # Only target orders belonging to this historical cohort enter outcomes.
        f=f.loc[f.customer_unique_id.isin(full.customer_unique_id)].copy()
        assert f.order_id.is_unique and f.amount.gt(0).all()
        target=f.groupby('customer_unique_id').agg(future_gmv=('amount','sum'),future_orders=('order_id','nunique')).reset_index()
        full=full[KEY+fields+['y']].merge(target,on='customer_unique_id',how='left',validate='one_to_one')
        full[['future_gmv','future_orders']]=full[['future_gmv','future_orders']].fillna(0)
        full.y=full.y.astype(int);full.future_orders=full.future_orders.astype(int)
        assert full.y.eq(full.future_gmv.gt(0).astype(int)).all()
        assert full.y.eq(full.future_orders.gt(0).astype(int)).all()
        cut=pd.Timestamp(date);start=cut-pd.DateOffset(months=6);end=cut+pd.Timedelta(days=90)
        assert end<=pd.Timestamp('2018-04-01') and f.order_approved_at.ge(cut).all() and f.order_approved_at.lt(end).all()
        full['label_end']=str(end.date());full=full.sort_values(KEY).reset_index(drop=True)
        assert not full.duplicated(KEY).any()
        snapshots[date]=full;history[date]=h;future[date]=f
        row=dict(snapshot_date=date,history_start_inclusive=str(start.date()),history_end_exclusive=date,label_start_inclusive=date,label_end_exclusive=str(end.date()),customers=len(full),positives=int(full.y.sum()),positive_rate=float(full.y.mean()),history_orders=len(h),cohort_label_orders=len(f),cohort_future_gmv=float(f.amount.sum()),all_pool_label_orders=int(events.order_approved_at.ge(cut).mul(events.order_approved_at.lt(end)).sum()),positive_customers_multiple_target_orders=int(full.future_orders.gt(1).sum()))
        for scope,a,b in [('history',start,cut),('label',cut,end)]:
            counts=events.order_approved_at.dt.normalize().value_counts().reindex(pd.date_range(a,b-pd.Timedelta(days=1)),fill_value=0)
            zero=counts.eq(0);runs=zero.groupby(zero.ne(zero.shift()).cumsum()).sum()
            row.update({scope+'_days':len(counts),scope+'_zero_event_days':int(zero.sum()),scope+'_longest_zero_run':int(runs.max()),scope+'_min_orders_day':int(counts.min()),scope+'_max_orders_day':int(counts.max())})
        summary.append(row);timeaudit.append(dict(snapshot_date=date,P2=pa,context=ca,service=sa))
        csv(f'context-coverage-{date}.csv',pd.DataFrame(coverage))
        if date in ['2017-07-01','2017-10-01','2018-01-01']:
            refpath=AUDIT/'private/july-full141.csv' if date=='2017-07-01' else P2.parent/('private/october-features.csv' if date=='2017-10-01' else 'private/january-features.csv')
            hashes[str(refpath)]=sha(refpath)
            ref=pd.read_csv(refpath,usecols=KEY+fields+['y'],dtype=dtype,float_precision='round_trip').sort_values(KEY).reset_index(drop=True)
            assert full[KEY].astype('string').equals(ref[KEY].astype('string'))
            for c in fields+['y']:
                a,b=full[c],ref[c]
                ok=a.fillna('__NA__').eq(b.fillna('__NA__')).to_numpy() if c in cats else np.isclose(a,b,rtol=1e-12,atol=1e-9,equal_nan=True)
                checks.append(dict(snapshot_date=date,field=c,rows=len(full),mismatched_rows=int((~ok).sum()),pass_check=bool(ok.all())))
                assert ok.all(),(date,c)
        print('BUILT',date,len(full),int(full.y.sum()),'matched_label_orders',len(f),flush=True)
    # Frozen H05 equivalent prediction: use archived semantic centers and original Oct scaling;
    # no KMeans re-fit, no target y, no K selection, no evaluation-guided label mapping.
    groupref=ROOT/'is6400-local-round2-20261110/role-04/h05-r2-verification.json'
    groupcode=groupref.parent/'rebuild_h05.py'
    hashes.update({str(groupref):sha(groupref),str(groupcode):sha(groupcode)})
    gr=json.loads(groupref.read_text());centers=np.array([[gr['centers_in_input_space'][str(g)][c] for c in ['R','log1p_F','log1p_M']] for g in [0,1,2]])
    def gx(d):
        a=d[['R','F','M']].to_numpy(float);a[:,1:]=np.log1p(a[:,1:]);return a
    octraw=OLD/'shared/private/oct-raw.csv';janraw=OLD/'shared/private/jan-raw.csv'
    hashes.update({str(p):sha(p) for p in [octraw,janraw]})
    oldoct=pd.read_csv(octraw,dtype=dtype,float_precision='round_trip')
    scale=StandardScaler().fit(gx(oldoct)).scale_
    group_checks=[]
    for date,d in snapshots.items():
        d['cluster']=np.argmin((((gx(d)[:,None,:]-centers[None,:,:])/scale[None,None,:])**2).sum(axis=2),axis=1)
        if date in ['2017-10-01','2018-01-01']:
            rp=ROOT/('is6400-local-round2-20261110/role-04/train_clusters.csv' if date=='2017-10-01' else 'is6400-h05-january-handoff-20261110/validation_clusters.csv')
            hashes[str(rp)]=sha(rp);ref=pd.read_csv(rp,dtype={c:'string' for c in KEY})
            z=d[KEY+['cluster']].merge(ref[KEY+['cluster_id']],on=KEY,how='outer',validate='one_to_one',indicator=True)
            assert z._merge.eq('both').all() and z.cluster.eq(z.cluster_id).all()
            group_checks.append(dict(snapshot_date=date,rows=len(z),mismatches=int(z.cluster.ne(z.cluster_id).sum()),all_keys_matched=True))
    dump('private/frozen-group-model.json',dict(source_path=str(groupref),source_sha256=sha(groupref),original_pipeline_source=str(groupcode),original_pipeline_sha256=sha(groupcode),input_fields=['R','log1p_F','log1p_M'],semantic_centers=centers.tolist(),october_standard_scale=scale.tolist(),distance='argmin sum(((input-semantic_center)/october_standard_scale)^2)',fit_scaler_rows=len(oldoct),new_kmeans_fits=0,labels={0:'recent_single',1:'long_single',2:'multiple_purchase'},raw_to_semantic_mapping=gr['raw_to_semantic_label'],october_january_keywise_proof=group_checks,diagnostic_only_never_X=True))
    cols=KEY+fields+['y','future_gmv','future_orders','label_end','cluster']
    for date,d in snapshots.items():
        d=d[cols];snapshots[date]=d;path=f'private/snapshots/{date}.csv';csv(path,d)
        back=pd.read_csv(OUT/path,dtype=dtype,float_precision='round_trip')
        for c in cols:
            if c in KEY+cats+['label_end']:ok=d[c].astype('string').fillna('__NA__').eq(back[c].astype('string').fillna('__NA__')).all()
            else:ok=np.allclose(d[c],back[c],rtol=1e-12,atol=1e-9,equal_nan=True)
            assert ok,(date,c)
            readback.append(dict(snapshot_date=date,field=c,pass_roundtrip=bool(ok),rows=len(d),missing=int(d[c].isna().sum())))
    cells={};support=[]
    def record(df,path):
        assert not df.duplicated(KEY).any()
        csv(path,df)
        target_events=pd.concat([future[date].loc[future[date].customer_unique_id.isin(g.customer_unique_id),['order_id','customer_unique_id']] for date,g in df.groupby('snapshot_date')],ignore_index=True)
        assert len(target_events)==df.future_orders.sum()
        return dict(path=path,sha256=sha(OUT/path),rows=len(df),unique_customers=int(df.customer_unique_id.nunique()),positive_rows=int(df.y.sum()),unique_positive_customers=int(df.loc[df.y.eq(1),'customer_unique_id'].nunique()),duplicate_customer_rows=len(df)-int(df.customer_unique_id.nunique()),target_order_rows=len(target_events),unique_target_orders=int(target_events.order_id.nunique()),repeated_target_order_rows=len(target_events)-int(target_events.order_id.nunique()),max_label_end=str(df.label_end.max()),customer_sha256=customer_sha(df),future_gmv_total=float(df.future_gmv.sum()),snapshot_dates=sorted(df.snapshot_date.unique().tolist()))
    janproof={}
    for v in EVALS:
        mature=[d for d in DATES if pd.Timestamp(d)+pd.Timedelta(days=90)<=pd.Timestamp(v)]
        latest=mature[-1];t=snapshots[latest]
        fitidx,calidx=train_test_split(np.arange(len(t)),test_size=.2,random_state=20261111,stratify=t.y)
        fitidx=np.sort(fitidx);calidx=np.sort(calidx)
        cal=t.iloc[calidx].copy();calcustomers=set(cal.customer_unique_id)
        if v=='2018-01-01':
            refidx=OLD/'shared/private/split-20261111/indices.npz';hashes[str(refidx)]=sha(refidx)
            with np.load(refidx) as ii:oldfit=oldoct.iloc[ii['fit']];oldcal=oldoct.iloc[ii['cal']]
            assert customer_sha(t.iloc[fitidx])==customer_sha(oldfit)
            assert customer_sha(cal)==customer_sha(oldcal)
            oldmanifest=OLD/'shared/data-manifest.json';hashes[str(oldmanifest)]=sha(oldmanifest)
            oldsha=json.loads(oldmanifest.read_text())['splits']['20261111']['fit_key_sha256']
            assert customer_sha(t.iloc[fitidx])==oldsha
            janproof=dict(fit_customer_sha256=customer_sha(oldfit),cal_customer_sha256=customer_sha(oldcal),matches_original_shared_fit_and_cal=True,source_indices_path=str(refidx),source_indices_sha256=sha(refidx),original_order_equals_KEY_sorted=bool(oldoct[KEY].astype('string').equals(t[KEY].astype('string'))))
        for strategy in ['single','pooled']:
            fit=t.iloc[fitidx].copy() if strategy=='single' else pd.concat([snapshots[d].loc[~snapshots[d].customer_unique_id.isin(calcustomers)] for d in mature],ignore_index=True).sort_values(KEY).reset_index(drop=True)
            assert not set(fit.customer_unique_id)&calcustomers
            assert pd.Timestamp(fit.label_end.max())<=pd.Timestamp(v) and pd.Timestamp(cal.label_end.max())<=pd.Timestamp(v)
            cell=f'{v}__{strategy}';entry=dict(eval_date=v,strategy=strategy,latest_mature_snapshot=latest,allowed_mature_snapshots=mature,fit_cal_customer_overlap=0,equal_weight_unit='one customer-snapshot prediction opportunity',fit_cal_label_end_lte_eval=True)
            for name,d in [('fit',fit),('cal',cal),('eval',snapshots[v])]:
                entry[name]=record(d,f'private/cells/{cell}/{name}.csv')
                support.append(dict(cell=cell,role=name,**{k:value for k,value in entry[name].items() if k not in ['path','sha256','customer_sha256','snapshot_dates']}))
            cells[cell]=entry
            print('CELL',cell,'fit',len(fit),'positive',int(fit.y.sum()),'cal',len(cal),int(cal.y.sum()),flush=True)
    # Public: date/support/coverage/hash only, with no customer-level target rows.
    csv('window-summary.csv',pd.DataFrame(summary));csv('cell-support.csv',pd.DataFrame(support))
    csv('historical-feature-reproduction.csv',pd.DataFrame(checks));csv('all-field-roundtrip.csv',pd.DataFrame(readback))
    caldays=pd.date_range('2017-01-01','2018-03-31',freq='D')
    raworders=pd.read_csv(RAW/'olist_orders_dataset.csv',usecols=['order_id','order_purchase_timestamp','order_approved_at'],parse_dates=['order_purchase_timestamp','order_approved_at'])
    daily=pd.DataFrame({'date':caldays})
    for name,times in [('purchase_orders',raworders.order_purchase_timestamp),('approved_orders',raworders.order_approved_at),('eligible_approved_orders',events.order_approved_at)]:daily[name]=times.dt.normalize().value_counts().reindex(caldays,fill_value=0).to_numpy()
    csv('daily-coverage.csv',daily)
    csv('monthly-coverage.csv',daily.assign(month=daily.date.dt.strftime('%Y-%m')).groupby('month',as_index=False)[['purchase_orders','approved_orders','eligible_approved_orders']].sum())
    overlaps=[];calendar=[]
    for a,b in itertools.combinations(DATES,2):
        ca,cb=set(snapshots[a].customer_unique_id),set(snapshots[b].customer_unique_id)
        overlaps.append(dict(left_date=a,right_date=b,left_customers=len(ca),right_customers=len(cb),shared_customers=len(ca&cb),shared_positive_customers=len(set(snapshots[a].loc[snapshots[a].y.eq(1),'customer_unique_id'])&set(snapshots[b].loc[snapshots[b].y.eq(1),'customer_unique_id'])),shared_matched_target_orders=len(set(future[a].order_id)&set(future[b].order_id))))
        for ka,kb in itertools.product(['history','label'],repeat=2):
            def bounds(d,k):
                t=pd.Timestamp(d);return (t-pd.DateOffset(months=6),t) if k=='history' else (t,t+pd.Timedelta(days=90))
            aa,ab=bounds(a,ka);ba,bb=bounds(b,kb);lo=max(aa,ba);hi=min(ab,bb)
            calendar.append(dict(left_date=a,left_interval=ka,right_date=b,right_interval=kb,overlap_days=max(0,(hi-lo).days),overlap_start=str(lo.date()) if lo<hi else '',overlap_end_exclusive=str(hi.date()) if lo<hi else ''))
    csv('customer-event-overlap.csv',pd.DataFrame(overlaps));csv('calendar-overlap.csv',pd.DataFrame(calendar))
    dump('date-construction-audit.json',dict(time_audits=timeaudit,raw_source_hash_audit=raw_audit,selected_functions_only=True,original_main_executed=False))
    dump('sourcehash.json',hashes)
    manifest=dict(schema_version=1,status='READY',keys=KEY,raw_fields=fields,categorical_fields=cats,base_fields=BASE,additional_columns=['y','future_gmv','future_orders','label_end','cluster'],categorical_and_key_csv_dtype='string',never_X=KEY+['y','future_gmv','future_orders','label_end','cluster'],snapshots={d:dict(path=f'private/snapshots/{d}.csv',sha256=sha(OUT/f'private/snapshots/{d}.csv'),rows=len(x),positives=int(x.y.sum()),label_end=x.label_end.iloc[0]) for d,x in snapshots.items()},cells=cells,jan_single_reuse_proof=janproof,group_long_id=1,group_model_path='frozen-group-model.json',group_keywise_proof=group_checks,sourcehash_path='sourcehash.json',raw_source_hash_audit=raw_audit,earliest_snapshot_reason='2017-07-01 is earliest permitted snapshot with the fixed six-natural-month history from observation start 2017-01-01; no performance-based window selection',target_definition='G=sum positive merchandise order amounts at approved timestamps in [snapshot,snapshot+90d) for customers in historical cohort; N=count distinct matched approved orders; y=1(G>0)=1(N>0)',target_not_profit_or_incrementality=True,no_freight_in_future_gmv=True,evaluation_is_development_not_blind=True,april_snapshot_rows_constructed=0,april_label_rows_constructed=0,april_event_dates_used_as_targets=0,latest_target_end_exclusive='2018-04-01',predictive_models_trained=0,new_kmeans_fits=0,assumptions=['Static customer/product/seller/geolocation extract; no attribute change logs','Payments, estimated delivery dates and shipping-limit values assumed known at approval and unchanged; no availability/backfill logs','Event timestamps support as-of masking but do not prove full source availability at historical cutoffs','Daily coverage reports observed zero counts, not proof of ingestion completeness','Pooled repeated customers and overlapping labels are prediction opportunities, not independent new samples','All 3 rolling evaluation windows are used/seen development windows; no new blind validation claim'])
    manifest['group_model_path']='private/frozen-group-model.json'
    # Confirm all external source bytes remained unchanged before final ready marker.
    for p,h in hashes.items():
        if p!=name and Path(p).is_file():assert sha(p)==h,p
    dump('data-manifest.json',manifest)
    dump('outputhash.json',{str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='outputhash.json'})
    print('DATA_READY',json.dumps({'snapshots':len(snapshots),'cells':len(cells),'jan_single_reuse_proof':janproof}),flush=True)

if __name__=='__main__':
    with threadpool_limits(limits=2):main()
