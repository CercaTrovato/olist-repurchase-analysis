from pathlib import Path
import json,hashlib,sys
sys.dont_write_bytecode=True
import win32com.client
from PIL import Image
out=Path('E:/app-data/codex/outputs/is6400-classroom-ppt-20261125')
source=out/'IS6400_SixSigma_Classroom_20261125.pptx';dest=out/'native-previews'
dest.mkdir(exist_ok=True)
before=hashlib.sha256(source.read_bytes()).hexdigest();app=None;doc=None;records=[]
try:
 app=win32com.client.DispatchEx('PowerPoint.Application');app.AutomationSecurity=3
 doc=app.Presentations.Open(str(source),True,False,False)
 for slide in doc.Slides:
  p=dest/f'slide-{slide.SlideIndex:02d}.png'
  slide.Export(str(p),'PNG',9600,5400)
  with Image.open(p) as im:
   assert im.size==(9600,5400),(p.name,im.size)
   records.append({'file':p.name,'pixels':list(im.size),'effective_dpi':720,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
finally:
 if doc is not None:doc.Close()
 if app is not None:app.Quit()
assert before==hashlib.sha256(source.read_bytes()).hexdigest()
(out/'native-preview-verification.json').write_text(json.dumps({'source_sha256':before,'renderer':'PowerPoint native slide.Export PNG','records':records},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'pages':len(records),'pixels':[9600,5400],'effective_dpi':720,'source_unchanged':True}))
