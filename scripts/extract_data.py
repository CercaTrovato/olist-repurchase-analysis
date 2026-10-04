"""Extract and verify the bundled official archive. Requires only Python stdlib."""
from pathlib import Path
import hashlib,json,os,zipfile

ROOT=Path(__file__).resolve().parents[1]
data=ROOT/'data'
manifest=json.loads((data/'source-manifest.json').read_text(encoding='utf-8'))
archive=data/'olist-v2.zip'
if hashlib.sha256(archive.read_bytes()).hexdigest()!=manifest['zip_sha256']:
    raise ValueError('Archive SHA-256 differs. Download the repository again.')
raw=data/'raw';raw.mkdir(exist_ok=True)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None,'ZIP CRC failed'
    assert set(z.namelist())=={i['name'] for i in manifest['files']}
    for item in manifest['files']:
        target=(raw/item['name']).resolve()
        if target.parent!=raw.resolve():raise ValueError('Unsafe archive path')
        content=z.read(item['name'])
        if hashlib.sha256(content).hexdigest()!=item['sha256']:raise ValueError(item['name'])
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest()!=item['sha256']:
                raise ValueError('Existing raw file was changed; preserve it and resolve manually: '+item['name'])
        else:
            tmp=target.with_suffix('.partial')
            with tmp.open('xb') as f:
                f.write(content);f.flush();os.fsync(f.fileno())
            os.replace(tmp,target)
        print('OK',item['name'])
print('All 9 CSV files verified in data/raw. Never edit the originals.')
