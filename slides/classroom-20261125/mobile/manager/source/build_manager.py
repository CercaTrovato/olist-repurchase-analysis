from pathlib import Path
from html import escape
import json,sys,hashlib,re,subprocess,xml.etree.ElementTree as E
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
from pypdf import PdfReader
S=Path(__file__).parent;C=S/'candidate-v2';C.mkdir(exist_ok=True)
V=Path('D:/上课资料/CityU');sys.path.insert(0,str(V/'_meta/tools'));from safe_write import atomic_write
scripts=[
 {'slide':1,'title':'Who should we contact first?','paragraphs':[
 "Hello everyone. We are Team Six Sigma. We studied Olist's past online orders to answer a practical question: with a limited marketing budget, which customers should we contact first?",
 "We want to find people likely to buy again and understand who our list is missing."],
 'transition':'Let me explain how we do that.',
 'zh':'先说经理要作的决定：预算有限，先联系谁？用历史购买行为排优先名单，并检查遗漏。不要先报算法、快照或模型文件。'},
 {'slide':2,'title':'Our approach','paragraphs':[
 "We use past purchases to make a priority list, then check who actually buys again later.",
 "We also check which types of customers the list covers or misses. This helps a manager decide whom to contact first and which group may need a different message."],
 'transition':'Next, my teammate will explain the data behind our analysis.',
 'zh':'先排名单，再看后来谁真的买了；再检查名单偏向哪些客户、漏了哪些客户。分群与预测的用途都保留，改成经理能理解的动作。技术划分和参数留备查及同伴展开。'},
 {'slide':9,'title':'What the results mean','paragraphs':[
 "Both January lists contained about three thousand customers. Our chosen method found fifty people who later bought again, compared with forty-six for the original method. In April, the figures were sixty-five and sixty-four. The gain was small.",
 "Adding delivery records, reviews or customer groups did not improve the January list. But the groups did show who was being missed.",
 "For customers who have not bought recently, we propose testing a home-goods shopping guide against a general guide. Thank you."],
 'transition':'We are happy to take your questions.',
 'zh':'先讲观察到的差别：一月50对46、四月65对64，提升有限；已测额外特征未提高主命中。分群用于看遗漏。最后明确下一步比较家居用品主题指南与通用指南，这是提议，不是已产生的营销效果。'}
]
pdfmetrics.registerFont(TTFont('Phone','C:/Windows/Fonts/arial.ttf'));pdfmetrics.registerFont(TTFont('PhoneBold','C:/Windows/Fonts/arialbd.ttf'))
W,H=390,1000;M=25;CW=W-2*M;BURG=HexColor('#541B35');INK=HexColor('#142132');MUTED=HexColor('#5A6470');BG=HexColor('#FBF9F5')
layout=[]
def para(c,txt,y,size=24,leading=33,font='Phone',color=INK,gap=14):
 p=Paragraph(escape(txt),ParagraphStyle('phone',fontName=font,fontSize=size,leading=leading,textColor=color,splitLongWords=False));_,h=p.wrap(CW,H);bottom=y-h
 if bottom<48:raise ValueError(('overflow',txt,bottom))
 p.drawOn(c,M,bottom);layout.append({'page':c.getPageNumber(),'size':size,'bottom':bottom,'text':txt});return bottom-gap
