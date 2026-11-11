"""Maintenance-only correction of regenerated common-long-slice narrative; no retraining."""
from pathlib import Path
OUT=Path(__file__).resolve().parent
p=OUT/'run_features.py';s=p.read_text(encoding='utf-8')
if 'LONG_CLUSTER=1\n' not in s:s=s.replace("H02=BASE+", "LONG_CLUSTER=1\nH02=BASE+")
s=s.replace('mask=jan.cluster_id.eq(1).to_numpy()', 'mask=jan.cluster_id.eq(LONG_CLUSTER).to_numpy()')
s=s.replace('assert jan.cluster_id.eq(2).sum()==703', 'assert jan.cluster_id.eq(LONG_CLUSTER).sum()==12330;assert int(jan.loc[jan.cluster_id.eq(LONG_CLUSTER),\'y\'].sum())==90')
p.write_text(s,encoding='utf-8')
p=OUT/'finalize_features.py';s=p.read_text(encoding='utf-8')
if 'LONG_CLUSTER=1\n' not in s:s=s.replace('OUT=Path(__file__).resolve().parent','OUT=Path(__file__).resolve().parent\nLONG_CLUSTER=1')
s=s.replace('scores.cluster_id.to_numpy()[order]==1','scores.cluster_id.to_numpy()[order]==LONG_CLUSTER')
s=s.replace('AUC 并非最高，久单79也未超过基线。','AUC 并非最高；共同久单 cluster_id=1 的固定79捕获以本页表格为准，不能沿用旧 cluster2 的解释。')
p.write_text(s,encoding='utf-8')
assert '久单79也未超过基线' not in s
compile((OUT/'run_features.py').read_text(encoding='utf-8'),'run_features.py','exec');compile(s,'finalize_features.py','exec')
print('P2 generators corrected; common LONG_CLUSTER=1; no model/score changed')
