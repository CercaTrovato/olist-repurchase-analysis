from pathlib import Path
import json,subprocess,hashlib,zipfile,re
import pandas as pd
from lxml import etree as E
S=Path(__file__).parent;R=S/'repo';C=S/'source-cache';V=Path('D:/上课资料/CityU');A=V/'IS6400_Business_Data_Analytics/assignment/graded/A06-group-project'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
inv=json.loads((S/'inventory.json').read_text(encoding='utf-8'));idx={x['path']:x for x in inv['files']}
assets=['research/team-round3-20261112/figures/01-team-models-and-long79.png','research/role05-mainline-20261113/figures/02-role05-paired-changes.png','research/final-validation-20261112/figures/01-rolling-probability.png','research/final-validation-20261112/figures/02-january-hits-value-tradeoff.png','research/common-comparison-20261112/statistics/figures/calibration-base8-weightedLR.png','research/ae-ablation-20261112/statistics/blocks-canonical-conditional-intervals.png']
for n,rel in enumerate(assets,1):(S/f'sample-figure-{n}.png').write_bytes(subprocess.check_output(['git','-C',str(R),'show','origin/main:'+rel]))
sources=[A/'work/presentation-20261125/IS6400_SixSigma_Classroom_20261125.pptx',A/'work/presentation-20261125/IS6400_SixSigma_Classroom_20261125.pdf',V/'IS6400_Business_Data_Analytics/course_files_export/IS6400 Project Guideline.pdf',Path('E:/app-data/codex/outputs/is6400-weighted-april-20261110/weighted-lr8.joblib'),Path('E:/app-data/codex/outputs/is6400-round3-20261111/baselines/private/LR8.joblib')]
hashes={str(p):sha(p) for p in sources}
slides={}
with zipfile.ZipFile(sources[0]) as z:
 ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
 for n in [3,6,7,8,9,10,11,12,13,14,15]:slides[str(n)]='\n'.join(''.join(x.xpath('.//a:t/text()',namespaces=ns)) for x in E.fromstring(z.read(f'ppt/slides/slide{n}.xml')).xpath('//a:p',namespaces=ns))
metrics=pd.read_csv(C/'research/frozen-temporal-test-20261125/metrics.csv');top=metrics.loc[metrics.top_fraction.eq(.1)] if 'top_fraction' in metrics else metrics.loc[metrics.fraction.eq(.1)]
print('test columns',metrics.columns.tolist());print(top[['snapshot_date','method','N','positive_count','K','hits']].to_string(index=False))
assert '65' in slides['14'] and '64' in slides['14'] and '67' in slides['14'] and '59' in slides['14'] and '53' in slides['14']
assert all(x in slides['12'] for x in ['1,469','2,937','5,874','75'])
paths=[]
for rel in ['research/final-validation-20261112/probability/probability-manifest.json','research/final-validation-20261112/data/data-manifest.json']:
 source=C/rel
 if not source.exists():source=Path('E:/app-data/codex/outputs/is6400-final-validation-20261112')/Path(rel).relative_to('research/final-validation-20261112')
 if not source.exists():continue
 d=json.loads(source.read_text(encoding='utf-8'))
 def walk(v):
  if isinstance(v,dict):
   for x in v.values():walk(x)
  elif isinstance(v,list):
   for x in v:walk(x)
  elif isinstance(v,str) and re.match(r'^[DE]:[/\\]',v):paths.append(v)
 walk(d)
record={'original_source_sha256':hashes,'ppt_source_matches_git':hashes[str(sources[0])]==json.loads((S/'evidence-check.json').read_text(encoding='utf-8'))['git_file_sha256']['slides/classroom-20261125/IS6400_SixSigma_Classroom_20261125.pptx'],'selected_slide_text':slides,'figure_visual_sample':assets,'private_artifact_paths_checked':len(set(paths)),'private_artifact_paths_present':sum(Path(p).exists() for p in set(paths)),'private_artifact_missing':[p for p in set(paths) if not Path(p).exists()],'row_score_table_for_plotting_present':Path('E:/app-data/codex/outputs/is6400-frozen-test-20261125/private/customer-predictions.csv').is_file()}
(S/'supplement-check.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k not in ['selected_slide_text','private_artifact_missing','original_source_sha256']},ensure_ascii=False,indent=2))
