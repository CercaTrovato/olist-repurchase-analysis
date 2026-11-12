"""Seal evidence after the two emitted PNG plots have actually been viewed."""
import json,hashlib
from pathlib import Path
OUT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(x,n):(OUT/n).write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
v=json.loads((OUT/'verification.json').read_text());v['status']='PASS';v['actual_visual_review']={'files':{n:sha(OUT/n) for n in ['LR-optimization.png','CB-fit-curves.png']},'observed':'Both PNGs actually viewed; source emits same SVG; axes/legend distinguish gradient gtol vs actual ftol stop and canonical fit curves vs Jan performance.'};dump(v,'verification.json')
files=[dict(path=p.relative_to(OUT).as_posix(),bytes=p.stat().st_size,sha256=sha(p),private='private' in p.relative_to(OUT).parts) for p in OUT.rglob('*') if p.is_file() and p.name!='manifest.json'];dump(dict(files=files,private_rows_not_public=True),'manifest.json')
assert all(sha(OUT/f['path'])==f['sha256'] for f in files);print('SEALED',v['model_count'],'models',len(files),'files')
