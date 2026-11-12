from pathlib import Path
from zipfile import ZipFile
import json,hashlib,numpy as np,pandas as pd
O=Path('E:/app-data/codex/outputs/is6400-round3-team-intake-20261112');A=O/'audit';D=O/'private/extracted/role03/Round3_role03_prediction_v1';K=['customer_unique_id','snapshot_date']
zpath=Path('E:/app-data/codex/outputs/is6400-h04-v02-intake-20261110/H04-role03-v02.zip')
with ZipFile(zpath) as z:
 with z.open('H04_role03_prediction_v0.2/validation_predictions.csv') as f:old=pd.read_csv(f,dtype={'customer_unique_id':'string'})
new=pd.read_csv(D/'january-predictions.csv',dtype={'customer_unique_id':'string'})
g=pd.read_csv(D/'validation_clusters.csv',dtype={'customer_unique_id':'string'})
j=old.merge(new,on=K,validate='one_to_one',suffixes=('_old','_new')).merge(g[K+['cluster_id']],on=K,validate='one_to_one')
assert len(j)==29368 and j.y_old.eq(j.y_new).all()
out=[]
for oldname,newname in [('LogisticRegression','F0_base_unweighted'),('LogisticRegressionWeighted','F0_base_weighted')]:
 a=j['selected_'+oldname+'_top10'].eq(1);b=j[newname+'_selected_10'].eq(1)
 out.append({'old_reference':'H04 v0.2 cached Jan predictions','new_reference':'Round3 role03 F0','weighted':'Weighted' in oldname,'N':len(j),'K_old':int(a.sum()),'K_new':int(b.sum()),'hits_old':int(j.loc[a,'y_old'].sum()),'hits_new':int(j.loc[b,'y_new'].sum()),'list_intersection':int((a&b).sum()),'replaced_each_direction':int((a&~b).sum()),'different_selection_flags':int(a.ne(b).sum()),'max_abs_score_diff':float(abs(j[oldname+'_score']-j[newname+'_score']).max()),'long_seats_old':int((a&j.cluster_id.eq(1)).sum()),'long_seats_new':int((b&j.cluster_id.eq(1)).sum()),'long_hits_old':int(j.loc[a&j.cluster_id.eq(1),'y_old'].sum()),'long_hits_new':int(j.loc[b&j.cluster_id.eq(1),'y_new'].sum()),'cause_not_identified':'Matched counts do not establish identical pipeline execution; dependency/ordering/optimization provenance not fully recorded in new metadata.'})
pd.DataFrame(out).to_csv(A/'h04-v02-vs-round3-F0.csv',index=False)
(A/'h04-reference-source.json').write_text(json.dumps({'path':str(zpath),'sha256':hashlib.sha256(zpath.read_bytes()).hexdigest(),'read_only':True,'new_fits':0,'v04_zip_current_temp_path_missing':True,'scope':'Compare cached Jan v0.2, not a fresh v0.4 replay.'},indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
