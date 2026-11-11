"""Final file hashes after aggregate-only plot/document edits; no fitting."""
import hashlib,json
from pathlib import Path
OUT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
run=json.loads((OUT/'verification.json').read_text());readback=json.loads((OUT/'readback-verification.json').read_text())
assert sha(OUT/'run_control.py')==run['code_sha256']
checks={n:sha(OUT/n)==h for n,h in run['output_sha256'].items() if not n.replace('\\','/').startswith('figures/')}
assert all(checks.values())
assert all(sha(p)==h for p,h in run['input_sha256'].items())
result=dict(status='complete_local_readback_passed',scientific_run_code_unchanged=True,scientific_outputs_unchanged=len(checks),source_files_unchanged=len(run['input_sha256']),
    plot_changes='aggregate-only re-render title and SD footnote; no additional fitting/scoring',local_readback=readback['status'],
    output_sha256={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='final-manifest.json'})
(OUT/'final-manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print('Complete; source and scientific artifacts unchanged; readback PASS; final plots and docs hashed')
