from experiment_common import *
BASE=OUT
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier,HistGradientBoostingClassifier
from sklearn.preprocessing import OneHotEncoder,FunctionTransformer,StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from threadpoolctl import threadpool_limits
import sklearn

old=json.loads((BASE/'results.json').read_text(encoding='utf-8'))
assert old['cohorts']==[tm,vm,sm]
assert old['features']==features and old['source_sha256']==hashes
def preprocess(scale=False):
 numeric=Pipeline([('log1p',FunctionTransformer(np.log1p)),('scale',StandardScaler())]) if scale else 'passthrough'
 return ColumnTransformer([('numeric',numeric,features[:-1]),('state',OneHotEncoder(handle_unknown='ignore',sparse_output=False),['state'])],sparse_threshold=0)
specs={
 'LogisticRegression':[(LogisticRegression(C=1.0,class_weight=w,max_iter=2000,random_state=2026),{'C':1.0,'class_weight':w}) for w in [None,'balanced']],
 'RandomForest':[(RandomForestClassifier(n_estimators=200,max_depth=8,min_samples_leaf=20,class_weight=w,random_state=2026,n_jobs=2),{'trees':200,'max_depth':8,'min_samples_leaf':20,'class_weight':w}) for w in [None,'balanced_subsample']],
 'HistGradientBoosting':[(HistGradientBoostingClassifier(max_iter=150,max_leaf_nodes=leaves,learning_rate=.05,l2_regularization=5,min_samples_leaf=30,early_stopping=False,random_state=2026),{'iterations':150,'leaves':leaves,'learning_rate':.05,'l2_regularization':5,'min_samples_leaf':30}) for leaves in [15,31]],
}
result={'design':old['cohorts'],'features':features,'sklearn_version':sklearn.__version__,'selection':'two prespecified candidates per added model; validation AP only. CatBoost original 3-candidate selection reused. All evaluated on same exploratory test quarter, not an untouched new confirmatory test.',
 'models':{'CatBoost':{'selected':old['selected']['config'],'validation':old['selected']['validation'],'test':old['test_catboost']}},'simple_rule':old['test_recency_baseline']}
combined=pd.concat([train,val])
for name,variants in specs.items():
 trials=[]
 for estimator,params in variants:
  pipeline=Pipeline([('preprocess',preprocess(name=='LogisticRegression')),('model',estimator)])
  t=time.perf_counter()
  with threadpool_limits(limits=2):
   pipeline.fit(train[features],train.y)
   scores=pipeline.predict_proba(val[features])[:,1]
  metrics=evaluate(val,scores)
  trials.append({'params':params,'validation':metrics,'fit_seconds':time.perf_counter()-t,'pipeline':pipeline})
  print('VALIDATION',name,params,metrics,flush=True)
 selected=max(trials,key=lambda a:a['validation']['AP'])
 final_model=selected['pipeline']
 with threadpool_limits(limits=2):
  final_model.fit(combined[features],combined.y)
  pred=final_model.predict_proba(test[features])[:,1]
 metrics=evaluate(test,pred)
 result['models'][name]={'selected':selected['params'],'validation':selected['validation'],'test':metrics,'trials':[{k:v for k,v in a.items() if k!='pipeline'} for a in trials]}
 pd.DataFrame({'customer_unique_id':test.index,'actual_repeat_90d':test.y.to_numpy(),'score':pred}).to_csv(BASE/(name+'-test-predictions.csv'),index=False)
 print('TEST',name,metrics,flush=True)
result['source_hashes_unchanged']=all(hashlib.sha256((DATA/n).read_bytes()).hexdigest()==hashes[n] for n in names)
assert result['source_hashes_unchanged']
(BASE/'model-comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
table=pd.DataFrame({name:v['test'] for name,v in result['models'].items()}).T
table.loc['Recency rule']=pd.Series(result['simple_rule'])
table.to_csv(BASE/'model-comparison.csv')
print('FINAL COMPARISON\n'+table.to_string(),flush=True)