pdf=C/'IS6400_Slides_1-2-9_Manager_Mobile.pdf';assert not pdf.exists()
c=canvas.Canvas(str(pdf),pagesize=(W,H),pageCompression=1,invariant=1);c.setTitle('IS6400: manager-focused speaking script — Slides 1, 2, 9');c.setAuthor('LI Binxiong')
for i,item in enumerate(scripts,1):
 c.setFillColor(BG);c.rect(0,0,W,H,fill=1,stroke=0);c.setFillColor(BURG);c.rect(0,H-9,W,9,fill=1,stroke=0);c.setFont('PhoneBold',13);c.drawString(M,H-35,f'SLIDE {item["slide"]:02d} / MANAGER VERSION')
 y=para(c,item['title'],H-60,28,34,'PhoneBold',BURG,18)
 for p in item['paragraphs']:y=para(c,p,y)
 y-=5;c.setStrokeColor(HexColor('#D8C9CF'));c.line(M,y,W-M,y);y-=22;y=para(c,'NEXT' if i<3 else 'Q&A',y,12,16,'PhoneBold',BURG,7);para(c,item['transition'],y)
 c.setFillColor(MUTED);c.setFont('Phone',11);c.drawString(M,23,'SIX SIGMA | 25 NOV 2026');c.drawRightString(W-M,23,f'{i} / 3');c.bookmarkPage('slide'+str(item['slide']));c.addOutlineEntry('Slide '+str(item['slide']),'slide'+str(item['slide']),0,False);c.showPage()
c.save()
def save(name,text):atomic_write(str(C/name),text)
md='# 第1、2、9页：给非技术经理的讲稿\n\n本版按本人反馈重写，作为本人三页的当前主讲版本。先讲业务决定和结果，再在Q&A按需展开参数；与当前15页课堂稿的数字和已测/未测边界一致。旧技术讲稿保留历史，原PPT和已交附件不改。\n\n'
for x in scripts:md+='## 第'+str(x['slide'])+'页\n\n'+'\n\n'.join(x['paragraphs'])+'\n\n'+x['transition']+'\n\n中文理解：'+x['zh']+'\n\n'
save('Manager-Script.md',md.rstrip()+'\n')
word_count=sum(len(re.findall(r"\b[\w]+(?:['’-][\w]+)*\b",' '.join(x['paragraphs'])+' '+x['transition'])) for x in scripts)
save('content.json',json.dumps({'scripts':scripts,'word_count_including_transitions':word_count,'format':{'pages':3,'page_pt':[W,H],'body_pt':24,'leading_pt':33},'timing':'未真人计时，不由词数推定完成排练。','layout':layout},ensure_ascii=False,indent=2)+'\n')
save('README.md','# 最新手机主讲稿：经理版\n\n- [下载第1/2/9页英文讲稿PDF：24pt、3页](IS6400_Slides_1-2-9_Manager_Mobile.pdf)\n- [中英文字版](Manager-Script.md)\n\n按本人要求改为面向不懂技术的经理：有限预算联系谁、名单覆盖和遗漏、观察结果、下一步购物指南试验。原15页PPT、已交13页和旧技术讲稿保留；技术参数和10题QA继续作备查。PDF宽390pt，可按宽度查看并纵向滚动。未进行真人计时或手机实机测试。\n')
reader=PdfReader(pdf);assert len(reader.pages)==3
full=' '.join(' '.join(p.extract_text().split()) for p in reader.pages)
for x in scripts:
 for p in x['paragraphs']+[x['transition']]:assert ' '.join(p.split()) in full
xml=subprocess.check_output(['D:/poppler/Library/bin/pdftotext.exe','-bbox',str(pdf),'-']);root=E.fromstring(xml);flags=[]
for i,p in enumerate(root.findall('.//{http://www.w3.org/1999/xhtml}page'),1):
 for w in p.findall('.//{http://www.w3.org/1999/xhtml}word'):
  if float(w.get('xMin'))<20 or float(w.get('xMax'))>370 or float(w.get('yMin'))<10 or float(w.get('yMax'))>988:flags.append({'page':i,'word':w.text,**w.attrib})
assert not flags,flags
verification={'pages':3,'body_pt':24,'word_count_including_transitions':word_count,'word_edge_flags':flags,'minimum_text_bottom_pt':min(x['bottom'] for x in layout),'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in C.iterdir() if p.is_file()}}
save('build-verification.json',json.dumps(verification,ensure_ascii=False,indent=2)+'\n');print(json.dumps(verification,ensure_ascii=False,indent=2))
