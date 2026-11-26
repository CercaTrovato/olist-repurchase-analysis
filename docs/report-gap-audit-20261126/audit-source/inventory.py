from pathlib import Path
import subprocess,json,hashlib,collections,sys
S=Path(__file__).parent;R=S/'repo';V=Path('D:/上课资料/CityU');CACHE=S/'source-cache'
sys.path.insert(0,str(V/'_meta/tools'));from safe_write import atomic_write
head=subprocess.check_output(['git','-C',str(R),'rev-parse','origin/main']).decode().strip()
raw=subprocess.check_output(['git','-C',str(R),'-c','core.quotepath=false','ls-tree','-rl','-z','origin/main']).decode('utf-8')
rows=[]
for line in raw.split('\0'):
 if not line:continue
 meta,path=line.split('\t',1);m,typ,blob,size=meta.split();rows.append({'path':path,'blob':blob,'bytes':int(size),'ext':Path(path).suffix.lower()})
selected=[x for x in rows if x['path'].startswith(('research/','docs/','slides/classroom-20261125/')) and x['ext'] in {'.md','.py','.json','.csv','.txt','.yml','.yaml','.toml'} and x['bytes']<1500000]
p=subprocess.run(['git','-C',str(R),'cat-file','--batch'],input=('\n'.join(x['blob'] for x in selected)+'\n').encode(),stdout=subprocess.PIPE,check=True)
b=p.stdout;offset=0
for x in selected:
 end=b.index(b'\n',offset);header=b[offset:end].decode().split();length=int(header[2]);data=b[end+1:end+1+length];offset=end+1+length+1
 assert len(data)==x['bytes'];x['sha256']=hashlib.sha256(data).hexdigest();dest=CACHE/x['path'];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
summary={'remote_commit':head,'tracked_files':len(rows),'cached_text_files':len(selected),'extensions':dict(collections.Counter(x['ext'] for x in rows)),'research_families':dict(collections.Counter(x['path'].split('/')[1] for x in rows if x['path'].startswith('research/'))),'files':rows,'cached':selected}
atomic_write(str(S/'inventory.json'),json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ['files','cached']},ensure_ascii=False,indent=2))
for x in selected:
 if Path(x['path']).name=='README.md' and len(Path(x['path']).parts)<4:print(x['path'])
