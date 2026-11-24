from pathlib import Path
import json,hashlib,sys,os
sys.dont_write_bytecode=True
import win32com.client
out=Path('E:/app-data/codex/outputs/is6400-classroom-ppt-20261125')
src=out/'IS6400_SixSigma_Classroom_20261125.pptx';pdf=src.with_suffix('.pdf')
temporary=out/'classroom-rendering.pdf'
assert not temporary.exists()
if pdf.exists():
 prior=json.loads((out/'native-export.json').read_text(encoding='utf-8'))
 assert hashlib.sha256(pdf.read_bytes()).hexdigest()==prior['pdf_sha256'],'Concurrent PDF edit'
before=hashlib.sha256(src.read_bytes()).hexdigest()
app=None;doc=None;rows=[];hidden=[];edges=[]
try:
 app=win32com.client.DispatchEx('PowerPoint.Application');app.AutomationSecurity=3
 doc=app.Presentations.Open(str(src),True,False,False)
 assert doc.Slides.Count==15
 doc.SaveAs(str(temporary),32)
 for slide in doc.Slides:
  hidden.append({'slide':slide.SlideIndex,'hidden':bool(slide.SlideShowTransition.Hidden)})
  for sp in slide.Shapes:
   if sp.Left < -.5 or sp.Top < -.5 or sp.Left+sp.Width > doc.PageSetup.SlideWidth+.5 or sp.Top+sp.Height > doc.PageSetup.SlideHeight+.5:
    edges.append({'slide':slide.SlideIndex,'id':int(sp.Id),'name':sp.Name,'left':float(sp.Left),'top':float(sp.Top),'width':float(sp.Width),'height':float(sp.Height)})
   if not sp.HasTextFrame or not sp.TextFrame.HasText:continue
   tf=sp.TextFrame2;tr=tf.TextRange
   allowed_h=sp.Height-tf.MarginTop-tf.MarginBottom;allowed_w=sp.Width-tf.MarginLeft-tf.MarginRight
   if tr.BoundHeight>allowed_h+1.5 or tr.BoundWidth>allowed_w+1.5:
    rows.append({'slide':slide.SlideIndex,'id':int(sp.Id),'text':tr.Text[:110],
      'bound_h':float(tr.BoundHeight),'available_h':float(allowed_h),'bound_w':float(tr.BoundWidth),'available_w':float(allowed_w)})
finally:
 if doc is not None:doc.Close()
 if app is not None:app.Quit()
assert before==hashlib.sha256(src.read_bytes()).hexdigest()
assert temporary.read_bytes().startswith(b'%PDF-')
os.replace(temporary,pdf)
report={'slides':15,'pptx_unchanged_by_export':True,'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'native_text_bounds_flags':rows,'shape_edges_flags':edges,'hidden':hidden}
(out/'native-export.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
