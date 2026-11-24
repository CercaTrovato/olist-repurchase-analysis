"""Preserve the submitted package; edit a separate classroom revision in OOXML."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from copy import deepcopy
from lxml import etree as E
import hashlib,json,re,os

SRC=Path('E:/app-data/codex/outputs/is6400-submitted-board-shared-20261115/original/IS6400_Final_PPT_Team Six Sigma_20261115.pptx')
OUT=Path('E:/app-data/codex/outputs/is6400-classroom-ppt-20261125')
OUT.mkdir(parents=True,exist_ok=True)
DEST=OUT/'IS6400_SixSigma_Classroom_20261125.pptx'
if DEST.exists():
 prior=json.loads((OUT/'build-verification.json').read_text(encoding='utf-8'))
 assert hashlib.sha256(DEST.read_bytes()).hexdigest()==prior['candidate_sha256'],'Concurrent candidate edit'
 version=1
 while (Path(__file__).parent/f'candidate-v{version}.pptx').exists():version+=1
 archive=Path(__file__).parent/f'candidate-v{version}.pptx';archive.write_bytes(DEST.read_bytes())
 if DEST.with_suffix('.pdf').exists():(Path(__file__).parent/f'candidate-v{version}.pdf').write_bytes(DEST.with_suffix('.pdf').read_bytes())
P='http://schemas.openxmlformats.org/presentationml/2006/main';A='http://schemas.openxmlformats.org/drawingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships';PKG='http://schemas.openxmlformats.org/package/2006/relationships'
CT='http://schemas.openxmlformats.org/package/2006/content-types';NS={'p':P,'a':A,'r':R}
q=lambda n,t:'{'+n+'}'+t
def xml(root):return E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
def sha(b):return hashlib.sha256(b).hexdigest()
with ZipFile(SRC) as z:parts={n:z.read(n) for n in z.namelist()}
assert sha(SRC.read_bytes())=='9452af19a145bc491532fb414c2d1704eecb9362998ca14eed59814486cbd8b2'
roots={n:E.fromstring(parts[f'ppt/slides/slide{n}.xml']) for n in range(1,14)}
def shape(root,id):
 return next(x for x in root.findall('./p:cSld/p:spTree/p:sp',NS) if x.find('./p:nvSpPr/p:cNvPr',NS).get('id')==str(id))
def replace(root,id,text,size=None):
 sp=shape(root,id);body=sp.find('p:txBody',NS)
 sample=deepcopy(sp.find('.//a:rPr',NS))
 if sample is None:sample=E.Element(q(A,'rPr'),lang='en-US',sz='1800')
 if size is not None:sample.set('sz',str(round(size*100)))
 for p in list(body.findall('a:p',NS)):body.remove(p)
 for line in text.split('\n'):
  p=E.SubElement(body,q(A,'p'));r=E.SubElement(p,q(A,'r'));r.append(deepcopy(sample));E.SubElement(r,q(A,'t')).text=line
 return sp

# Match the actual submitted palette and two-font typography.
BURG=shape(roots[1],300001).find('./p:spPr/a:solidFill/a:srgbClr',NS).get('val')
INK='2D2B2D';ACCENT='AD1852';MUTED='6F6268';TINT='EEE5E8';WHITE='FFFFFF'
uid=max(int(c.get('id')) for root in roots.values() for c in root.findall('.//p:cNvPr',NS))+1000
def add_text(root,text,x,y,w,h,size=18,color=INK,bold=False,font='Calibri',fill=None,align='l'):
 global uid;uid+=1
 if text:h=max(h,size*1.2*len(text.split('\n'))/28.3464567+.015)
 tree=root.find('./p:cSld/p:spTree',NS)
 sp=E.SubElement(tree,q(P,'sp'))
 nv=E.SubElement(sp,q(P,'nvSpPr'));E.SubElement(nv,q(P,'cNvPr'),id=str(uid),name='Classroom '+str(uid))
 E.SubElement(nv,q(P,'cNvSpPr'),txBox='1');E.SubElement(nv,q(P,'nvPr'))
 pr=E.SubElement(sp,q(P,'spPr'));xf=E.SubElement(pr,q(A,'xfrm'))
 E.SubElement(xf,q(A,'off'),x=str(round(x*360000)),y=str(round(y*360000)))
 E.SubElement(xf,q(A,'ext'),cx=str(round(w*360000)),cy=str(round(h*360000)))
 geo=E.SubElement(pr,q(A,'prstGeom'),prst='rect');E.SubElement(geo,q(A,'avLst'))
 if fill:E.SubElement(E.SubElement(pr,q(A,'solidFill')),q(A,'srgbClr'),val=fill)
 else:E.SubElement(pr,q(A,'noFill'))
 E.SubElement(E.SubElement(pr,q(A,'ln')),q(A,'noFill'))
 tx=E.SubElement(sp,q(P,'txBody'));E.SubElement(tx,q(A,'bodyPr'),wrap='square',lIns='70000',rIns='70000',tIns='0',bIns='0',anchor='ctr' if fill else 't')
 E.SubElement(tx,q(A,'lstStyle'))
 for line in text.split('\n'):
  p=E.SubElement(tx,q(A,'p'));pp=E.SubElement(p,q(A,'pPr'),algn=align)
  run=E.SubElement(p,q(A,'r'));rp=E.SubElement(run,q(A,'rPr'),lang='en-US',sz=str(round(size*100)),b='1' if bold else '0')
  E.SubElement(E.SubElement(rp,q(A,'solidFill')),q(A,'srgbClr'),val=color)
  E.SubElement(rp,q(A,'latin'),typeface=font);E.SubElement(rp,q(A,'ea'),typeface='Microsoft YaHei')
  E.SubElement(run,q(A,'t')).text=line
 return sp

# Cover introduces the research object before the business question.
replace(roots[1],300005,'Olist e-commerce: customer repurchase.\nCompare equal-sized lists. Understand missed buyers.')

replace(roots[2],900022,'Development + frozen test')
replace(roots[2],900023,'Jan screen; Apr test; May/Jun checks',size=14)
add_text(roots[2],'Temporal test: saved eight-input screening model. January group checks: later R3 run.',1.6,17.75,30.6,.55,10.5,MUTED)

# Keep the January process example; make all three dataset roles explicit below it.
for sp in list(roots[3].findall('./p:cSld/p:spTree/p:sp',NS)):
 id=int(sp.find('./p:nvSpPr/p:cNvPr',NS).get('id'))
 if id>=300026:sp.getparent().remove(sp)
for sp in roots[3].findall('./p:cSld/p:spTree/p:sp',NS):
 text=''.join(sp.itertext())
 if 'AT THE PREDICTION DATE' in text:
  replace(roots[3],sp.find('./p:nvSpPr/p:cNvPr',NS).get('id'),'JANUARY EXAMPLE / AT THE PREDICTION DATE',size=11)
phases=[('October 2017 / TRAIN','21,160 / 211','Fit model + preprocessing'),
        ('January 2018 / VALIDATE','29,368 / 230','Compare models and lists'),
        ('April 2018 / TEST','37,813 / 299','Load frozen model; no refit')]
for j,(title,count,purpose) in enumerate(phases):
 x=1.6+j*10.42
 add_text(roots[3],'',x,13.35,9.82,3.75,fill=TINT)
 add_text(roots[3],title,x+.12,13.48,9.56,.65,16.5,BURG,True)
 add_text(roots[3],count,x+.12,14.3,9.56,.95,27,BURG,font='Georgia')
 add_text(roots[3],'customers / 90-day repeat buyers',x+.12,15.55,9.56,.58,13.5,MUTED)
 add_text(roots[3],purpose,x+.12,16.2,9.56,.8,18,INK)
add_text(roots[3],'History: six calendar months. Outcome: next 90 days. May/June stability checks: backup 5.',1.6,17.65,30.6,.65,11,MUTED)

# Source-stage captions prevent the saved H04 test from being confused with R3.
replace(roots[5],300026,'Weighted LR leads January screening')
replace(roots[5],300027,'Standard and class-weighted versions use the same customer pool.')
replace(roots[5],300034,'Highest AP in this screening.\nCatBoost has the highest ROC-AUC.\nChoice follows the fixed-capacity goal.',size=18)
for page,id in [(5,300028),(6,300043)]:
 ext=shape(roots[page],id).find('./p:spPr/a:xfrm/a:ext',NS)
 ext.set('cx',str(int(ext.get('cx'))+108000))
replace(roots[6],300045,'October 5-fold CV: 7.0 unweighted vs 6.8 weighted hits per fold.\nTraining-period diagnostic; not a replacement for the January comparison.',size=17)
add_text(roots[5],'Saved screening-stage comparison; later January extension/group checks use a separate R3 run.',1.6,18.03,30.6,.5,10,MUTED)
add_text(roots[12],'January R3 capacity checks. Saved screening-stage model tested separately on backup 5.',1.6,18.03,30.6,.5,10,MUTED)
replace(roots[12],300117,'Capacity and validation trade-offs')

replace(roots[9],300069,'A simple reference\nchecked across time')
replace(roots[9],300071,'January: 50 vs 46. April: 65 vs 64.')
replace(roots[9],300072,'Equal-capacity comparisons; April uses the saved screening-stage LR8.')
replace(roots[9],300074,'Added complexity did not improve January hits')
replace(roots[9],300075,'The tested fields and group methods did not exceed 50 at 10%.')
replace(roots[9],300077,'Group diagnosis reveals missed buyers')
replace(roots[9],300078,'Use the profiles to design a feasible content trial.')
replace(roots[9],300079,'Next: confirm reachability and sample size, then run an approved content trial.',size=11)

def new_backup(n,label,title):
 root=deepcopy(roots[12]);tree=root.find('./p:cSld/p:spTree',NS)
 for child in list(tree):
  if child.tag==q(P,'sp'):
   id=child.find('./p:nvSpPr/p:cNvPr',NS).get('id')
   if id not in {'300116','300117'}:tree.remove(child)
 replace(root,300116,f'{n:02d}  /  BACKUP {label}')
 replace(root,300117,title,size=36)
 title_shape=shape(root,300117);xf=title_shape.find('./p:spPr/a:xfrm',NS)
 xf.find('a:off',NS).set('y',str(round(1.65*360000)));xf.find('a:ext',NS).set('cy',str(round(2*360000)))
 roots[n]=root;return root

r=new_backup(14,5,'Frozen LR8 models checked across time')
add_text(r,'Saved eight-input pipelines. Same Top 10% capacity within each month.',1.6,3.65,30.6,.8,18)
cols=[('Month',2.7),('Customers / buyers',7.0),('Places',4.2),('Recency',4.0),('LR',4.0),('Weighted LR',8.6)]
data=[['April','37,813 / 299','3,782','45','64','65'],['May','40,025 / 284','4,003','57','67','65'],['June','39,804 / 271','3,981','48','53','59']]
for i,row in enumerate([[c[0] for c in cols]]+data):
 x=1.6;y=5.15+i*1.5
 for j,(cell,(_,w)) in enumerate(zip(row,cols)):
  fill=BURG if i==0 else TINT if j==5 else ('F1ECEE' if i%2 else 'F8F5F2')
  add_text(r,cell,x,y,w,1.42,17 if i==0 else 22,WHITE if i==0 else BURG if j==5 else INK,i==0 or j==5,fill=fill,align='l' if j<2 else 'ctr')
  x+=w
for j,(label,value) in enumerate([('APRIL PRECISION','1.72%'),('APRIL RECALL','21.74%'),('APRIL AP','0.020365'),('APRIL ROC-AUC','0.606916')]):
 x=1.6+j*7.72
 add_text(r,label,x,11.65,7.35,.6,12,MUTED,True)
 add_text(r,value,x,12.35,7.35,1.2,28 if j<2 else 24,BURG,font='Georgia')
add_text(r,'May favors unweighted LR. Keep the selected model fixed during testing.',1.6,14.6,30.6,.85,19,INK)
add_text(r,'The 90-day outcome windows overlap; report months separately.',1.6,15.65,30.6,.8,17,MUTED)
add_text(r,'Source: frozen-model evaluation, 25 Nov 2026. Saved H04-spec LR8; not the later R3 fitted artifact.',1.6,17.65,30.6,.6,10.5,MUTED)

r=new_backup(15,6,'Model and clustering parameter settings')
add_text(r,'Fixed configurations used for the model and cluster comparisons.',1.6,3.65,30.6,.8,18)
settings=[('Logistic regression','C = 1; max_iter = 2,000; seed = 2026\nUnweighted or balanced class weights; L2 / lbfgs'),
 ('Random forest','300 trees; depth = 8; minimum leaf size = 20\nUnweighted or balanced class weights; seed = 2026'),
 ('CatBoost','300 iterations; depth = 6; learning rate = 0.05\nL2 leaf regularization = 5; seed = 2026; weighted variant tested'),
 ('K-means','k = 3; k-means++; 20 starts; max_iter = 300\ntol = 0.0001; seed = 42; fit October, apply January')]
for i,(model,setting) in enumerate(settings):
 y=5.15+i*2.55
 add_text(r,model,1.6,y,7.2,2.36,20,WHITE,True,fill=BURG)
 add_text(r,setting,8.95,y,23.25,2.36,18.5,INK,fill=TINT if i%2==0 else 'F1ECEE')
add_text(r,'Model choice: January Top 10% hits. October five-fold CV is a separate diagnostic.',1.6,15.85,30.6,.9,17,INK)
add_text(r,'AI assistance: Codex supported slide editing and evaluation scripting; results were checked against saved inputs.',1.6,17.65,30.6,.6,10.5,MUTED)

notes={
1:('Hello everyone. We are Team Six Sigma. We use Olist\'s historical e-commerce orders to study customer repurchase. Our business question is which existing customers should receive limited attention. We compare equal-sized prediction lists and use customer groups to understand who those lists miss.',
   '先介绍Olist历史订单和客户复购主题，再提出有限名额的问题。6号负责；目标约25秒，不等于真人计时。'),
2:('Our workflow connects prediction and customer segmentation. Customer histories use information available before each snapshot. October is for training and January for model development. We compare equal-sized lists, then join scores, groups and outcomes to diagnose coverage. We also load the saved screening-stage model for an April test, with May and June stability checks. The content trial remains a proposal.',
   '6号约35秒。先共同输入，再左预测右分群，再群内诊断。新增测试使用保存的H04规格模型；后续R3群检查仍是另一保存阶段。不要把两者说成同一个拟合文件。'),
3:('We create one row per customer at each prediction date. Inputs describe the previous six calendar months. The label records an eligible approved positive-value order in the next ninety days. October supplies 21,160 training customers and 211 repeat buyers. January supplies 29,368 customers and 230 buyers for development. April supplies 37,813 customers and 299 buyers for frozen-model testing. The January process example selects 2,937 people; April selects 3,782. Preprocessing is learned only from October. We do not refit on the test snapshots.',
   '1号约60秒。十月标签区间[2017-10-01,2017-12-30)，一月[2018-01-01,2018-04-01)，四月[2018-04-01,2018-06-30)。四月测试不调参由本人核验；不宣称首次看到四月。'),
4:('We describe three customer groups using historical recency, frequency and spending. The transformation and K-means centers are learned on October and applied to January. Group names summarize profiles rather than manual cutoffs. The long-inactive group contains ninety repeat buyers among 12,330 customers. These differences motivate delivery and review feature ideas. The newest proposed combinations differ from the fields already tested, so their predictive benefit remains untested.',
   '2号约50秒。37/135天是中位数，不是人工阈值。F/M先log1p，R保留天数，再按十月标准化。新G1/G2不等于实际F1/F2。'),
5:('The seven-method screening uses the same January customers and 2,937 places. Weighted logistic regression finds fifty buyers, ordinary logistic regression forty-six, CatBoost forty-five and random forest forty-four. Weighted forest and CatBoost find thirty-six and thirty-five; the recency rule finds thirty. We choose the weighted logistic reference for this capacity objective. It has the highest AP, but CatBoost has the highest ROC-AUC. The result is a development comparison, not proof of winning every metric. The next slide uses later R3 saved scores.',
   '3号第5/6页共140秒预算。LR根据历史线索学习评分；复购者少，加权让少数复购案例的训练错误占更大分量，不改变样本人数。recency按R从小到大选，即最近买过优先。AP概括不同阈值的精确率/召回率表现；ROC-AUC看真实复购者能否排在未复购者前面，两者都不是整体准确率。第5页H04 v0.2缓存；第6页后R3不同名单。无系统GridSearch最优证明。后备14测试的是实际保存H04规格模型。'),
6:('In the later R3 checks, all methods use the same January cohort and Top 10% capacity. The weighted baseline finds fifty buyers. Delivery fields find forty-eight, review fields forty-six, a group label fifty, and separate group models forty-nine. These are negative results for the tested variants only. October five-fold mean hits are seven unweighted and six point eight weighted, so weighting does not win every diagnostic. Each fold selects 424 customers, which is not directly comparable with the January count of fifty.',
   '3号续。F1已知送达数/平均配送时长/迟到比例；F2已知评分数/平均分/低分比例。CV仅十月分层五折shuffle、seed2026。群模型的H05表示先拟合全十月，不能称整个流程完全折内隔离。'),
7:('The later R3 global list finds fifty buyers, but only two of the ninety long-inactive repeat buyers. Only seventy-three of this group enter the global list. A separate group-only comparison fixes capacity at seventy-nine, finding one buyer unweighted and two weighted. These are different lists. More group places do not by themselves prove better within-group ranking. The group diagnostics identify a coverage gap rather than a proven causal explanation for every missed buyer.',
   '5号约55秒。2190+73+674=2937；21+2+27=50；漏88。79沿用既有群内诊断协议的固定规模，与旧H04全局该群79席一致；当前R3全局该群73席，但群内对照继续各取79以保持同容量。现有记录不证明79是业务最优配额，本次没有按命中数重选它。'),
8:('The proposal randomly assigns reachable, consenting long-inactive customers equally to a themed shopping guide or a generic guide. Both groups receive contact, with the same channel, format and timing. We compare ninety-day repurchase using all randomized customers in the denominator. This tests the content theme, not contact versus no contact. The trial has not run. Detecting a fifty-percent relative improvement requires 21,308 people in total under the planning assumptions, exceeding the historical pool of 12,330. Reachability and sample size must be checked first.',
   '4号约60秒。相对50%不是50个百分点；基线90/12330约0.730%，目标约1.095%。双侧alpha .05，power .80，1:1。历史池不是已同意可触达人数。'),
9:('Our simple weighted reference found fifty buyers versus forty-six in January. In the April frozen-model test, it found sixty-five versus sixty-four, ahead of the recency rule at forty-five. The advantage is modest and is not uniform across months. The tested extensions did not improve January Top 10% hits. Group diagnosis still reveals missed buyers and supports a content-test proposal. Next, we check reachability and sample size before an approved trial. Thank you.',
   '6号约35秒。四月测试属已保存H04规格模型；五月普通67高于加权65，保留不利结果。加权三期都高于recency，但不声称稳定显著胜普通。'),
10:('The baseline uses seven numerical fields and state. Numerical fields use log-one-plus and training-fitted standardization. State is one-hot encoded. The frozen pipeline expands the raw eight fields to thirty-four columns. Scores rank every eligible customer; there is no fixed zero-point-five selection threshold. Balanced class weights change fitting influence, not sample counts. The raw weighted output is used for ranking rather than assumed calibrated purchase probability.',
    '八字段不等于八个编码后系数。R/F/M、平均明细行数、运费占比、近30天订单/金额、州。无SMOTE/下采样。'),
11:('The group models change allocation of a fixed global capacity. The baseline gives long-inactive customers seventy-three places and finds two buyers. Adding group ID gives 181 places and finds two; separate models give 518 and find four. At the equal group-only capacity of seventy-nine, the counts are two, two and one. Better coverage and better within-group ranking therefore need separate evidence.',
    '此表为一月R3，不是四月测试。分群模型群0/1分别拟合、群2全局兜底。'),
12:('Capacity checks retain the later January R3 scores. At five percent both logistic models find thirty-one buyers; at ten percent the counts are forty-six and fifty; at twenty percent seventy-three and seventy-five. The October five-fold spread is sample standard deviation, not a confidence interval. These are internal diagnostics, not five independent future periods.',
    'R3一月20%加权75；旧H04规格缓存74，不混表。'),
13:('The left column contains fields already tested by the R3 models. The right column contains newer proposals with different definitions. The tested delivery and review results cannot establish that every proposed feature combination is ineffective. New proposals require matched validation before adoption.',
    '旧v3第14页现第13页。delivery_days_log不能在通用管道再次log1p。'),
14:('These are actual predictions from saved, already fitted pipelines. October trained the models; January supported development. The April test has 37,813 customers and 299 buyers. At the same 3,782 places, weighted LR finds sixty-five, ordinary LR sixty-four and recency forty-five. Precision is 1.72 percent and recall 21.74 percent. May finds sixty-five versus sixty-seven, and June fifty-nine versus fifty-three. We keep the selected model fixed. Outcome windows overlap, so the months are reported separately.',
    '完整来源为research/frozen-temporal-test-20261125。本人已核验四月表现未用于调参；程序仅load/predict，模型hash原件未变。四月共同56、独有9/8，p=1不是等效证明。Wilson参考区间不覆盖训练/时间漂移。'),
15:('These settings are recorded configurations rather than a claimed global optimum. Logistic regression uses C equal to one and up to two thousand iterations. Forest depth and minimum leaf size control complexity. CatBoost uses three hundred iterations and learning rate zero point zero five. K-means uses three groups and twenty starts. Three clusters were checked for initialization stability, not proven optimal by an undocumented elbow search. October cross-validation is separate from January model screening and April testing.',
    '参数语义与实际值分开。LR的C越小正则越强；max_iter是上限而非实际轮数；KMeans n_init20不是20群。AI assistance: Codex supported slide editing and evaluation scripting; numerical results were checked against saved models and input data.')}

changed=[1,2,3,5,6,9,12]
for n in changed:parts[f'ppt/slides/slide{n}.xml']=xml(roots[n])
for n in [14,15]:
 parts[f'ppt/slides/slide{n}.xml']=xml(roots[n])
 rel=E.fromstring(parts['ppt/slides/_rels/slide12.xml.rels'])
 for el in rel:
  if el.get('Type').endswith('/notesSlide'):el.set('Target',f'../notesSlides/notesSlide{n}.xml')
 parts[f'ppt/slides/_rels/slide{n}.xml.rels']=xml(rel)

base_note=E.fromstring(parts['ppt/notesSlides/notesSlide1.xml'])
for n,(en,zh) in notes.items():
 note=deepcopy(base_note)
 body=next(sp.find('p:txBody',NS) for sp in note.findall('./p:cSld/p:spTree/p:sp',NS) if sp.find('./p:nvSpPr/p:nvPr/p:ph',NS).get('type')=='body')
 for child in list(body.findall('a:p',NS)):body.remove(child)
 for line in ['ENGLISH',en,'中文提示',zh]:
  p=E.SubElement(body,q(A,'p'));r=E.SubElement(p,q(A,'r'));rp=E.SubElement(r,q(A,'rPr'),lang='en-US',sz='1200')
  E.SubElement(rp,q(A,'latin'),typeface='Calibri');E.SubElement(rp,q(A,'ea'),typeface='Microsoft YaHei');E.SubElement(r,q(A,'t')).text=line
 parts[f'ppt/notesSlides/notesSlide{n}.xml']=xml(note)
 if n>13:
  rel=E.fromstring(parts['ppt/notesSlides/_rels/notesSlide1.xml.rels'])
  for el in rel:
   if el.get('Type').endswith('/slide'):el.set('Target',f'../slides/slide{n}.xml')
  parts[f'ppt/notesSlides/_rels/notesSlide{n}.xml.rels']=xml(rel)

presentation=E.fromstring(parts['ppt/presentation.xml']);rels=E.fromstring(parts['ppt/_rels/presentation.xml.rels'])
ids=presentation.find('p:sldIdLst',NS);rid=max(int(x.get('Id')[3:]) for x in rels)+1;sid=max(int(x.get('id')) for x in ids)+1
content=E.fromstring(parts['[Content_Types].xml'])
for n in [14,15]:
 E.SubElement(ids,q(P,'sldId'),id=str(sid),attrib={q(R,'id'):'rId'+str(rid)})
 E.SubElement(rels,q(PKG,'Relationship'),Id='rId'+str(rid),Type=R+'/slide',Target=f'slides/slide{n}.xml');rid+=1;sid+=1
 for path,typ in [(f'/ppt/slides/slide{n}.xml','application/vnd.openxmlformats-officedocument.presentationml.slide+xml'),(f'/ppt/notesSlides/notesSlide{n}.xml','application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml')]:
  E.SubElement(content,q(CT,'Override'),PartName=path,ContentType=typ)
parts['ppt/presentation.xml']=xml(presentation);parts['ppt/_rels/presentation.xml.rels']=xml(rels);parts['[Content_Types].xml']=xml(content)
app=E.fromstring(parts['docProps/app.xml'])
for child in app:
 if E.QName(child).localname in {'Slides','Notes'}:child.text='15'
parts['docProps/app.xml']=xml(app)
for n,root in roots.items():
 ids_in_slide=[c.get('id') for c in root.findall('.//p:cNvPr',NS)]
 assert len(ids_in_slide)==len(set(ids_in_slide)),('duplicate drawing IDs',n)
for name,data in parts.items():
 if name.endswith(('.xml','.rels')):E.fromstring(data)
temporary=OUT/'classroom-writing.tmp'
assert not temporary.exists()
with ZipFile(temporary,'w',ZIP_DEFLATED) as z:
 for name,data in parts.items():z.writestr(name,data)
os.replace(temporary,DEST)
assert sha(SRC.read_bytes())=='9452af19a145bc491532fb414c2d1704eecb9362998ca14eed59814486cbd8b2'
with ZipFile(SRC) as z:
 unchanged=[n for n in range(1,14) if n not in changed]
 assert all(z.read(f'ppt/slides/slide{n}.xml')==parts[f'ppt/slides/slide{n}.xml'] for n in unchanged)
 charts=[n for n in z.namelist() if n.startswith(('ppt/charts/','ppt/embeddings/'))]
 assert all(z.read(n)==parts[n] for n in charts)

info={'source_sha256':sha(SRC.read_bytes()),'candidate_sha256':sha(DEST.read_bytes()),'slides':15,'main_slides':9,'backup_slides':6,
 'visible_changed_original_pages':changed,'appended_pages':[14,15],'unchanged_original_pages':unchanged,
 'original_chart_and_embedding_parts_preserved':len(charts),'notes_pages':15,'member_pages_unchanged':{'role01':[3],'role02':[4],'role03':[5,6],'role04':[8],'role05':[7],'role06':[1,2,9]},
 'model_test_source':'77d50b613961245fc67617df743068af557d7f8f / research/frozen-temporal-test-20261125',
 'style':{'burgundy':BURG,'heading':'Georgia','body':'Calibri'},'submitted_original_modified':False,'canvas_resubmission':False}
(OUT/'build-verification.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'speaker-notes.json').write_text(json.dumps({str(n):{'en':en,'zh':zh} for n,(en,zh) in notes.items()},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(info,ensure_ascii=False,indent=2))
