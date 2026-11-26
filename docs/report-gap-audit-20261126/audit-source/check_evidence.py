from pathlib import Path,PurePosixPath
import json,subprocess,hashlib,io,re,ast,posixpath
import pandas as pd
S=Path(__file__).parent;C=S/'source-cache';R=S/'repo';V=Path('D:/上课资料/CityU')
sys_path=str(V/'_meta/tools');import sys;sys.path.insert(0,sys_path);from safe_write import atomic_write
inv=json.loads((S/'inventory.json').read_text(encoding='utf-8'));by={x['path']:x for x in inv['files']}
allfiles=list(by.values());payload=subprocess.run(['git','-C',str(R),'cat-file','--batch'],input=('\n'.join(x['blob'] for x in allfiles)+'\n').encode(),stdout=subprocess.PIPE,check=True).stdout
off=0;hashes={}
for x in allfiles:
 end=payload.index(b'\n',off);size=int(payload[off:end].split()[2]);b=payload[end+1:end+1+size];off=end+1+size+1;hashes[x['path']]=hashlib.sha256(b).hexdigest()
def read(p):return (C/p).read_text(encoding='utf-8-sig')
def df(p):return pd.read_csv(C/p)
manifests=[]
for p in C.rglob('public-evidence-manifest.json'):
 d=json.loads(p.read_text(encoding='utf-8'));files=d.get('files',{});bad=[];missing=[]
 if not isinstance(files,dict):continue
 for name,want in files.items():
  if not isinstance(want,str):continue
  actual=name if name in by else posixpath.normpath((p.parent.relative_to(C)/name).as_posix())
  if actual not in by:missing.append(name)
  elif hashes[actual]!=want:bad.append({'path':actual,'expected':want,'actual':hashes[actual]})
 manifests.append({'manifest':p.relative_to(C).as_posix(),'entries':len(files),'mismatch':bad,'missing':missing})
checks=[]
for rel in ['research/team-round3-20261112/members/role03/january-comparison.csv','research/team-round3-20261112/members/role03/group-model-comparison.csv','research/role05-mainline-20261113/audit/capacity-all-models.csv','research/frozen-temporal-test-20261125/metrics.csv']:
 d=df(rel);bad=[]
 for i,x in d.iterrows():
  k=x.get('K',x.get('global_K'));h=x.get('hits',x.get('TP'));n=x.get('N');p=x.get('positive_count')
  for col,expected in [('precision',h/k if k else None),('recall',h/p if p else None)]:
   if col in d and expected is not None and abs(x[col]-expected)>1e-10:bad.append({'row':int(i)+2,'field':col})
  if 'cluster_0_selected' in d and sum(x[f'cluster_{j}_selected'] for j in range(3))!=k:bad.append({'row':int(i)+2,'field':'group_places_sum'})
  if 'cluster_0_hits' in d and sum(x[f'cluster_{j}_hits'] for j in range(3))!=h:bad.append({'row':int(i)+2,'field':'group_hits_sum'})
  if all(c in d for c in ['TP','FP','FN','TN']):
   if sum(x[c] for c in ['TP','FP','FN','TN'])!=n or x.TP+x.FN!=p or x.TP+x.FP!=k:bad.append({'row':int(i)+2,'field':'confusion_totals'})
 checks.append({'path':rel,'rows':len(d),'arithmetic_errors':bad})
py=[]
for rel in ['research/team-round3-20261112/members/role03/run_round3.py','research/team-round3-20261112/members/role03/run_group_models.py','research/frozen-temporal-test-20261125/score_frozen.py','research/final-validation-20261112/data/run_data.py','research/final-validation-20261112/probability/run_probability.py','research/final-validation-20261112/value/run_value.py']:
 if not (C/rel).exists():continue
 tree=ast.parse(read(rel));calls=[n.attr for n in ast.walk(tree) if isinstance(n,ast.Attribute) and n.attr in ['fit','fit_transform','set_params','partial_fit']]
 abs_paths=re.findall(r"[DE]:[/\\][^'\"\n]+",read(rel));py.append({'path':rel,'ast_parse_ok':True,'fit_call_sites':calls,'absolute_path_literals':abs_paths[:12]})
families=[]
for fam in inv['research_families']:
 fs=[x for x in inv['files'] if x['path'].startswith('research/'+fam+'/')];families.append({'family':fam,'files':len(fs),'csv':sum(x['ext']=='.csv' for x in fs),'svg':sum(x['ext']=='.svg' for x in fs),'png':sum(x['ext']=='.png' for x in fs),'py':sum(x['ext']=='.py' for x in fs),'unique_image_blobs':len({x['blob'] for x in fs if x['ext'] in ['.png','.svg']})})
targets=['research/team-round3-20261112/members/role03/run_round3.py','research/team-round3-20261112/members/role03/run-metadata.json','research/role05-mainline-20261113/README.md','research/role02-v11-20261113/README.md','research/final-validation-20261112/README.md','research/final-validation-20261112/data/README.md','research/frozen-temporal-test-20261125/score_frozen.py','research/frozen-temporal-test-20261125/README.md','docs/03-methodology.md']
quotes=[]
pattern=re.compile('Not run|group_models|全部已验收|硬编码|不能采用|缺口可关闭|可关闭|80%|20%|先前|三期|overlap|calibrat|before|set_params|暂无|标签此前|已完成|2,937|50/|65|log1p|low_score|class_weight|May|27|20–25|最优|全量|metadata',re.I)
for rel in targets:
 for i,line in enumerate(read(rel).splitlines(),1):
  if pattern.search(line):quotes.append({'path':rel,'line':i,'text':line[:340]})
result={'remote_commit':inv['remote_commit'],'manifest_checks':manifests,'arithmetic_checks':checks,'code_structure_checks':py,'research_inventory':families,'evidence_quotes':quotes,'git_file_sha256':hashes}
atomic_write(str(S/'evidence-check.json'),json.dumps(result,ensure_ascii=False,indent=2)+'\n')
pd.DataFrame(families).to_csv(S/'experiment-inventory.csv',index=False,encoding='utf-8',lineterminator='\n')
print(json.dumps({'manifest_checks':[{**m,'mismatch':len(m['mismatch']),'missing':len(m['missing'])} for m in manifests],'arithmetic_checks':checks,'research_inventory':families,'code_structure_checks':py},ensure_ascii=False,indent=2))
