"""Finish metadata privacy paths and bind the final source/readback hashes."""
import hashlib,json
from pathlib import Path
OUT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
m=json.loads((OUT/'data-manifest.json').read_text())
assert m['status']=='READY'
v=json.loads((OUT/'independent-readback.json').read_text());assert v['status']=='PASS'
m['group_model_path']='private/frozen-group-model.json'
m['independent_readback_path']='independent-readback.json'
m['independent_readback_sha256']=sha(OUT/'independent-readback.json')
m['group_model_sha256']=sha(OUT/m['group_model_path'])
m['privacy']='All private/ files including customer-snapshot rows, future outcomes and model/scaler numeric parameters remain private; publish only exact support/date/coverage/hash/code allowlists'
h=json.loads((OUT/'sourcehash.json').read_text())
h[str(OUT/'run_data.py')]=sha(OUT/'run_data.py')
h[str(OUT/'verify_data.py')]=sha(OUT/'verify_data.py')
h[str(OUT/'finalize_data.py')]=sha(OUT/'finalize_data.py')
save(OUT/'sourcehash.json',h);save(OUT/'data-manifest.json',m)
save(OUT/'outputhash.json',{str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='outputhash.json'})
print(json.dumps({'status':m['status'],'manifest_sha256':sha(OUT/'data-manifest.json'),'readback':v['status'],'sourcehash_sha256':sha(OUT/'sourcehash.json'),'plan_sha256':h[str(OUT.parent/'task_plan.md')]}))
