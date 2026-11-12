"""Read-only supplemental July/October semantics counts; preserve original receipts/tables."""
import hashlib,json,sys
from pathlib import Path
from zipfile import ZipFile
import pandas as pd
sys.dont_write_bytecode=True
ROOT=Path('E:/app-data/codex/outputs')
LAB=ROOT/'is6400-common-comparison-20261112/ae-followup/time-audit'
OUT=LAB/'clarification'
RAW=Path('D:/上课资料/CityU/IS6400_Business_Data_Analytics/assignment/graded/A06-group-project/work/data/raw')
ZIP=ROOT/'is6400-team-intake-20261110/H02_candidate_v2.zip'
P2=ROOT/'is6400-validation-20261111/features/run_features.py'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(v,name):(OUT/name).write_text(json.dumps(v,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
def csv(v,name):pd.DataFrame(v).to_csv(OUT/name,index=False,lineterminator='\n')

def main():
    OUT.mkdir(exist_ok=True)
    # All original artifacts, including old receipts and hashes, must remain byte-identical.
    before={str(p.relative_to(LAB)):sha(p) for p in LAB.rglob('*') if p.is_file() and 'clarification' not in p.relative_to(LAB).parts}
    source=json.loads((RAW.parent/'source-manifest.json').read_text(encoding='utf-8-sig'))
    names=['olist_orders_dataset.csv','olist_customers_dataset.csv','olist_order_items_dataset.csv']
    expected={x['name']:x['sha256'] for x in source['files']}
    assert all(sha(RAW/n)==expected[n] for n in names)
    o=pd.read_csv(RAW/names[0],usecols=['order_id','customer_id','order_purchase_timestamp','order_approved_at'],dtype={'order_id':'string','customer_id':'string'},parse_dates=['order_purchase_timestamp','order_approved_at'])
    c=pd.read_csv(RAW/names[1],usecols=['customer_id','customer_unique_id'],dtype='string')
    i=pd.read_csv(RAW/names[2],usecols=['order_id','price'],dtype={'order_id':'string'})
    o=o.merge(c,on='customer_id',validate='one_to_one').merge(i.groupby('order_id').price.sum().rename('amount'),on='order_id',how='left',validate='one_to_one')
    eligible=o.order_approved_at.notna()&o.amount.gt(0)&o.customer_unique_id.notna()
    with ZipFile(ZIP) as z:
        path='H02_candidate_v2/reproduce/notebooks/03-role01-h02-coverage-features-labels.ipynb'
        notebook=z.read(path);nb=json.loads(notebook)
    h02_source=''.join(nb['cells'][7]['source']);h02_setup=''.join(nb['cells'][1]['source']);p2_source=P2.read_text()
    # Verify exact source conditions; no original functions or main are executed.
    hguard="hist=events.loc[events.order_approved_at.ge(start)&events.order_approved_at.lt(cut)]"
    lguard="future=events.loc[events.order_approved_at.ge(cut)&events.order_approved_at.lt(end)]"
    pguard="h=orders.loc[orders.order_approved_at.ge(start)&orders.order_approved_at.lt(t)].copy()"
    assert hguard in h02_source and lguard in h02_source and pguard in p2_source
    assert 'eligible=orders.loc[orders.order_approved_at.notna() & orders.amount.gt(0)].copy()' in h02_setup
    guards={'H02_history':hguard,'H02_label':lguard,'P2_history':pguard,'H02_qualification':'order_approved_at.notna() & amount.gt(0)','P2_qualification':'order_approved_at.notna() & price_sum.gt(0) & customer_unique_id.notna()','time_basis':'approval timestamp, not purchase timestamp','h02_notebook_member_sha256':hashlib.sha256(notebook).hexdigest(),'h02_member':path,'p2_source_sha256':sha(P2)}
    rows=[];event_pools=[];delays=[];approval_target=[]
    for date,table in [('2017-07-01','july'),('2017-10-01','october')]:
        d=pd.Timestamp(date);start=d-pd.DateOffset(months=6);end=d+pd.Timedelta(days=90)
        cohort=pd.read_csv(LAB/'private'/f'{table}-full141.csv',usecols=['customer_unique_id','y'],dtype={'customer_unique_id':'string'})
        ids=set(cohort.customer_unique_id);zeroids=set(cohort.loc[cohort.y.eq(0)].customer_unique_id)
        matched=o.customer_unique_id.isin(ids)
        history=eligible&o.order_approved_at.ge(start)&o.order_approved_at.lt(d)
        label=eligible&o.order_approved_at.ge(d)&o.order_approved_at.lt(end)
        assert set(o.loc[history,'customer_unique_id'])==ids
        counts=o.loc[label&matched].groupby('customer_unique_id').size()
        assert len(counts)==int(cohort.y.sum())
        event_pools.append({'snapshot_date':date,'label_start_inclusive':date,'label_end_exclusive':str(end.date()),'cohort_customers':len(ids),'whole_label_window_eligible_orders':int(label.sum()),'whole_label_window_unique_customers':int(o.loc[label,'customer_unique_id'].nunique()),'matched_cohort_repurchase_orders':int((label&matched).sum()),'matched_cohort_positive_customers':len(counts),'matched_cohort_single_event_positive_customers':int(counts.eq(1).sum()),'matched_cohort_multi_event_positive_customers':int(counts.gt(1).sum()),'max_label_events_one_cohort_customer':int(counts.max()),'unmatched_window_orders':int((label&~matched).sum()),'last_approval_used_for_labels':str(o.loc[label,'order_approved_at'].max())})
        # The hypothetical purchase-based mask is measured only; it never changes existing cohort/features.
        for purchase_scope,pm in [('all_purchase_before_cut',o.order_purchase_timestamp.lt(d)),('purchase_inside_six_calendar_month_history',o.order_purchase_timestamp.ge(start)&o.order_purchase_timestamp.lt(d))]:
            risk=pm&o.amount.gt(0)&o.order_approved_at.ge(d)
            miss=pm&o.amount.gt(0)&o.order_approved_at.isna()
            selected=risk&history
            rows.append({'snapshot_date':date,'purchase_scope':purchase_scope,'positive_amount_purchase_before_cut_approval_at_or_after_cut_orders':int(risk.sum()),'candidate_unique_customers':int(o.loc[risk,'customer_unique_id'].nunique()),'candidate_customers_already_in_actual_cohort':int(o.loc[risk&matched,'customer_unique_id'].nunique()),'candidate_customers_outside_actual_cohort':int(o.loc[risk&~matched,'customer_unique_id'].nunique()),'actual_history_selected_future_approval_orders':int(selected.sum()),'actual_history_selected_future_approval_customers':int(o.loc[selected,'customer_unique_id'].nunique()),'actual_history_selected_purchase_at_or_after_cut_orders':int((history&o.order_purchase_timestamp.ge(d)).sum()),'actual_cohort_additions_due_to_future_approval':0,'actual_feature_orders_affected_by_future_approval':0,'missing_approval_orders_in_purchase_scope':int(miss.sum()),'latest_candidate_approval':str(o.loc[risk,'order_approved_at'].max()) if risk.any() else None})
            assert not selected.any()
        purchase_label=o.order_purchase_timestamp.ge(d)&o.order_purchase_timestamp.lt(end)&o.amount.gt(0)
        late=purchase_label&o.order_approved_at.ge(end)
        missing=purchase_label&o.order_approved_at.isna()
        for scope,mask in [('all_window_purchasers',pd.Series(True,index=o.index)),('matched_existing_cohort',matched)]:
            v=late&mask;timestamps=o.loc[v,'order_approved_at']
            delays.append({'snapshot_date':date,'label_start_inclusive':date,'label_end_exclusive':str(end.date()),'scope':scope,'positive_amount_purchase_window_orders':int((purchase_label&mask).sum()),'purchased_in_window_approved_at_or_after_end_orders':int(v.sum()),'delayed_unique_customers':int(o.loc[v,'customer_unique_id'].nunique()),'latest_delayed_approval':str(timestamps.max()) if len(timestamps) else None,'max_approval_days_after_label_end':float((timestamps.max()-end).total_seconds()/86400) if len(timestamps) else None,'purchase_window_missing_approval_orders':int((missing&mask).sum()),'late_orders_selected_in_current_approval_label':int((v&label).sum()),'delayed_customers_current_y0':int(o.loc[v&o.customer_unique_id.isin(zeroids),'customer_unique_id'].nunique()) if scope=='matched_existing_cohort' else None})
        # Approval-time target legitimately includes orders purchased before the target start.
        for scope,mask in [('all_window_approvals',pd.Series(True,index=o.index)),('matched_existing_cohort',matched)]:
            carry=label&o.order_purchase_timestamp.lt(d)&mask
            approval_target.append({'snapshot_date':date,'scope':scope,'approved_in_label_window_orders':int((label&mask).sum()),'of_those_purchased_before_label_start_orders':int(carry.sum()),'of_those_unique_customers':int(o.loc[carry,'customer_unique_id'].nunique())})
    csv(event_pools,'event-pool-versus-cohort.csv');csv(rows,'purchase-approval-cutoff-checks.csv');csv(delays,'purchase-window-approval-delay.csv');csv(approval_target,'approval-target-carry-in.csv');dump(guards,'source-guards.json')
    after={k:sha(LAB/k) for k in before};assert before==after
    proof={'original_artifacts_checked':len(before),'all_original_artifacts_unchanged':True,'before_sha256':before,'scope':'read-only raw counts for July and October; no cohort/feature rebuild; no training','april_snapshot_rows_parsed':0,'april_label_rows_parsed':0,'models_trained':0,'event_pools':event_pools,'history_cutoff_checks':rows,'purchase_target_delay_checks':delays,'approval_target_carry_in':approval_target,'source_sha256':{str(RAW/n):expected[n] for n in names}|{str(RAW.parent/'source-manifest.json'):sha(RAW.parent/'source-manifest.json'),str(ZIP):sha(ZIP),str(P2):sha(P2)}}
    dump(proof,'clarification-audit.json')
    print(json.dumps({'pools':event_pools,'history':rows,'delays':delays,'carry_in':approval_target},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
