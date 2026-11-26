"""Rebuild metadata from saved evidence without fitting a model.
The regeneration environment is not asserted to be the original training environment.
"""
from pathlib import Path
import json,hashlib,platform
import numpy as np,pandas as pd,sklearn
METHODS=['F0_global_weighted','B_global_with_cluster','C_segmented_group2_global_fallback']
VARIANTS={'F0_base':[],'F1_delivery':['delivered_known_n','delivery_days_mean','late_delivery_share'],'F2_review':['review_known_n','review_score_mean','low_review_share']}
def fingerprint(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build_metadata(source,kind,invocation_mode="metadata_only"):
 source=Path(source);names=['january-comparison.csv','cv-summary.csv','group-model-comparison.csv','group-cv-summary.csv'];artifacts={}
 for name in names:
  p=source/name
  if p.is_file():artifacts[name]={'sha256':fingerprint(p),'rows':len(pd.read_csv(p))}
 groups=[]
 if (source/'group-model-comparison.csv').is_file():groups=sorted(pd.read_csv(source/'group-model-comparison.csv').method.unique().tolist())
 cv={'method':'StratifiedKFold','folds':5,'shuffle':True,'random_state':2026,'fit_scope':'October training snapshot only','january_role':'development and candidate comparison, not an independent blind test'}
 base={'schema':'role03-evidence-metadata-v2','round':'round3','train_snapshot':'2017-10-01','validation_snapshot':'2018-01-01','invocation_mode':invocation_mode,'execution_scope':('metadata regeneration from saved results; no fit/predict executed in this invocation' if invocation_mode=='metadata_only' else 'driver completed its declared training/scoring before metadata serialization; other saved results retain separate fingerprints'),'original_training_environment':'not reconstructed from this regeneration','regeneration_environment':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__},'cv':cv,'ranking':'score descending, customer_unique_id ascending for ties','capacities':[.05,.10,.20],'model_settings':{'C':1.,'class_weight':'balanced where weighted, otherwise None','penalty':'l2','solver':'lbfgs','tol':.0001,'max_iter':2000,'random_state':2026},'saved_artifacts':artifacts,'group_models':{'status':'saved_results_available' if set(METHODS).issubset(groups) else 'saved_results_incomplete_or_absent','methods':groups,'new_fits_in_this_regeneration':0,'representation_scope':'H05 mapping fitted once on all October; conditional group CV. Imputation/scaling/encoding and LR fit within each fold; clustering is not refitted per fold.'}}
 if kind=='base':base.update(feature_version='round3-role01-time-v1',variants=VARIANTS,models=['LogisticRegression','LogisticRegressionWeighted'])
 elif kind=='group':
  base['methods']={'F0_global_weighted':'Global weighted logistic regression','B_global_with_cluster':'Global weighted LR with categorical cluster_id','C_segmented_group2_global_fallback':'Separate weighted LR for groups0/1, global model for group2; fallback to global if a training group has one class'}
  base['cv']['representation_scope']=base['group_models']['representation_scope']
  base['cv']['selection_metric']='January Top10% hits informed development comparison. CV summaries are separate internal diagnostics.'
 else:raise ValueError('kind must be base or group')
 return base
def write_metadata(source,output,kind,invocation_mode="metadata_only"):
 output=Path(output);output.mkdir(parents=True,exist_ok=True);name='run-metadata.json' if kind=='base' else 'group-model-metadata.json';text=json.dumps(build_metadata(source,kind,invocation_mode),ensure_ascii=False,indent=2)+'\n';target=output/name;temp=target.with_suffix('.json.partial')
 if temp.exists():raise FileExistsError(temp)
 with temp.open('x',encoding='utf-8',newline='\n') as f:f.write(text)
 temp.replace(target);return target
def metadata_cli(kind):
 import argparse
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--metadata-only',action='store_true',required=True);parser.add_argument('--source-dir',type=Path,default=Path(__file__).parent);parser.add_argument('--output-dir',type=Path,required=True);a=parser.parse_args();p=write_metadata(a.source_dir,a.output_dir,kind);print(str(p))
