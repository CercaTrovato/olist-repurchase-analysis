import sys
sys.dont_write_bytecode=True
import hashlib,json
from pathlib import Path
import pandas as pd
import numpy as np
from catboost import CatBoostClassifier
OUT=Path(__file__).resolve().parent
def dump(x,n):(OUT/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    p=json.loads((OUT/'private/catboost-preprocess.json').read_text());cols=p['raw_fields'];cats=p['categorical_fields'];nums=[c for c in cols if c not in cats]
    b=pd.read_csv(OUT/'private/january-features.csv',dtype={c:'string' for c in cats})
    for c in cats:b[c]=b[c].fillna('__MISSING__').astype(str)
    b[nums]=b[nums].fillna(pd.Series(p['training_numeric_median']))
    model=CatBoostClassifier();model.load_model(str(OUT/'private/structure-catboost.cbm'))
    pred=model.predict_proba(b[cols])[:,1];saved=pd.read_csv(OUT/'private/january-scores.csv')['structure-catboost_score'].to_numpy();error=float(np.abs(pred-saved).max());assert error<1e-12
    v=json.loads((OUT/'artifact-verification.json').read_text());v['catboost_serialized_score_max_difference']=error;v['graph_visual_review']='Both final PNG figures actually viewed; candidate labels, metrics, denominators/legend readable; source also emits SVG'
    raw=Path('D:/上课资料/CityU/IS6400_Business_Data_Analytics/assignment/graded/A06-group-project/work/data/raw/olist_orders_dataset.csv')
    orders=pd.read_csv(raw,usecols=['order_approved_at','order_purchase_timestamp'],parse_dates=['order_approved_at','order_purchase_timestamp']);checks=[]
    for date in ['2017-10-01','2018-01-01']:
        t=pd.Timestamp(date);h=orders.loc[orders.order_approved_at.ge(t-pd.DateOffset(months=6))&orders.order_approved_at.lt(t)]
        n=int(h.order_purchase_timestamp.ge(t).sum());assert n==0;checks.append({'snapshot_date':date,'approved_history_future_purchase_timestamps':n})
    v['purchase_timestamp_checks']=checks;dump(v,'artifact-verification.json')
    spec=json.loads((OUT/'feature-views.json').read_text());seller=[c for c in spec['logical_views']['commerce'] if c.startswith('seller_id_')]
    for c in seller:spec['logical_views']['commerce'].remove(c);spec['logical_views']['seller_context'].append(c);spec['column_definitions'][c]['view']='seller_context'
    dump(spec,'feature-views.json')
    note={'reason':'First implementation applied signed-log to every numeric field, including coordinates; this contradicted the pre-result frozen plan. All five candidates were rerun using declared coordinate identity/nonnegative-log protocol. Preliminary metrics/capacities/scores retained; not used for candidate choice.','preliminary_transform':'sign(x)*log1p(abs(x)) then training StandardScaler for all numeric inputs','formal_transform':'negative values and latitude/longitude unchanged; other nonnegative values log1p; then training StandardScaler','formal_results':'../../january-metrics.csv'}
    dump(note,'private/preprocess-mismatch/README.json')
    files=[]
    for f in OUT.rglob('*'):
        if f.is_file() and f.name!='manifest.json':files.append({'path':f.relative_to(OUT).as_posix(),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'private':'private' in f.relative_to(OUT).parts})
    dump({'files':files,'scope':'Only features directory; private raw rows/models/matrices are not public artifacts'},'manifest.json')
    print('PASS CatBoost max score difference',error,'purchase_checks',checks,'manifest_files',len(files))
if __name__=='__main__':main()
