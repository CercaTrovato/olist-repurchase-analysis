"""Score already fitted models on predeclared temporal windows; no model fitting."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
from datetime import datetime, timezone, timedelta
import ast, hashlib, importlib.util, io, json, math, zipfile
import joblib, numpy as np, pandas as pd, sklearn
from sklearn.metrics import average_precision_score, roc_auc_score
from scipy.stats import norm, binomtest

VAULT = Path('D:/上课资料/CityU')
OUT = Path('E:/app-data/codex/outputs/is6400-frozen-test-20261125')
PRIMARY = Path('E:/app-data/codex/outputs/is6400-weighted-april-20261110/weighted-lr8.joblib')
REFERENCE = Path('E:/app-data/codex/outputs/is6400-round3-20261111/baselines/private/LR8.joblib')
ARCHIVE = Path('E:/app-data/codex/outputs/is6400-team-intake-20261110/H02_candidate_v2.zip')
BUILDER = Path('E:/app-data/codex/outputs/olist-round1-local-20261107/role-01/build_h02.py')
RAW = VAULT/'IS6400_Business_Data_Analytics/assignment/graded/A06-group-project/work/data'
FIELDS = ['R','F','M','average_item_rows','freight_share','recent30_orders','recent30_spend','state']
KEY = ['customer_unique_id','snapshot_date']
sys.path.insert(0, str(VAULT/'_meta/tools'))
from safe_write import atomic_write

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(name, text):
    p=OUT/name; p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists(): raise FileExistsError('Preserve prior run: '+str(p))
    atomic_write(str(p),text)
    assert p.read_bytes()==text.encode('utf-8')

def wilson(success,n):
    z=float(norm.ppf(.975));p=success/n;den=1+z*z/n
    center=(p+z*z/(2*n))/den
    half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return float(center-half),float(center+half)

def selected(scores,ids,fraction):
    k=math.ceil(fraction*len(scores))
    order=np.lexsort((ids.astype(str).to_numpy(),-scores))
    mask=np.zeros(len(scores),dtype=bool);mask[order[:k]]=True
    return mask

def measure(frame,scores,fraction):
    y=frame.y.to_numpy(dtype=int); mask=selected(scores,frame.customer_unique_id,fraction)
    tp=int(y[mask].sum());k=int(mask.sum());pos=int(y.sum());n=len(y)
    lo,hi=wilson(tp,k);rl,rh=wilson(tp,pos)
    return dict(N=n,positive_count=pos,negative_count=n-pos,K=k,hits=tp,TP=tp,FP=k-tp,FN=pos-tp,TN=n-k-pos+tp,
        precision=tp/k,recall=tp/pos,precision_wilson95_low=lo,precision_wilson95_high=hi,
        recall_wilson95_low=rl,recall_wilson95_high=rh,
        AP=float(average_precision_score(y,scores)),ROC_AUC=float(roc_auc_score(y,scores)),
        population_positive_rate=pos/n,random_expected_hits=k*pos/n,lift_vs_random=(tp/k)/(pos/n)),mask

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    tree=ast.parse(Path(__file__).read_text(encoding='utf-8'))
    prohibited=[x.attr for x in ast.walk(tree) if isinstance(x,ast.Attribute) and x.attr in {'fit','fit_transform','partial_fit','set_params'}]
    assert not prohibited,prohibited
    before={str(p):sha(p) for p in [PRIMARY,REFERENCE,ARCHIVE,BUILDER,RAW/'source-manifest.json']}
    assert before[str(PRIMARY)]=='ffd60ea2051658162e8cc5d34c0ebdbb512b55d5c500e878d9c9ed4b11295b0f'
    assert before[str(REFERENCE)]=='2ff2d390e53534bacef1c98c6fc86e1089de762fdbff1494f9780bca9d527ee6'
    plan=dict(schema='frozen-temporal-test-plan-v1',locked_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),
        user_confirmation={'date':'2026-11-25','statement':'用户核验四月表现没有用于调参；本次要求用冻结模型测试并给出数据。','status':'user_verified_not_reaudited_as_complete_historical_chronology'},
        model_identity='Saved H04-specification LR8 pipeline, fitted on all October; distinct from later R3 saved scores/lists',
        primary='frozen_weighted_lr8',comparators=['frozen_unweighted_lr8','recency_rule'],
        dates=['2018-04-01','2018-05-01','2018-06-01'],primary_date='2018-04-01',
        primary_fraction=.10,additional_fixed_fractions=[.05,.20],history='six calendar months before each snapshot',
        outcome='approved positive merchandise-value order in [snapshot,snapshot+90 days)',
        ranking='score descending, customer ID ascending; ceil(N*fraction)',
        prohibits=['fitting','preprocessing refit','parameter changes','model reselection from test results','creating incomplete 90-day labels'],
        history_disclosure='April has existing historical results; this run is a new execution with saved weights, not a first-ever opening of April.',
        uncertainty='Wilson 95% intervals conditional on fixed model/list and approximate independent customer sampling; excludes training/time drift uncertainty',
        overlapping_windows='Report months separately; no pooling as independent tests.',source_sha256=before)
    save('test-plan.json',json.dumps(plan,ensure_ascii=False,indent=2)+'\n')

    primary=joblib.load(PRIMARY);ref_payload=joblib.load(REFERENCE);reference=ref_payload['pipeline']
    assert ref_payload['train_snapshot']=='2017-10-01'
    for name,model,weight in [('primary',primary,'balanced'),('reference',reference,None)]:
        params=model.named_steps['model'].get_params()
        assert params['C']==1.0 and params['max_iter']==2000 and params['class_weight']==weight
        assert list(model.feature_names_in_)==FIELDS
        assert np.isfinite(model.named_steps['model'].coef_).all()
    parameters={name:{'classifier':m.named_steps['model'].get_params(),
        'raw_fields':FIELDS,'transformed_columns':int(m.named_steps['model'].n_features_in_),
        'coefficient_sha256':hashlib.sha256(m.named_steps['model'].coef_.tobytes()).hexdigest()}
        for name,m in [('primary',primary),('reference',reference)]}

    with zipfile.ZipFile(ARCHIVE) as z:
        fb=z.read('H02_candidate_v2/snapshot_features.csv');yb=z.read('H02_candidate_v2/snapshot_labels.csv')
        assert hashlib.sha256(fb).hexdigest()=='ce62dedacb5af0e08c419586ff55e45043de56771553620ef3f08100e12712b9'
        assert hashlib.sha256(yb).hexdigest()=='5e75eae468449bb9810e8ac0b796bea588762dd6c3335f2923da91a46220888f'
        features=pd.read_csv(io.BytesIO(fb),dtype={'customer_unique_id':'string'})
        labels=pd.read_csv(io.BytesIO(yb),dtype={'customer_unique_id':'string'})
    known=features.merge(labels[KEY+['y']],on=KEY,validate='one_to_one')
    jan=known.loc[known.snapshot_date.eq('2018-01-01')].sort_values(KEY).reset_index(drop=True)
    identity=[]
    for name,model in [('frozen_weighted_lr8',primary),('frozen_unweighted_lr8',reference)]:
        scores=model.predict_proba(jan[FIELDS])[:,1];metric,_=measure(jan,scores,.1)
        identity.append({'method':name,'N':len(jan),'hits':metric['hits'],'AP':metric['AP']})
    assert [x['hits'] for x in identity]==[50,46],identity

    spec=importlib.util.spec_from_file_location('frozen_test_data_builder',BUILDER)
    builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    _,orders,categories,source_counts,provenance=builder.load_inputs(RAW/'raw',RAW/'source-manifest.json')
    rows=[];paired=[];windows=[];private_frames=[];april_match=False
    train_ids=set(known.loc[known.snapshot_date.eq('2017-10-01'),'customer_unique_id'])
    for date in plan['dates']:
        f,y,_,summary=builder.make_snapshot(orders,categories,'frozen_temporal_test',date)
        frame=f.merge(y[KEY+['y']],on=KEY,validate='one_to_one').sort_values(KEY).reset_index(drop=True)
        assert not frame.duplicated(KEY).any() and not frame[FIELDS].isna().any().any()
        cut=pd.Timestamp(date);end=cut+pd.Timedelta(days=90)
        assert end<=pd.Timestamp('2018-09-01') and end<orders.order_approved_at.max()
        if date=='2018-04-01':
            old=known.loc[known.snapshot_date.eq(date)].sort_values(KEY).reset_index(drop=True)
            assert len(frame)==len(old)
            assert frame[KEY+['state','y']].astype(str).equals(old[KEY+['state','y']].astype(str))
            assert np.allclose(frame[FIELDS[:-1]],old[FIELDS[:-1]],atol=1e-9,rtol=0)
            april_match=True
        scores_by_method={'frozen_weighted_lr8':primary.predict_proba(frame[FIELDS])[:,1],
                          'frozen_unweighted_lr8':reference.predict_proba(frame[FIELDS])[:,1],
                          'recency_rule':-frame.R.to_numpy()}
        masks={}
        for method,scores in scores_by_method.items():
            assert np.isfinite(scores).all()
            for fraction in [.05,.1,.2]:
                metric,mask=measure(frame,scores,fraction)
                rows.append({'snapshot_date':date,'method':method,'fraction':fraction,**metric})
                if fraction==.1:masks[method]=mask
            frame[method+'_score']=scores
            frame[method+'_selected_10pct']=masks[method].astype(int)
        pos=frame.y.to_numpy()==1;w=masks['frozen_weighted_lr8']
        for comp in ['frozen_unweighted_lr8','recency_rule']:
            c=masks[comp];gain=int((pos&w&~c).sum());loss=int((pos&c&~w).sum())
            paired.append(dict(snapshot_date=date,primary='frozen_weighted_lr8',comparator=comp,
                gained_positive_customers=gain,lost_positive_customers=loss,net_hits=gain-loss,
                exact_paired_positive_discordance_p=float(binomtest(gain,gain+loss,.5).pvalue) if gain+loss else 1.0,
                test_scope='Exact paired discordant positive-customer test; no multiple-comparison correction; descriptive secondary'))
        summary.update(training_customer_overlap=len(set(frame.customer_unique_id)&train_ids),
            calendar_coverage_check=True,source_system_completeness_proven=False)
        windows.append(summary);private_frames.append(frame)
    metrics=pd.DataFrame(rows);save('metrics.csv',metrics.to_csv(index=False,lineterminator='\n'))
    save('paired-comparisons.csv',pd.DataFrame(paired).to_csv(index=False,lineterminator='\n'))
    save('test-windows.csv',pd.DataFrame(windows).to_csv(index=False,lineterminator='\n'))
    save('private/customer-predictions.csv',pd.concat(private_frames,ignore_index=True).to_csv(index=False,lineterminator='\n'))
    checks=dict(schema='frozen-temporal-test-verification-v1',status='completed',no_fit_or_tuning_calls=True,
        original_sources_unchanged=all(sha(p)==h for p,h in before.items()),april_rebuilt_matches_H02=april_match,
        january_identity_checks=identity,model_parameters=parameters,source_counts=source_counts,
        raw_source_sha256=provenance['verified_csv_files'],windows=windows,
        python=sys.version.split()[0],numpy=np.__version__,pandas=pd.__version__,sklearn=sklearn.__version__,
        script_sha256=sha(__file__),plan_sha256=sha(OUT/'test-plan.json'),metrics_sha256=sha(OUT/'metrics.csv'))
    assert checks['original_sources_unchanged']
    save('verification.json',json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
    print(metrics.loc[metrics.fraction.eq(.1),['snapshot_date','method','N','positive_count','K','hits','precision','recall','AP','ROC_AUC']].to_string(index=False))
    print('OUTPUT',OUT)

if __name__=='__main__':main()
