from pathlib import Path
import json,re,hashlib,os,sys
from html import escape
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
from pypdf import PdfReader

S=Path(__file__).resolve().parent
C=S/'candidate-v3';C.mkdir(exist_ok=True)
V=Path('D:/上课资料/CityU');A=V/'IS6400_Business_Data_Analytics/assignment/graded/A06-group-project'
sys.path.insert(0,str(V/'_meta/tools'));from safe_write import atomic_write
SOURCE=A/'notes/classroom-speaker-20261125.md';RAW=SOURCE.read_bytes();text=RAW.decode('utf-8')
def sha(b):return hashlib.sha256(b).hexdigest()
def save(name,value):atomic_write(str(C/name),value)
def section(n):
 m=re.search(r'## 第 '+str(n)+r' 页[^\n]*\n\n(.*?)(?=\n## |\Z)',text,re.S);assert m
 return m.group(1).split('\n\n中文提示：')[0].strip()
scripts=[{'slide':1,'title':'Opening','lead':'','paragraphs':[section(1)],'transition':'Let me show how the analysis fits together.'},
 {'slide':2,'title':'How the analysis fits together','lead':'','paragraphs':[section(2)],'transition':'Next, my teammate will explain our customer snapshots and the training, validation and test periods.'},
 {'slide':9,'title':'Conclusions','lead':'To bring the findings together, we have three conclusions.','paragraphs':[section(9)],'transition':'We are happy to take your questions.'}]
# Paragraph breaks are reading aids; the approved spoken sentences are preserved.
splits={1:['Our business question'],2:['October is for','We also load'],9:['In the April','The tested extensions','Next, we check']}
for item in scripts:
 body=item['paragraphs'][0]
 for marker in splits[item['slide']]:body=body.replace(' '+marker,'\n\n'+marker)
 item['paragraphs']=body.split('\n\n')
 assert ' '.join(item['paragraphs'])==section(item['slide'])

