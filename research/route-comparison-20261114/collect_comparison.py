"""Repackage saved aggregate results for route comparison; no fits or new intervals."""
from pathlib import Path
import json,hashlib
import pandas as pd,numpy as np
O=Path(__file__).resolve().parent;D=O/'data';D.mkdir(exist_ok=True)
F=Path('E:/app-data/codex/outputs/is6400-final-validation-20261112')
T=Path('E:/app-data/codex/outputs/is6400-round3-team-intake-20261112')
S=T/'private/extracted/role03/Round3_role03_prediction_v1'
sources=[T/'audit/january-recomputed.csv',T/'audit/january-groups-recomputed.csv',S/'cv-summary.csv',S/'group-cv-summary.csv',F/'probability/primary-eval-metrics.csv',F/'value/capacity-results.csv']
r=pd.read_csv(sources[0]);teams=r[(r.table=='basic')|r.method.isin(['B_global_with_cluster','C_segmented_group2_global_fallback'])].copy();assert len(teams)==24
teams.to_csv(D/'team-capacity-results.csv',index=False)
g=pd.read_csv(sources[1]);g.to_csv(D/'team-group-results.csv',index=False)
cv=pd.read_csv(sources[2]);cv['method']=cv['variant']+'_'+cv['weighted'].map({True:'weighted',False:'unweighted'})
gc=pd.read_csv(sources[3]);gc=gc[gc.method.ne('F0_global_weighted')]
vc=pd.concat([cv,gc],ignore_index=True);vc['scope']='October internal stratified folds; each valid fold N4232 and K424';vc['errorbar_meaning']='sample standard deviation over 5 folds, not confidence interval';vc.to_csv(D/'team-cv-diagnostics.csv',index=False)
p=pd.read_csv(sources[4]);p[['evaluation_date','strategy']]=p.cell.str.split('__',expand=True)
cap=pd.read_csv(sources[5]);mapfamily={'weightedLR':'p_wlr','unweightedLR':'p_ulr','nativeCatBoost-mean3':'p_catboost'}
q=[]
for _,v in p.iterrows():
 fam=mapfamily[v.family];common=(cap.evaluation_date==v.evaluation_date)&(cap.strategy==v.strategy)&(cap.family==fam)&(cap.rule=='p')
 globalrow=cap[common&(cap.scope=='global')&cap.capacity.eq(.1)].iloc[0];longrow=cap[common&(cap.scope=='long79')].iloc[0]
 d=v.to_dict();d.update(family_score_column=fam,K=int(globalrow.K),hits=int(globalrow['hits']),long79_K=int(longrow.K),long79_hits=int(longrow['hits']),global_long_seats=int(globalrow.long_seats),global_long_hits=int(globalrow.long_hits));q.append(d)
out=pd.DataFrame(q);out.to_csv(D/'local-rolling-probability-and-lists.csv',index=False)
single=out[out.strategy.eq('single')];assert len(single)==9
jan=single[single.evaluation_date.eq('2018-01-01')]
assert int(jan[jan.family=='weightedLR']['hits'].iloc[0])==43 and int(jan[jan.family=='nativeCatBoost-mean3']['hits'].iloc[0])==49
protocol=[{'route':'A team R3 proposed freeze','train_snapshot':'2017-10-01','predictor_fit_rows':21160,'fit_positive_rows':211,'calibration_rows':0,'cal_positive_rows':0,'evaluation_snapshot':'2018-01-01','evaluation_rows':29368,'positive_rows':230,'K':2937,'method':'F0 base8 weighted LR; raw ranking scores','features':8,'hits':50,'long79_hits':2,'global_long_seats':73,'direct_A_B_superiority_comparison_valid':False},
{'route':'B proposed probability pipeline','train_snapshot':'2017-10-01','predictor_fit_rows':16928,'fit_positive_rows':169,'calibration_rows':4232,'cal_positive_rows':42,'evaluation_snapshot':'2018-01-01','evaluation_rows':29368,'positive_rows':230,'K':2937,'method':'full141 native CatBoost mean of 3 separately calibrated probabilities; single strategy','features':141,'hits':49,'long79_hits':2,'global_long_seats':int(jan[jan.family=='nativeCatBoost-mean3'].global_long_seats.iloc[0]),'direct_A_B_superiority_comparison_valid':False},
{'route':'B same-protocol reference','train_snapshot':'2017-10-01','predictor_fit_rows':16928,'fit_positive_rows':169,'calibration_rows':4232,'cal_positive_rows':42,'evaluation_snapshot':'2018-01-01','evaluation_rows':29368,'positive_rows':230,'K':2937,'method':'base8 weighted LR with held-out calibration','features':8,'hits':43,'long79_hits':2,'global_long_seats':int(jan[jan.family=='weightedLR'].global_long_seats.iloc[0]),'direct_A_B_superiority_comparison_valid':False}]
pd.DataFrame(protocol).to_csv(D/'protocol-comparison.csv',index=False)
value=cap[(cap.scope=='global')&cap.capacity.eq(.1)]
point=value.pivot(index=['evaluation_date','strategy','family'],columns='rule',values='captured_G')
counts={'n_correlated_combinations':len(point),'pFM_captured_G_gt_p':int((point.purchase_F_M>point.p).sum()),'expected_G_gt_p':int((point.expected_G>point.p).sum()),'expected_G_gt_pFM':int((point.expected_G>point.purchase_F_M).sum()),'not_independent_trials':True}
assert counts['pFM_captured_G_gt_p']==15 and counts['expected_G_gt_pFM']==11
(D/'value-direction-summary.json').write_text(json.dumps(counts,indent=2)+'\n',encoding='utf-8')
value[value.evaluation_date.eq('2018-01-01')&value.strategy.eq('single')].to_csv(D/'local-january-value-rules.csv',index=False)
pv=cap[(cap.evaluation_date=='2018-01-01')&(cap.strategy=='single')&(cap.scope=='global')&(cap.family=='p_catboost')&cap.rule.isin(['p','purchase_F_M','expected_G'])]
pv.to_csv(D/'proposed-B-capacity-value.csv',index=False)
record={'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},'checks':{'team_capacity_rows':len(teams),'team_CV_rows':len(vc),'local_rolling_systems':len(out),'local_single_strategy_systems':len(single),'protocol_rows':len(protocol),'value_direction_counts':counts},'new_model_fits':0,'new_uncertainty_intervals':0,'new_april_predictions':0,'proposal_not_frozen':True,'warning':'CB141 vs LR8 changes both information and model; full pipeline comparison, not pure algorithm effect. A full-Oct vs B fit/cal is not a head-to-head win test.'}
(O/'comparison-calculations.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(single[['evaluation_date','family','logloss','brier','AP','hits','long79_hits','global_long_seats']].to_string(index=False));print(json.dumps(counts))
