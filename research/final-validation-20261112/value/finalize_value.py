"""Aggregate extra tail diagnostics and refresh artifact hashes; no fits or scores."""
from pathlib import Path
import json, hashlib, math
import pandas as pd

ROOT=Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    manifest=json.loads((ROOT/'value-manifest.json').read_text(encoding='utf-8'))
    rows=[]
    for cell,entry in manifest['cells'].items():
        truth=pd.read_csv(entry['truth_path']); g=truth.future_gmv; positive=g[g>0]; k=math.ceil(len(positive)*.01)
        rows.append({'evaluation_date':cell.split('__')[0],'strategy':cell.split('__')[1],
            'population_N':len(g),'positive_customer_N':len(positive),
            'max_customer_G':float(g.max()),'max_customer_G_share':float(g.max()/g.sum()),
            'positive_top1pct_K':k,'positive_top1pct_G':float(positive.nlargest(k).sum()),
            'positive_top1pct_G_share':float(positive.nlargest(k).sum()/g.sum()),
            'population_top1pct_K':math.ceil(len(g)*.01),
            'population_top1pct_G_share':float(g.nlargest(math.ceil(len(g)*.01)).sum()/g.sum())})
    pd.DataFrame(rows).to_csv(ROOT/'amount-tail-positive-concentration.csv',index=False)
    evidence={'status':'ACTUALLY_VIEWED','figures':[],
        'checks':['all three PNG figures visually read at final version','all six panels per figure contain six frozen rules plus random expectation',
                  '100% endpoints converge to 100% of actual GMV','titles and caveat text separated after targeted layout repair',
                  'axes, units, all seven frozen capacities and legends visible','SVG uses same matplotlib figure source as inspected PNG'],
        'scope':'three aggregate-only figures; no customer labels; visual rendering is not causal validation'}
    for family in ['p_wlr','p_ulr','p_catboost']:
        evidence['figures'].append({'family':family,**{ext:{'path':f'figures/capacity-gmv-{family}.{ext}',
            'sha256':sha(ROOT/f'figures/capacity-gmv-{family}.{ext}')} for ext in ['png','svg']}})
    (ROOT/'actual-view-evidence.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    manifest['artifacts']={str(p.relative_to(ROOT)):sha(p) for p in ROOT.rglob('*') if p.is_file() and p.name!='value-manifest.json'}
    manifest['public_allowlist']=[str(p.relative_to(ROOT)) for p in ROOT.iterdir() if p.is_file() and p.suffix in ['.py','.md','.csv']]+[str(p.relative_to(ROOT)) for p in (ROOT/'figures').iterdir()]
    manifest['private_directories']=['private','__pycache__']
    manifest['privacy_note']='Never publish value-manifest or stage manifests: absolute private file paths and per-cell artifacts. Public is explicit aggregate/code/guide/figure allowlist only.'
    (ROOT/'value-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    print('Finalized aggregate tail diagnostics, final visual evidence, and all artifact hashes')

if __name__=='__main__': main()