qa=[
 {'q':'What is your business question?', 'zh':'你们研究的业务问题是什么？','answer':'We study which existing Olist customers are more likely to purchase again within ninety days. Under a fixed contact capacity, prediction ranks customers, while segmentation describes the groups covered or missed by the list. The findings support targeting decisions and a proposed content experiment.','hint':'研究对象：Olist既有客户。预测用于排序，分群用于画像和名单诊断；不是已经证明营销提升。','backup':'Slides 1, 2 and 9'},
 {'q':'How did you split the data?', 'zh':'训练集、验证集和测试集怎样划分？','answer':'We trained on October 2017 and used January 2018 for development and model selection. We then loaded the saved frozen model for April testing, without refitting or changing hyperparameters. May and June are additional temporal checks. Their ninety-day outcome windows overlap, so we report them separately.','hint':'十月21,160人／211正例；一月29,368／230；四月37,813／299。不是随机60/20/20；十月五折是额外内部诊断。','backup':'Slides 3 and 14'},
 {'q':'Which inputs did you use, and how did you avoid leakage?', 'zh':'用了什么输入？怎样避免未来信息泄漏？','answer':'The eight inputs describe RFM, order structure, recent activity and state. They use history before each snapshot; the label records an eligible purchase in the next ninety days. Preprocessing is learned from training data. Later delivery events and review responses are excluded from earlier predictors.','hint':'八字段：R、F、M、平均明细行数、运费占比、近30天订单数／金额、州。测试X可以进入predict，但不能用于fit或调参。源数据历史回写仍有假设。','backup':'Slides 3 and 10'},
 {'q':'Why did you select weighted logistic regression?', 'zh':'怎样选最佳模型？为什么选加权逻辑回归？','answer':'Our main objective is to find repeat buyers within the same 2,937 January places. Weighted LR found fifty buyers versus forty-six for ordinary LR and had the highest AP among the screening candidates. CatBoost had the highest ROC-AUC. October cross-validation did not favor weighting on mean hits, so our choice is specific to the January capacity objective.','hint':'一月七候选同池同名额；不是所有指标都最佳。十月CV普通7.0、加权6.8；前10%是比较条件，不是已经证明的最佳运营容量。','backup':'Slides 5 and 12'},
 {'q':'How did you set the model and clustering parameters?', 'zh':'参数如何设置？是系统搜索出的最优参数吗？','answer':'LR used C=1, L2 and up to 2,000 iterations. Forest used 300 trees, depth 8 and leaf size 20. CatBoost used 300 rounds, depth 6, learning rate 0.05 and L2=5. K-means used three clusters and twenty starts. These were fixed configurations; we did not establish a global optimum through exhaustive search.','hint':'预测模型seed 2026；聚类seed 42。K-means++，最多300轮，tol=0.0001。20 starts不是20群；三群检查过初始化稳定性，不等于证明k=3最优。','backup':'Slide 15'},
 {'q':'If segmentation did not improve prediction, why use it?', 'zh':'分群没提高预测，为什么仍有价值？','answer':'Segmentation provides interpretable customer profiles and shows which groups the prediction list covers or misses. In the later January baseline, only two of ninety long-inactive repeat buyers were selected. That coverage gap motivates feature hypotheses and a content-test proposal, even though the tested variants did not improve overall Top 10% hits.','hint':'你的主线：预测找名单；分群做画像、查覆盖和遗漏、提出可检验想法。已测配送48、评价46、加群号50、群模型49，基线50；新组合仍未测。','backup':'Slides 6, 7, 9 and 13'},
 {'q':'What is the difference between 73 and 79?', 'zh':'73席和固定79席有什么区别？为什么518席命中4人不够证明更好？','answer':'Seventy-three is the number of long-inactive customers included in the global list of 2,937. Seventy-nine is a separate group-only comparison size. Separate group models include 518 long-inactive customers in the global list and find four buyers. When each method selects 79 from this group, they find one buyer versus two for the weighted baseline. More group places do not prove better ranking.','hint':'79沿用已有群内比较协议，与旧八字段筛选阶段该群的全局席位一致；不是业务最优配额，也不是在2,937席外追加79席。','backup':'Slides 7 and 11'},
 {'q':'What did the frozen-model tests show?', 'zh':'冻结测试结果怎样？为什么五月不换普通LR？','answer':'At April Top 10%, weighted LR found sixty-five buyers, ordinary LR sixty-four and recency forty-five. Precision was 1.72 percent and recall 21.74 percent. May favored ordinary LR, 67 versus 65; June favored weighted LR, 59 versus 53. We keep the selected model fixed during testing rather than reselecting it from those results.','hint':'测试加载保存的H04规格八字段管道，不是后续R3拟合文件。四月AP=0.020365，AUC=0.606916。四月表现未用于调参由本人核验。','backup':'Slide 14'},
 {'q':'Is the gain significant, and does it prove business value?', 'zh':'优势显著吗？1.72%的精确率是否有业务价值？','answer':'The observed gain is modest. In April, the LR lists share fifty-six buyers; weighted LR uniquely finds nine and ordinary LR eight. This does not establish significant superiority. Precision of 1.72 percent exceeds the population rate of about 0.79 percent, but ranking performance alone does not prove marketing uplift or profit.','hint':'65/3,782是Precision；65/299是Recall。四月配对次要检验p=1.0不证明等效。真实联系成本、增量响应和利润尚未验证。','backup':'Slides 9 and 14'},
 {'q':'How would you test the business proposal?', 'zh':'业务试验具体怎样做？样本够吗？','answer':'We propose randomly assigning reachable, consenting long-inactive customers equally to a themed shopping guide or a generic guide. Both groups receive contact under the same conditions. We compare ninety-day repurchase using all randomized customers. The trial has not run. Detecting a fifty-percent relative improvement requires 21,308 people under the planning assumptions, more than the historical pool of 12,330.','hint':'测试内容主题，不是联系vs不联系。历史基线90/12,330≈0.730%；相对+50%目标≈1.095%，不是加50个百分点。双侧5%、power80%；先核同意、触达和样本量。','backup':'Slide 8'}
]
pdfmetrics.registerFont(TTFont('Phone','C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFont(TTFont('PhoneBold','C:/Windows/Fonts/arialbd.ttf'))
pdfmetrics.registerFont(TTFont('PhoneZH','C:/Windows/Fonts/simhei.ttf'))
W,H=390,1000;M=25;CW=W-2*M;BURG=HexColor('#541B35');INK=HexColor('#142132');MUTED=HexColor('#5A6470');BG=HexColor('#FBF9F5')
layout=[]
def para(c,txt,y,size=24,leading=33,font='Phone',color=INK,gap=12):
 p=Paragraph(escape(txt),ParagraphStyle('phone',fontName=font,fontSize=size,leading=leading,textColor=color,splitLongWords=(font=='PhoneZH'),wordWrap='CJK' if font=='PhoneZH' else None))
 width,height=p.wrap(CW-20 if font=='PhoneZH' else CW,H);bottom=y-height
 if bottom<48:raise ValueError(f'Overflow: {txt[:60]} ends at {bottom}')
 p.drawOn(c,M,bottom);layout.append({'page':c.getPageNumber(),'font':font,'size':size,'top':y,'bottom':bottom,'text':txt});return bottom-gap
def base(c,label,page,total):
 c.setFillColor(BG);c.rect(0,0,W,H,fill=1,stroke=0)
 c.setFillColor(BURG);c.rect(0,H-9,W,9,fill=1,stroke=0)
 c.setFont('PhoneBold',13);c.drawString(M,H-35,label)
 c.setFillColor(MUTED);c.setFont('Phone',11);c.drawString(M,23,'SIX SIGMA  |  25 NOV 2026');c.drawRightString(W-M,23,f'{page} / {total}')
def begin(path,title):
 c=canvas.Canvas(str(path),pagesize=(W,H),pageCompression=1,invariant=1);c.setTitle(title);c.setAuthor('LI Binxiong');return c
main=C/'IS6400_Slides_1-2-9_Mobile.pdf';assert not main.exists();c=begin(main,'IS6400: Slides 1, 2 and 9 — mobile speaking script')
for i,item in enumerate(scripts,1):
 base(c,f'SLIDE {item["slide"]:02d}  /  SPEAKING SCRIPT',i,3)
 y=para(c,item['title'],H-60,28,34,'PhoneBold',BURG,18)
 if item['lead']:y=para(c,item['lead'],y,24,33,gap=14)
 for p in item['paragraphs']:y=para(c,p,y,24,33,gap=14)
 y-=5;c.setStrokeColor(HexColor('#D8C9CF'));c.line(M,y,W-M,y);y-=22
 y=para(c,'NEXT' if item['slide']!=9 else 'Q&A',y,12,16,'PhoneBold',BURG,7)
 y=para(c,item['transition'],y,24,33)
 c.bookmarkPage('slide-'+str(item['slide']));c.addOutlineEntry('Slide '+str(item['slide']), 'slide-'+str(item['slide']),0,False);c.showPage()
c.save()
H=844
questions=C/'IS6400_QA10_Mobile.pdf';assert not questions.exists();c=begin(questions,'IS6400: 10 likely questions — short English answers and Chinese cues')
for i,item in enumerate(qa,1):
 base(c,f'QUESTION {i:02d} / 10',i,10)
 y=para(c,item['q'],H-60,25,30,'PhoneBold',BURG,10)
 y=para(c,item['zh'],y,16,23,'PhoneZH',MUTED,16)
 y=para(c,item['answer'],y,22,30,gap=18)
 y=para(c,'中文提示',y,13,19,'PhoneZH',BURG,7)
 y=para(c,item['hint'],y,16,23,'PhoneZH',INK,12)
 y=para(c,item['backup'],y,12,17,'PhoneBold',MUTED,0)
 c.bookmarkPage('q-'+str(i));c.addOutlineEntry('Q'+str(i)+': '+item['q'],'q-'+str(i),0,False);c.showPage()
c.save()
payload={'source_guide_sha256':sha(RAW),'scripts':scripts,'qa10':qa,'format':{'script_page_points':[W,1000],'qa_page_points':[W,H],'script_body_pt':24,'script_leading_pt':33,'qa_body_pt':22,'qa_chinese_cue_pt':16},'layout':layout}
save('content.json',json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
save('Slides-1-2-9.md','# 第1、2、9页手机讲稿\n\n'+''.join('## Slide '+str(x['slide'])+'\n\n'+(x['lead']+'\n\n' if x['lead'] else '')+'\n\n'.join(x['paragraphs'])+'\n\n'+x['transition']+'\n\n' for x in scripts))
save('QA10.md','# 10道可能的课堂问答\n\n'+''.join('## '+str(i)+'. '+x['q']+'\n\n'+x['zh']+'\n\n'+x['answer']+'\n\n中文提示：'+x['hint']+'\n\n备查：'+x['backup']+'\n\n' for i,x in enumerate(qa,1)))
save('README.md','# 手机大字讲稿与10题Q&A\n\n- [第1、2、9页英文讲稿：3页，正文24pt](IS6400_Slides_1-2-9_Mobile.pdf)\n- [10题Q&A：一题一页，英文22pt和中文提示16pt](IS6400_QA10_Mobile.pdf)\n- [讲稿文字版](Slides-1-2-9.md) · [Q&A文字版](QA10.md)\n\n对应11月25日15页课堂稿；讲稿正文沿用已核英文并保留转场。PDF宽390pt，讲稿为1000pt长页、QA高844pt，可按宽度查看并纵向滚动，嵌入字体、可选择文字。题目是备考建议，不表示教师已确认题单。本人实际演练与掌握另行记录。\n')
for path,expected in [(main,3),(questions,10)]:
 reader=PdfReader(path);assert len(reader.pages)==expected
 assert all(tuple(float(v) for v in p.mediabox[2:])==(W,1000 if path==main else 844) for p in reader.pages)
 assert all(p.extract_text().strip() for p in reader.pages)
 if path==main:
  joined=' '.join(p.extract_text() for p in reader.pages)
  for item in scripts:assert ' '.join(section(item['slide']).split()) in ' '.join(joined.split())
assert SOURCE.read_bytes()==RAW
result={'files':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in C.iterdir() if p.is_file()},'pdf_pages':{'script':3,'qa':10},'text_boxes':len(layout),'minimum_bottom':min(x['bottom'] for x in layout),'source_guide_unchanged':True}
save('build-verification.json',json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
