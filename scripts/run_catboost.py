# Reproduce the initial temporal CatBoost experiment.
from experiment_common import *

configs=[{'name':'depth4_unweighted','depth':4},{'name':'depth6_unweighted','depth':6},{'name':'depth4_balanced','depth':4,'auto_class_weights':'Balanced'}]
trials=[]
for cfg in configs:
 params={k:v for k,v in cfg.items() if k!='name'}
 model=CatBoostClassifier(iterations=500,learning_rate=.05,l2_leaf_reg=5,loss_function='Logloss',eval_metric='PRAUC',random_seed=2026,thread_count=2,verbose=False,allow_writing_files=False,**params)
 model.fit(train[features],train.y,cat_features=['state'],eval_set=(val[features],val.y),early_stopping_rounds=60,use_best_model=True)
 metrics=evaluate(val,model.predict_proba(val[features])[:,1])
 trials.append({'config':cfg,'trees':int(model.tree_count_),'validation':metrics})
 print('TRIAL',json.dumps(trials[-1]),flush=True)
best=max(trials,key=lambda a:a['validation']['AP'])
params={k:v for k,v in best['config'].items() if k!='name'}
combined=pd.concat([train,val])
final=CatBoostClassifier(iterations=best['trees'],learning_rate=.05,l2_leaf_reg=5,loss_function='Logloss',random_seed=2026,thread_count=2,verbose=False,allow_writing_files=False,**params)
final.fit(combined[features],combined.y,cat_features=['state'])
pred=final.predict_proba(test[features])[:,1]
result=evaluate(test,pred)
baseline=evaluate(test,-test.R.to_numpy())
predictions=pd.DataFrame({'customer_unique_id':test.index,'actual_repeat_90d':test.y.to_numpy(),'catboost_score':pred,'recency_score':-test.R.to_numpy()})
predictions.to_csv(OUT/'test-predictions.csv',index=False)
rank=np.lexsort((test.index.astype(str).to_numpy(),-pred))
deciles=[]
for j,idx in enumerate(np.array_split(rank,10),1):
 deciles.append({'decile':j,'n':len(idx),'repeaters':int(test.y.to_numpy()[idx].sum()),'repeat_rate':float(test.y.to_numpy()[idx].mean())})
report={'purpose':'Briefing exploratory feasibility only; not confirmatory evaluation or marketing uplift','model':'CatBoost','catboost_version':catboost.__version__,
 'target':'at least one further approved order with positive item amount in next 90 days; final cancellation/delivery status not filtered',
 'features':features,'cohorts':[tm,vm,sm],'selection':'3 configs; early stopping on validation PRAUC, select by sklearn validation AP; refit train+validation at chosen tree count; test once',
 'trials':trials,'selected':best,'test_catboost':result,'test_recency_baseline':baseline,
 'random_ranking_reference':{'AP_approximately':sm['prevalence'],'ROC_AUC':.5,'Precision_at_10pct_expected':sm['prevalence'],'Recall_at_10pct_expected':result['selected']/len(test)},
 'customer_overlap':{'train_test':len(set(train.index)&set(test.index)),'validation_test':len(set(val.index)&set(test.index)),'note':'Same customer can recur in historical snapshots, consistent with scoring existing customers. IDs not features; target periods do not overlap. Not an unseen-customer generalisation test.'},
 'deciles':deciles,'importance':dict(sorted(zip(features,final.feature_importances_.tolist()),key=lambda kv:-kv[1])),
 'caveats':['Single held-out quarter with few positives; no confidence intervals or multiple-period validation','Targets capture observed approvals only, not complete customer retention or net completed purchases','Snapshot eligibility excludes customers without approval in prior six months','Repeated customers across historical snapshots are intentional; historical spending is not profit','No causal or marketing-treatment effect','Do not interpret class-weighted scores as calibrated probabilities'],
 'source_sha256':hashes}
(OUT/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for n in names:assert hashlib.sha256((DATA/n).read_bytes()).hexdigest()==hashes[n]
print('FINAL',json.dumps({k:report[k] for k in ['selected','test_catboost','test_recency_baseline','random_ranking_reference','customer_overlap','importance','deciles']},ensure_ascii=False,indent=2),flush=True)
print('SOURCE HASHES UNCHANGED')
