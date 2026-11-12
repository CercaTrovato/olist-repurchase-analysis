"""Two declared existing weighted-LR implementations, no tuning or new candidate."""
from pathlib import Path
from zipfile import ZipFile
import importlib.util,json,hashlib,platform
import pandas as pd,numpy as np,sklearn,scipy
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer,StandardScaler,OneHotEncoder
from sklearn.linear_model import LogisticRegression
from threadpoolctl import threadpool_limits
O=Path('E:/app-data/codex/outputs/is6400-round3-team-intake-20261112');D=O/'private/extracted/role03/Round3_role03_prediction_v1';A=O/'audit';KEY=['customer_unique_id','snapshot_date']
with ZipFile('E:/app-data/codex/outputs/is6400-team-intake-20261110/H02_candidate_v2.zip') as z:
 def rd(n):
  p=next(p for p in z.namelist() if p.endswith('/'+n) or p==n)
  with z.open(p) as f:return pd.read_csv(f,dtype={'customer_unique_id':'string'})
 f=rd('snapshot_features.csv');l=rd('snapshot_labels.csv')
data=f.merge(l[KEY+['y']],on=KEY,validate='one_to_one');train=data[data.snapshot_date.eq('2017-10-01')];val=data[data.snapshot_date.eq('2018-01-01')]
spec=importlib.util.spec_from_file_location('read_only_role03',D/'run_round3.py');r3=importlib.util.module_from_spec(spec);spec.loader.exec_module(r3)
num=r3.BASE_NUMERIC;cat=r3.BASE_CATEGORICAL
current=r3.make_model([],True)
legacy=Pipeline([('preprocess',ColumnTransformer([('numeric',Pipeline([('log1p',FunctionTransformer(np.log1p,feature_names_out='one-to-one')),('scale',StandardScaler())]),num),('state',OneHotEncoder(handle_unknown='ignore',sparse_output=False),cat)],remainder='drop')),('model',LogisticRegression(C=1.,class_weight='balanced',max_iter=2000,random_state=2026))])
stored=pd.read_csv(D/'january-predictions.csv',dtype={'customer_unique_id':'string'}).set_index(KEY)
with ZipFile('E:/app-data/codex/outputs/is6400-h04-v02-intake-20261110/H04-role03-v02.zip') as z:
 with z.open('H04_role03_prediction_v0.2/validation_predictions.csv') as fh:old=pd.read_csv(fh,dtype={'customer_unique_id':'string'}).set_index(KEY)
refs=val[KEY].copy();rr=[];matrices={}
for label,model in [('current_R3_declared',current),('legacy_H04_declared_same_row_order',legacy)]:
 with threadpool_limits(limits=2):model.fit(train[num+cat],train.y)
 score=model.predict_proba(val[num+cat])[:,1];m=model.named_steps['model'];x=model.named_steps['preprocess'].transform(train[num+cat]);matrices[label]=x
 ref=stored.loc[pd.MultiIndex.from_frame(val[KEY]),'F0_base_weighted_score'].to_numpy();prior=old.loc[pd.MultiIndex.from_frame(val[KEY]),'LogisticRegressionWeighted_score'].to_numpy()
 order=np.lexsort((val.customer_unique_id.astype(str).to_numpy(),-score));k=2937;sel=np.zeros(len(score),bool);sel[order[:k]]=True
 refs[label+'_score']=score
 rr.append({'replay':label,'new_candidate':False,'train_rows':len(train),'val_rows':len(val),'hits':int(val.y.to_numpy()[sel].sum()),'max_abs_diff_to_R3':float(abs(score-ref).max()),'max_abs_diff_to_H04_v02':float(abs(score-prior).max()),'n_iter':int(m.n_iter_[0]),'score_min':float(score.min()),'score_max':float(score.max()),'params':{k:m.get_params()[k] for k in ['C','class_weight','max_iter','tol','solver','random_state']}})
diff=float(abs(matrices['current_R3_declared']-matrices['legacy_H04_declared_same_row_order']).max())
receipt={'new_candidate_fits':0,'existing_configuration_replay_fits':2,'april_predictions':0,'environment':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__,'scipy':scipy.__version__},'same_order_preprocessed_matrix_max_diff':diff,'results':rr,'scope':'Replaying declared existing base configs under current local dependencies; not changing tol, not searching, not establishing original runtime or freeze provenance.'}
(O/'private/replayed-base-scores.csv').parent.mkdir(parents=True,exist_ok=True);refs.to_csv(O/'private/replayed-base-scores.csv',index=False)
(A/'base-replay.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(receipt,ensure_ascii=False,indent=2))
