from pathlib import Path
import pandas as pd,numpy as np,json
O=Path('E:/app-data/codex/outputs/is6400-round3-team-intake-20261112');D=O/'private/extracted/role03/Round3_role03_prediction_v1';K=['customer_unique_id','snapshot_date']
a=pd.read_csv(O/'private/replayed-base-scores.csv');b=pd.read_csv(D/'january-predictions.csv');g=pd.read_csv(D/'validation_clusters.csv');j=a.merge(b,on=K,validate='one_to_one').merge(g[K+['cluster_id']],on=K,validate='one_to_one')
r=json.loads((O/'audit/base-replay.json').read_text(encoding='utf-8'))
for v in r['results']:
 s=j[v['replay']+'_score'].to_numpy();o=np.lexsort((j.customer_unique_id.astype(str).to_numpy(),-s));sel=np.zeros(len(j),bool);sel[o[:2937]]=True;prior=j.F0_base_weighted_selected_10.eq(1).to_numpy()
 v.update(list_intersection_to_R3=int((sel&prior).sum()),different_flags_to_R3=int((sel!=prior).sum()),long_seats=int((sel&j.cluster_id.eq(1)).sum()),long_hits=int(j.loc[sel&j.cluster_id.eq(1),'y'].sum()))
(O/'audit/base-replay.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(r['results'],ensure_ascii=False,indent=2))
