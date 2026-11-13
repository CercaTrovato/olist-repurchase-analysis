"""Bounded verification of member Role02 v1.1; no member script execution."""
from pathlib import Path
import json,hashlib,math
import pandas as pd,numpy as np
O=Path(__file__).resolve().parent;N=O/'private/extracted/Round3_role02';P=Path('E:/app-data/codex/outputs/is6400-round3-team-intake-20261112/private/extracted/role02/Round3_role02');A=O/'audit';A.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rd(p):return pd.read_csv(p,encoding='utf-8-sig',dtype={'scope':str})
checks=[]
for line in (N/'CHECKSUMS.sha256').read_text(encoding='utf-8-sig').splitlines():
 if not line.strip():continue
 h,name=line.split(None,1);p=N/name.strip().lstrip('*');checks.append({'file':name.strip(),'exists':p.is_file(),'hash_match':p.is_file() and sha(p)==h})
assert all(v['hash_match'] for v in checks)
pd.DataFrame(checks).to_csv(A/'package-checksums.csv',index=False)
key=['candidate_id','scope'];full=rd(N/'training-feature-evidence.csv');prior=rd(P/'training-feature-evidence.csv');corrected=rd(Path('E:/app-data/codex/outputs/is6400-round3-team-intake-20261112/audit/role02-evidence-recomputed-corrected.csv'))
rows=[];changed={};model_fits=0
for label,rel in [('full','training-feature-evidence.csv'),('smoke','smoke/training-feature-evidence.csv')]:
 new=rd(N/rel).sort_values(key).reset_index(drop=True);old=rd(P/rel).sort_values(key).reset_index(drop=True)
 assert new.shape==old.shape and new[key].equals(old[key])
 for c in new:
  if c in ['d_se','d_ci_lo','d_ci_hi']:continue
  if pd.api.types.is_numeric_dtype(new[c]):assert np.allclose(new[c],old[c],atol=1e-12,rtol=1e-12,equal_nan=True),(label,c)
  else:assert new[c].fillna('').equals(old[c].fillna('')),(label,c)
 changes={c:int((~np.isclose(new[c],old[c],atol=1e-12,rtol=1e-12,equal_nan=True)).sum()) for c in ['d_se','d_ci_lo','d_ci_hi']};changed[label]=changes
 for _,r in new.iterrows():
  n1=int(r.positives_nonmissing);n0=int(r.negatives_nonmissing);d=float(r.cohens_d)
  se=math.sqrt((n1+n0)/(n1*n0)+d*d/(2*(n1+n0-2))) if math.isfinite(d) and min(n1,n0)>=2 else np.nan
  assert np.isclose(r.d_se,se,atol=1e-12,rtol=1e-12,equal_nan=True)
  assert np.isclose(r.d_ci_lo,d-1.96*se,atol=1e-12,rtol=1e-12,equal_nan=True) and np.isclose(r.d_ci_hi,d+1.96*se,atol=1e-12,rtol=1e-12,equal_nan=True)
  rows.append({'scope_set':label,'candidate_id':r.candidate_id,'scope':r.scope,'nonmissing_positive':n1,'nonmissing_negative':n0,'SE_recomputed':se,'SE_given':r.d_se,'SE_match':True,'point_and_AUC_unchanged':True})
pd.DataFrame(rows).to_csv(A/'interval-recalculation.csv',index=False)
j=full.merge(corrected[key+['corrected_d_se','corrected_d_ci_lo','corrected_d_ci_hi']],on=key,validate='one_to_one')
delta={c:float(abs(j[c]-j['corrected_'+c]).max()) for c in ['d_se','d_ci_lo','d_ci_hi']}
assert len(j)==56 and all(v<1e-12 for v in delta.values())
stable=['candidate-screening.csv','group-comparison.csv','field-correlation.csv','tables/r3_fold_selection.csv','tables/r3_january_direction.csv','tables/r3_retained_fields.csv','tables/r3_input_checks.csv','tables/r3_asof_verification.csv','scripts/r3_build_candidates.py','scripts/r3_inputs.py','scripts/r3_plots.py','scripts/r3_verify.py','scripts/run_all.py']
stable_checks=[]
for n in stable:assert sha(N/n)==sha(P/n),n;stable_checks.append({'file':n,'same_sha256':True})
pd.DataFrame(stable_checks).to_csv(A/'unchanged-critical-files.csv',index=False)
newdef=rd(N/'candidate-definitions.csv');olddef=rd(P/'candidate-definitions.csv');assert newdef.drop(columns=['note']).equals(olddef.drop(columns=['note']))
newfit=json.loads((N/'tables/r3_transform_fit.json').read_text());oldfit=json.loads((P/'tables/r3_transform_fit.json').read_text());newfit.pop('spec_version');oldfit.pop('spec_version');assert newfit==oldfit
spec=json.loads((N/'feature-spec.json').read_text());prev=json.loads((P/'feature-spec.json').read_text())
for keyname in ['groups','retained_flags','train_N','train_positives','train_snapshot','validation_snapshot']:assert spec[keyname]==prev[keyname],keyname
rec={'status':'PASS_TARGETED_ROLE02_V11_REPAIR','package_hash_checks':len(checks),'all_checksums_match':True,'actual_package_role':2,'contains_role03_new_model_or_predictions':False,'rows_full':len(full),'rows_smoke':len(rd(N/'smoke/training-feature-evidence.csv')),'changed_interval_cells_by_column':changed,'point_estimates_and_AUC_changed':0,'critical_files_unchanged':len(stable),'match_previous_independent_corrected_max_abs_diff':delta,'feature_formulas_and_selections_unchanged':True,'numeric_transform_fit_same_except_version':True,'original_private_row_tables_not_supplied':True,'private_original_table_sha_not_independently_matched':True,'new_model_fits':0,'new_april_predictions':0,'dates_in_member_handoff_not_user_authorization':True,'closed':'Role02 20-row CI support denominator and related disclosure revision','still_open':['Role02 proposed combinations not tested by Role03','Role03 CV/metadata clarification','Role05 CI/attribution/version explanation','Specific local final model and primary metric pending user later']}
(A/'verification.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(rec,ensure_ascii=False,indent=2))
