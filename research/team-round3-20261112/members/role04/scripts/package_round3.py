"""Allowlisted aggregate handoff packaging; no analysis/model rerun."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import csv,hashlib,json,shutil,sys,xml.etree.ElementTree as ET
R=Path(__file__).resolve().parents[1]; S=R/'outputs/round3_role04'
source=Path(sys.argv[1]) if len(sys.argv)>1 else Path('E:/xwechat_files/PRIVATE_WECHAT_ID/msg/file/2026-11')
name='Role04_Round3_2026-11-12'; D=R/'deliverables'/name
if D.exists() or D.with_suffix('.zip').exists(): raise SystemExit('Refusing to overwrite existing delivery')
sha=lambda b:hashlib.sha256(b).hexdigest()
z=ZipFile(source/'Round3_role01_time_v1.zip'); provenance=[]
for n in ['field-time-audit.csv','time-window-audit.csv']:
 b=(source/n).read_bytes();assert b==z.read('Round3_role01_time_v1/'+n),n
 provenance.append(dict(source=n,sha256=sha(b),check='external CSV byte-identical to ZIP member'))
provenance.append(dict(source='Round3_role01_time_v1.zip',sha256=sha((source/'Round3_role01_time_v1.zip').read_bytes()),check='read-only reference; ZIP and private features excluded'))
def write(p,text):
 p=D/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')
def table(path,rows):
 with path.open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
files=[p for p in S.rglob('*') if p.is_file() and p.parts[-2]!='reproduce' and p.suffix in ['.md','.csv','.json','.png','.svg']]
for p in files:
 q=D/p.relative_to(S);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
for n in ['field-time-audit.csv','time-window-audit.csv']:
 q=D/'audit/role01'/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes((source/n).read_bytes())
table(D/'audit/role01/source-hashes.csv',provenance)
append='''

## Role01 时间审计引用（本次打包补充）

已对照 Round3_role01_time_v1.zip 的交接说明及 field-time-audit.csv、time-window-audit.csv；外部两份CSV与ZIP内成员逐字节一致，来源SHA256见audit/role01/source-hashes.csv。以下是引用Role01结论，本轮未独立重算时间审计，未引入其逐客户特征表。

- 十月训练标签于2017-12-30 00:00日历成熟；日历成熟不保证源记录已完整入库。
- 一月为开发验证；四月为已见窗口回测，均不得包装成新增盲测。
- 2018-05-01、2018-06-01候选目标分别与已见目标重叠60、29天，仅适合作锁定方法后的补充时间敏感性检查。
- 2018-06-30快照的90天窗口为[2018-06-30,2018-09-28)，超出H02工作观察上界2018-09-01共27天，不用于完整90天标签评价。
- 字段审计要求送达及评价答复严格早于预测日；预计送达承诺依赖事前可知且未回写假设，最终状态不可作为当时输入。本交付未新增这些字段。

**交付状态：可交汇总材料，非全部核验完成。H04 v0.4预测包缺失，模型数字是旧汇总复用、版本未核；内容试验尚未开展；历史客户池不等于实际可触达人群。**

本ZIP不含复跑所需的私有输入，不能独立完整复跑。请先阅读reproduce/RUN.md。原outputs成果保持不变，仅在本交付副本补充说明。
'''
with (D/'docs/HANDOFF.md').open('a',encoding='utf-8') as f:f.write(append)
for n in ['run_round3.py','package_round3.py']:
 q=D/'scripts'/n;q.parent.mkdir(exist_ok=True);shutil.copy2(R/'scripts'/n,q)
write('reproduce/RUN.md','''# 运行与输入边界

此ZIP为汇总交付，不是独立完整复跑包。没有原始数据、客户键、逐人分数或local_data。不要直接在解压目录运行分析脚本，否则会缺输入。

将scripts/run_round3.py放到已有项目根目录下的scripts中，准备以下外部输入（相对项目根目录）：

- data/H02_candidate_v2.zip：内含snapshot_features.csv、snapshot_labels.csv；指纹见audit/reference-input-versions.csv。
- outputs/H05-km3-v1/local_data/validation_clusters.csv：原H05逐人群号。
- outputs/feedback_round1/local_data/train_audit.local.csv：首轮既有训练群号与特征标签。
- outputs/feedback_round1/local_data/historical_pairs_train.local.csv、historical_pairs_validation.local.csv：历史客户品类缓存。只复用，不在本脚本重建。
- outputs/feedback_round1/results/segment-errors-recomputed.csv：旧模型汇总。本包不重复带入旧轮成果；需从既有项目取得。

所有实际使用输入哈希见audit/source-hashes.csv。H04 v0.4未作为本脚本输入，脚本运行成功不代表该版本验证成功。要重建历史品类缓存需旧轮脚本及原始Olist表，均不含在本包。

Python 3.12；依赖pandas、numpy、scipy、matplotlib。已记录版本见audit/environment.json；scipy版本见requirements.txt。字体依赖C:/Windows/Fonts/msyh.ttc，其他平台需修改为可用中文字体。

```powershell
# 在已有项目根目录执行；使用已安装上述依赖的Python环境
python scripts/run_round3.py
```

本机可用py -3.12，且需设置$env:PYTHONPATH='MEMBER_HOME/Dev\\work\\Lib\\site-packages'。脚本仅重算聚合和图表，不训练模型或聚类；会刷新outputs/round3_role04的生成文件，因此先备份该目录。不会更新本次交付ZIP，也不自动加入交接附录。

本次打包没有运行分析脚本，所有画像及样本量文件按字节复制。打包源码为scripts/package_round3.py，参数是Role01附件所在目录；从原项目运行，目标已存在会拒绝覆盖。脚本中的日期为本次交付日期。
''')
env=json.loads((S/'audit/environment.json').read_text());import scipy
write('reproduce/requirements.txt','\n'.join(f'{k}=={env[k]}' for k in ['pandas','numpy','matplotlib'])+'\nscipy=='+scipy.__version__+'\n')
write('README.md','''# Role04 第三轮交付｜2026-11-12

**部分核验完成：H04 v0.4预测包缺失；模型数字为旧汇总复用、版本未核。内容试验尚未开展。历史客户池不等于可触达人群。**

先读docs/HANDOFF.md。2号使用results/category-support.csv及theme-candidates.csv；5号使用profile-summary.csv、audit核验及指纹；6号使用三群画像、试验设计及images/zh的PNG/SVG。所有角色可查看Role01时间审计引用。

文件逐项用途见FILE-LIST.csv；包内文件SHA256见CHECKSUMS.sha256。ZIP整体SHA256位于ZIP旁同名.sha256文件；校验清单不自我包含。复跑需要外部私有输入，详见reproduce/RUN.md。未含逐客户文件，未执行外发。
''')
checks=[]
def ck(n,v):assert v,n;checks.append(dict(check=n,passed=True))
for p in files:
 if p.name!='HANDOFF.md':ck('unchanged '+str(p.relative_to(S)),sha(p.read_bytes())==sha((D/p.relative_to(S)).read_bytes()))
def rows(p):return list(csv.DictReader(p.open(encoding='utf-8-sig')))
pr=rows(D/'results/profile-summary.csv');ss=rows(D/'results/sample-size-scenarios.csv')
ck('population',sum(int(x['n']) for x in pr)==29368);ck('positives',sum(int(x['positives']) for x in pr)==230)
ck('legacy capacity',sum(int(x['legacy_selected']) for x in pr)==2937)
doc=(D/'docs/content-experiment.md').read_text(encoding='utf-8');cards=(D/'docs/profile-cards.md').read_text(encoding='utf-8')
for x in ss:ck('sample text '+x['total'],x['total'] in doc and x['n_per_arm'] in doc and int(x['total'])==2*int(x['n_per_arm']))
for x in pr:
 g=x['cluster_id'];tree=ET.parse(D/f'images/zh/profile-{g}.svg');text=' '.join(tree.getroot().itertext())
 ck('SVG population '+g,f"{int(x['n']):,}" in text);ck('card population '+g,x['n'] in cards)
ck('no private filenames',not any(any(w in str(p.relative_to(D)).lower() for w in ['local_data','snapshot-asof-features','snapshot_features','snapshot_labels','validation_clusters']) for p in D.rglob('*') if p.is_file()))
write('audit/package-checks.json',json.dumps({'scope':'packaging checks only; no model/time audit recomputation','checks':checks},ensure_ascii=False,indent=2))
listing=[]
for p in sorted(D.rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(D).as_posix();kind=rel.split('/')[0]
 purpose={'docs':'交接、画像与实验设计','results':'可复算汇总证据及样本量','images':'中文展示图；SVG文本可编辑','audit':'核验记录、参考版本及来源指纹','scripts':'本轮分析与打包源码','reproduce':'外部输入、依赖和复跑说明'}.get(kind,'交付入口')
 listing.append(dict(file=rel,purpose=purpose,roles={'results':'2/5/6','images':'6','audit':'1/3/5','scripts':'2/5','reproduce':'2/5'}.get(kind,'全组'),bytes=p.stat().st_size))
table(D/'FILE-LIST.csv',listing)
write('CHECKSUMS.sha256','\n'.join(sha(p.read_bytes())+'  '+p.relative_to(D).as_posix() for p in sorted(D.rglob('*')) if p.is_file())+'\n')
out=D.with_suffix('.zip')
with ZipFile(out,'w',ZIP_DEFLATED) as zz:
 for p in sorted(D.rglob('*')):
  if p.is_file():zz.write(p,name+'/'+p.relative_to(D).as_posix())
with ZipFile(out) as zz:
 assert zz.testzip() is None
 for p in D.rglob('*'):
  if p.is_file():assert zz.read(name+'/'+p.relative_to(D).as_posix())==p.read_bytes()
out.with_suffix('.zip.sha256').write_text(sha(out.read_bytes())+'  '+out.name+'\n',encoding='utf-8')
print(json.dumps(dict(zip=str(out),sha256=sha(out.read_bytes()),files=len(listing)+2,checks=len(checks),zip_crc='PASS',zip_bytes_match='PASS'),indent=2))
