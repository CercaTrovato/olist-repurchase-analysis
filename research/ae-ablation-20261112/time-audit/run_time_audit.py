"""July/October recovery only. No training; no April snapshot or label parsing."""
import sys
sys.dont_write_bytecode=True
import ast, hashlib, itertools, json, warnings
from pathlib import Path
from zipfile import ZipFile
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path('E:/app-data/codex/outputs/is6400-common-comparison-20261112/ae-followup/time-audit')
ROOT=Path('E:/app-data/codex/outputs')
RAW=Path('D:/上课资料/CityU/IS6400_Business_Data_Analytics/assignment/graded/A06-group-project/work/data/raw')
P2=ROOT/'is6400-validation-20261111/features/run_features.py'
CONTEXT=ROOT/'is6400-round3-extension-20261111/context/run_context.py'
SERVICE=ROOT/'is6400-round3-20261111/features/run_features.py'
READER=ROOT/'is6400-rfm-weighted-2x2-20261110/run_rfm_2x2.py'
ZIP=ROOT/'is6400-team-intake-20261110/H02_candidate_v2.zip'
SPEC=ROOT/'is6400-validation-20261111/features/feature-views.json'
KEY=['customer_unique_id','snapshot_date']
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(v,p):
    (OUT/p).write_text(json.dumps(v,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
def csv(d,p): d.to_csv(OUT/p,index=False,lineterminator='\n')
def selected_functions(source,names,env):
    tree=ast.parse(source)
    selected=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names]
    assert {n.name for n in selected}==set(names)
    exec(compile(ast.Module(body=selected,type_ignores=[]),'<audited-functions>','exec'),env)
    return env

def main():
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'private').mkdir(exist_ok=True)
    sourcehash={str(p):sha(p) for p in [P2,CONTEXT,SERVICE,READER,ZIP,SPEC,RAW.parent/'source-manifest.json']}
    spec=json.loads(SPEC.read_text());fields=spec['views']['full-structure'];cats=spec['categorical_columns']
    assert len(fields)==141
    # Executable allowlist: function bodies only, with explicit safe namespaces. No original main/import block runs.
    with ZipFile(ZIP) as z:
        notebook_path='H02_candidate_v2/reproduce/notebooks/03-role01-h02-coverage-features-labels.ipynb'
        nb_bytes=z.read(notebook_path); nb=json.loads(nb_bytes)
    sourcehash[notebook_path]=hashlib.sha256(nb_bytes).hexdigest()
    function_source=''.join(nb['cells'][7]['source'])
    FEATURES=['R','F','M','average_order_value','max_order_value','average_item_rows','freight_share','observed_history_days','recent30_orders','recent30_spend','state']
    baseenv=selected_functions(function_source,['make_snapshot'],dict(pd=pd,np=np,OBS_START=pd.Timestamp('2017-01-01'),OBS_END=pd.Timestamp('2018-09-01'),FEATURES=FEATURES))
    # Only bounded development CSV parser; never a full zip member read for CSV.
    readerenv=selected_functions(READER.read_text(),['read_dev'],dict(TEAM=ZIP.parent,sha=sha,H02_SHA='3b58f4e493e825a76ccc569f205cfa0db5d27e22b13389c3c00ff958a316419a',ZipFile=ZipFile,pd=pd,DEV_ROWS=50528,DATES=('2017-10-01','2018-01-01'),KEY=KEY))
    october_original,january_original=readerenv['read_dev']()
    raw_source_audit=[]
    p2env=selected_functions(P2.read_text(),['load','build','mode'],dict(pd=pd,np=np,json=json,Path=Path,RAW=RAW,KEY=KEY,sha=sha,dump=lambda x,n:raw_source_audit.append(x)))
    orders,items,pay,reviews,catalog=p2env['load']()
    # Raw whole-extract tables are read for as-of aggregation, not April snapshot or label evaluation.
    item_order=items.groupby('order_id').agg(freight=('freight_value','sum'),item_rows=('order_item_id','size'))
    events=orders.rename(columns={'price_sum':'amount'}).merge(item_order,on='order_id',validate='one_to_one')
    # H02 notebook reads ordinary NumPy numerics; P2 load() uses nullable numerics.
    for c in ['amount','freight','item_rows']:events[c]=events[c].astype(float)
    ctxcols=['seller_other_buyers_log_mean','seller_other_orders_log_mean','seller_other_repeat_smoothed_mean','basket_sellers_mean','basket_products_mean','basket_categories_mean','credit_order_share','boleto_order_share','installments_max_mean']
    svccols=['delivery_known_any','known_late_rate','last_order_late','known_delivery_days_mean','review_known_any','latest_known_review_score']
    ctxenv=selected_functions(CONTEXT.read_text(),['build_context'],dict(pd=pd,np=np,KEY=KEY,SELLER=ctxcols[:3],COMMERCE=ctxcols[3:]))
    svcenv=selected_functions(SERVICE.read_text(),['make_new'],dict(pd=pd,np=np,NULLABLE=['known_late_rate','last_order_late','known_delivery_days_mean','latest_known_review_score']))
    allfull={}; histories={}; futures={}; summary=[]; reconstruction=[]; readback=[]; time_audits=[]
    originals=pd.read_csv(P2.parent/'private/october-features.csv',dtype={c:'string' for c in ['customer_unique_id','snapshot_date']+cats},usecols=KEY+fields+['y'])
    assert len(originals)==21160 and originals.snapshot_date.eq('2017-10-01').all()
    sourcehash[str(P2.parent/'private/october-features.csv')]=sha(P2.parent/'private/october-features.csv')
    for date in ['2017-07-01','2017-10-01']:
        x,y,h,f=baseenv['make_snapshot'](events,date);histories[date]=h;futures[date]=f
        x['snapshot_date']=date
        x=x.merge(y,on='customer_unique_id',validate='one_to_one')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',pd.errors.PerformanceWarning)
            more,pa=p2env['build'](orders,items,pay,reviews,date,x)
        context,ca,coverage,exclusion=ctxenv['build_context'](orders,items,pay,date)
        service,sa,sh=svcenv['make_new'](orders.assign(amount=orders.price_sum),reviews,date)
        full=x.copy()
        for add in [more,context,service[KEY+svccols]]:
            full=full.merge(add,on=KEY,how='left',validate='one_to_one',indicator=True)
            assert full._merge.eq('both').all();full=full.drop(columns='_merge')
        assert set(fields).issubset(full.columns)
        for c in fields:
            if c in cats:full[c]=full[c].astype('string')
            else:full[c]=pd.to_numeric(full[c],errors='raise').astype(float)
        full=full[KEY+fields+['y']].sort_values(KEY).reset_index(drop=True);allfull[date]=full
        filename='private/'+('july' if date=='2017-07-01' else 'october')+'-full141.csv';csv(full,filename)
        loaded=pd.read_csv(OUT/filename,dtype={c:'string' for c in KEY+cats})
        assert loaded[KEY].astype('string').equals(full[KEY].astype('string'))
        for c in fields+['y']:
            a=full[c];b=loaded[c]
            if c in cats: ok=bool(a.fillna('__NA__').eq(b.fillna('__NA__')).all());error=None
            else: ok=bool(np.allclose(a,b,rtol=1e-12,atol=1e-9,equal_nan=True));error=float(np.nanmax(np.abs(a-b))) if (a.notna()&b.notna()).any() else None
            readback.append(dict(snapshot_date=date,field=c,roundtrip_ok=ok,max_abs_error=error,missing=int(a.isna().sum()),distinct=int(a.nunique(dropna=True))))
            assert ok,(date,c)
        if date=='2017-10-01':
            ref=originals.sort_values(KEY).reset_index(drop=True);assert ref[KEY].astype('string').equals(full[KEY].astype('string'))
            h02ref=october_original.sort_values(KEY).reset_index(drop=True);assert h02ref[KEY].astype('string').equals(full[KEY].astype('string'))
            for c in fields+['y']:
                a=full[c];b=ref[c]
                if c in cats:ok=bool(a.fillna('__NA__').eq(b.fillna('__NA__')).all());error=None;neq=int((~a.fillna('__NA__').eq(b.fillna('__NA__'))).sum())
                else:
                    match=np.isclose(a,b,rtol=1e-12,atol=1e-9,equal_nan=True);ok=bool(match.all());neq=int((~match).sum());error=float(np.nanmax(np.abs(a-b))) if (a.notna()&b.notna()).any() else None
                reconstruction.append(dict(field=c,block='H02' if c in FEATURES else 'context' if c in ctxcols else 'service' if c in svccols else 'P2-derived',pass_at_rtol1e12_atol1e9=ok,mismatched_rows=neq,max_abs_error=error,rows=len(full)))
            for c in FEATURES+['y']:
                a=full[c];b=h02ref[c]
                assert a.eq(b).all() if c=='state' else np.allclose(a,b,rtol=1e-12,atol=1e-9,equal_nan=True),c
        cut=pd.Timestamp(date);start=cut-pd.DateOffset(months=6);end=cut+pd.Timedelta(days=90)
        row=dict(snapshot_date=date,history_start_inclusive=str(start.date()),history_end_exclusive=date,label_start_inclusive=date,label_end_exclusive=str(end.date()),mature_at=str(end.date()),customers=len(full),positives=int(full.y.sum()),positive_rate=float(full.y.mean()),history_orders=len(h),label_eligible_orders=len(f),positive_customers_with_multiple_label_events=int(f.loc[f.customer_unique_id.isin(full.customer_unique_id)].groupby('customer_unique_id').size().gt(1).sum()))
        for scope,a,b in [('history',start,cut),('label',cut,end)]:
            counts=events.order_approved_at.dt.normalize().value_counts().reindex(pd.date_range(a,b-pd.Timedelta(days=1)),fill_value=0)
            zero=counts.eq(0);runs=zero.groupby(zero.ne(zero.shift()).cumsum()).sum()
            row.update({scope+'_days':len(counts),scope+'_zero_event_days':int(zero.sum()),scope+'_longest_zero_run':int(runs.max()),scope+'_min_orders_per_day':int(counts.min()),scope+'_max_orders_per_day':int(counts.max())})
        summary.append(row);time_audits.append(dict(date=date,P2=pa,context=ca,service=sa))
        csv(pd.DataFrame(coverage),('july' if date=='2017-07-01' else 'october')+'-context-coverage.csv')
        print('BUILT',date,len(full),int(full.y.sum()),'141',flush=True)
    csv(pd.DataFrame(summary),'window-summary.csv');csv(pd.DataFrame(reconstruction),'october-full141-reproduction.csv');csv(pd.DataFrame(readback),'all-field-roundtrip.csv')
    cal=pd.date_range('2017-01-01','2017-12-31',freq='D')
    raw_orders=pd.read_csv(RAW/'olist_orders_dataset.csv',usecols=['order_id','order_purchase_timestamp','order_approved_at'],parse_dates=['order_purchase_timestamp','order_approved_at'])
    daily=pd.DataFrame({'date':cal})
    for name,times in [('purchase_orders',raw_orders.order_purchase_timestamp),('approved_orders',raw_orders.order_approved_at),('eligible_approved_orders',events.order_approved_at)]:daily[name]=times.dt.normalize().value_counts().reindex(cal,fill_value=0).to_numpy()
    csv(daily,'daily-coverage-2017.csv')
    monthly=daily.assign(month=daily.date.dt.strftime('%Y-%m')).groupby('month',as_index=False)[['purchase_orders','approved_orders','eligible_approved_orders']].sum();csv(monthly,'monthly-coverage-2017.csv')
    sets={'2017-07-01':set(allfull['2017-07-01'].customer_unique_id),'2017-10-01':set(october_original.customer_unique_id),'2018-01-01':set(january_original.customer_unique_id)}
    overlap=[]
    for a,b in itertools.combinations(sets,2):
        sa,sb=sets[a],sets[b];overlap.append(dict(left_snapshot=a,right_snapshot=b,left_customers=len(sa),right_customers=len(sb),shared_customers=len(sa&sb),share_of_left=len(sa&sb)/len(sa),share_of_right=len(sa&sb)/len(sb)))
    csv(pd.DataFrame(overlap),'customer-overlap-allowed-periods.csv')
    # April interval arithmetic only. No April customer/label vector is ever constructed.
    windows={d:{'history':(pd.Timestamp(d)-pd.DateOffset(months=6),pd.Timestamp(d)),'label':(pd.Timestamp(d),pd.Timestamp(d)+pd.Timedelta(days=90))} for d in ['2017-07-01','2017-10-01','2018-01-01','2018-04-01']}
    intersections=[]
    for a,b in itertools.combinations(windows,2):
        for ka,kb in itertools.product(['history','label'],repeat=2):
            s=max(windows[a][ka][0],windows[b][kb][0]);e=min(windows[a][ka][1],windows[b][kb][1]);days=max(0,(e-s).days)
            intersections.append(dict(left_snapshot=a,left_interval=ka,right_snapshot=b,right_interval=kb,overlap_days=days,start_inclusive=str(s.date()) if days else '',end_exclusive=str(e.date()) if days else '',eligible_event_count_in_intersection=int(events.order_approved_at.ge(s).mul(events.order_approved_at.lt(e)).sum()) if days and e<=pd.Timestamp('2018-01-01') else None,event_count_not_computed_reason='outside July/October construction scope' if days and e>pd.Timestamp('2018-01-01') else ''))
    csv(pd.DataFrame(intersections),'calendar-window-overlaps.csv')
    # Relate July train outcomes to October historical inputs at the actual event/customer level.
    july=allfull['2017-07-01'];octo=allfull['2017-10-01']; shared=sets['2017-07-01']&sets['2017-10-01']
    transfer={'shared_July_Oct_customers':len(shared),'July_positive_customers':int(july.y.sum()),'July_positive_customers_present_in_Oct_cohort':int(july.loc[july.y.eq(1)].customer_unique_id.isin(sets['2017-10-01']).sum()),'July_label_orders_present_in_Oct_history':len(set(futures['2017-07-01'].order_id)&set(histories['2017-10-01'].order_id)),'July_label_orders_total':len(futures['2017-07-01']),'Oct_positive_customers_also_in_July_cohort':int(octo.loc[octo.y.eq(1)].customer_unique_id.isin(sets['2017-07-01']).sum()),'same_customer_positive_in_both_July_and_Oct_labels':len(set(july.loc[july.y.eq(1)].customer_unique_id)&set(octo.loc[octo.y.eq(1)].customer_unique_id))}
    dump(transfer,'event-customer-transfer.json')
    # Conditional support: no fit/cal split is created or trained.
    support=[]
    for d,df in allfull.items():
        for c in ['state','delivery_known_any','review_known_any']:
            for val,g in df.groupby(c,dropna=False):support.append(dict(snapshot_date=d,field=c,value=val,n=len(g),positives=int(g.y.sum()),positive_rate=float(g.y.mean())))
    csv(pd.DataFrame(support),'rare-event-support.csv')
    blocks=[]
    for c in fields:
        block=next((v for v,cs in spec.get('logical_views',{}).items() if c in cs),'unspecified')
        constructor='H02 make_snapshot' if c in FEATURES else 'context build_context(date)' if c in ctxcols else 'service make_new(date)' if c in svccols else 'P2 build(date)'
        assumption=''
        if c in cats or any(s in c for s in ['product_','seller_','buyer_','distance','same_state','categories','category']):assumption='Static customer/product/seller/geolocation extract; no attribute change logs'
        if any(s in c for s in ['payment','installment','credit','boleto','promised','shipping_limit','late']):assumption+='; values assumed known at approval and unchanged, no availability/rewrite log'
        blocks.append(dict(field=c,logical_block=block,constructor=constructor,recovery_status='actually_rebuilt_July_and_October',october_numeric_reproduction=next(r['pass_at_rtol1e12_atol1e9'] for r in reconstruction if r['field']==c),original_assumptions=assumption,new_assumptions_introduced=False))
    csv(pd.DataFrame(blocks),'field-recoverability-141.csv')
    fig,axes=plt.subplots(2,1,figsize=(11,6),sharex=True)
    axes[0].plot(daily.date,daily.eligible_approved_orders,lw=.7);axes[0].set_ylabel('Eligible approvals / day')
    for i,d in enumerate(['2017-07-01','2017-10-01']):
        for kind,(a,b) in windows[d].items():axes[1].broken_barh([(matplotlib.dates.date2num(a),(b-a).days)],(i*1.5,.6),facecolors='#216c9c' if kind=='history' else '#de8743',label=kind if i==0 else None)
    axes[1].set_yticks([.3,1.8],['July snapshot','October snapshot']);axes[1].legend();axes[1].xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%Y-%m'));axes[0].grid(alpha=.2);fig.tight_layout();fig.savefig(OUT/'time-coverage.png',dpi=150);fig.savefig(OUT/'time-coverage.svg');plt.close(fig)
    passed=all(r['pass_at_rtol1e12_atol1e9'] for r in reconstruction)
    result=dict(scope='recovery_only_no_model_fit',constructed_snapshots=['2017-07-01','2017-10-01'],H02_rows_parsed=50528,april_snapshot_rows_parsed=0,april_label_rows_parsed=0,april_scores_read=0,raw_full_period_csv_read=True,raw_read_purpose='as-of July/October aggregation; whole-source hash verification',historical_asof_assumptions_preserved_not_proved=True,new_assumptions_introduced=False,full141_rebuilt=True,october_full141_reproduced=passed,october_h02_all11_y_reproduced=True,numerical_tolerance={'rtol':1e-12,'atol':1e-9},models_trained=0,transformers_fit=0,new_blind_test=False,April_customer_overlap='not computed because prohibited April cohort/snapshot construction',window_summary=summary,time_audits=time_audits,raw_source_hash_audit=raw_source_audit[0],event_customer_transfer=transfer)
    result['raw_source_hash_audit'].pop('snapshot_rows_read',None)
    dump(sourcehash,'sourcehash.json');dump(result,'audit.json')
    assert passed, 'Full141 October comparison has mismatches; inspect CSV'
    dump({str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='outputhash.json'},'outputhash.json')
    print(json.dumps(dict(full141_reproduced=passed,summary=summary,transfer=transfer,overlap=overlap),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
