"""Render aggregate acceptance evidence. No model fitting or private row reads."""
from pathlib import Path
import pandas as pd,numpy as np,hashlib,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
O=Path(__file__).resolve().parent;A=O/'audit';F=O/'figures';F.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
def save(fig,name):
 for ext in ['png','svg']:fig.savefig(F/(name+'.'+ext),dpi=170,bbox_inches='tight')
 plt.close(fig)
r=pd.read_csv(A/'january-recomputed.csv');r=r[r.top_fraction.eq(.1)]
choices=[('basic','F0_base_unweighted','Base\nunweighted'),('basic','F0_base_weighted','Base\nweighted'),('basic','F1_delivery_unweighted','Delivery\nunweighted'),('basic','F1_delivery_weighted','Delivery\nweighted'),('basic','F2_review_unweighted','Review\nunweighted'),('basic','F2_review_weighted','Review\nweighted'),('group','B_global_with_cluster','B: add\ncluster'),('group','C_segmented_group2_global_fallback','C: group\nmodels')]
fig,axes=plt.subplots(2,1,figsize=(12.8,7.4),layout='constrained');x=np.arange(len(choices));colors=['#677d91','#147c88','#677d91','#147c88','#677d91','#147c88','#bd8130','#77559d']
for ax,metric,title,ylim in zip(axes,['hits','long79_hits'],['Global list: exactly 2,937 selected','Separate long-group list: exactly 79 selected'],[60,3]):
 values=[float(r[(r.table==t)&(r.method==m)].iloc[0][metric]) for t,m,_ in choices]
 bars=ax.bar(x,values,color=colors)
 for b,v in zip(bars,values):ax.text(b.get_x()+b.get_width()/2,v+.05 if metric=='long79_hits' else v+.7,str(int(v)),ha='center')
 ax.set_ylim(0,ylim);ax.set_xticks(x,[z for _,_,z in choices]);ax.set_ylabel('Actual repurchasers captured');ax.set_title(title);ax.grid(axis='y',alpha=.2)
fig.suptitle('Real team Round 3: saved predictions independently recounted\nJanuary is a seen development window; delivery/review sets differ from Role 02 proposal',fontsize=13)
save(fig,'01-team-models-and-long79')

e=pd.read_csv(A/'role02-evidence-recomputed-corrected.csv',dtype={'scope':str});labels={'C01':'Known delivery ratio','C02':'Pending delivery count','C03':'Log delivery duration','C04':'Missing delivery flag','C05':'Log known deliveries','C06':'Any known delivery','C07':'Late delivery share *','C08':'Mean review score','C09':'Missing review flag','C10':'Low review share','C11':'Known review ratio','C12':'Reviews / deliveries','C13':'Any known review','C14':'Log known reviews'}
fig,axes=plt.subplots(1,2,figsize=(13.8,7.2),layout='constrained')
for ax,scope,title in zip(axes,['ALL','1'],['All October training customers','October long-dormant group']):
 q=e[e.scope==scope].sort_values('candidate_id');yy=np.arange(len(q))
 for i,(_,v) in enumerate(q.iterrows()):
  color='#c6812c' if v.candidate_id in ['C02','C03','C04','C08','C09','C11'] else '#147c88'
  ax.errorbar(v.cohens_d,i,xerr=1.96*v.corrected_d_se,fmt='o',color=color,capsize=3)
 ax.axvline(0,color='#8292a2',ls='--',lw=1);ax.set_yticks(yy,[f'{v} {labels[v]}' for v in q.candidate_id]);ax.invert_yaxis();ax.set_xlabel("Cohen's d; approximate 95% interval");ax.set_title(title);ax.grid(axis='x',alpha=.2)
fig.suptitle('Role 02 point effects preserved; interval support corrected to observed nonmissing counts\nOrange: retained numeric fields or companion flags. * Conditional timestamp assumption; excluded.',fontsize=12)
save(fig,'02-role02-corrected-effect-intervals')

font=Path('C:/Windows/Fonts/msyh.ttc');assert font.exists();font_manager.fontManager.addfont(str(font));plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
p=pd.read_csv(A/'current-profile-summary.csv');cat=pd.read_csv(O/'private/extracted/role04/Role04_Round3_2026-11-12/results/category-support.csv');theme='cama_mesa_banho'
names=['购买较近的单单群','购买较久的单单群','历史多单群']
for _,v in p.iterrows():
 g=int(v.cluster_id);c=cat[(cat.snapshot_date=='2018-01-01')&(cat.cluster_id==g)&(cat.category==theme)].iloc[0]
 texts=[('一月已见开发验证｜H05-km3-v1',13),('当前名单依据：Round3 role03 F0 加权逻辑回归',13),(f'群规模：{int(v.n):,} / 29,368 人（{v.share:.2%}）',16),(f'实际复购：{int(v.positives)} / {int(v.n):,} 人（{v.rate:.2%}）',16),('',8),(f'距最近购买 R：中位数 {v.R_median:.2f} 天',14),(f'历史订单 F：中位数 {v.F_median:.0f} 笔',14),(f'历史商品额 M：中位数 {v.M_median:.2f}（源数据单位）',14),('',8),(f'全局 2,937 人名单中，本群入选 {int(v.r3_F0_selected)} 人',17),(f'这些入选客户中，实际复购 {int(v.r3_F0_hits)} 人',17),(f'本群复购者覆盖：{int(v.r3_F0_hits)} / {int(v.positives)}（{v.r3_F0_hits/v.positives:.2%}）',14),('',8),(f'床品／餐桌／卫浴相关品类历史覆盖：{int(c.buyers)} / {int(c.denominator):,}',13),('历史相关不能证明内容触达有效；随机内容试验尚未开展。',12)]
 fig=plt.figure(figsize=(12.6,8.8));fig.patch.set_facecolor('#f3f7fa');fig.text(.055,.945,f'群 {g}｜{names[g]}',fontsize=24,color='#145668',weight='bold',va='top')
 yy=.875
 for text,size in texts:fig.text(.06,yy,text,fontsize=size,color='#183342',va='top');yy-=.047
 fig.text(.06,.048,'历史：[2017-07-01,2018-01-01)；目标：[2018-01-01,2018-04-01)',fontsize=10,color='#52677b')
 fig.text(.06,.022,'来源：4 号群画像＋3 号本轮逐人分数；课程核验衍生图，原交付保留。',fontsize=10,color='#52677b')
 save(fig,f'03-current-group-{g}')
files=sorted(F.glob('*'));rec={'new_png_svg_pairs':5,'new_fits':0,'actual_view_status':'PENDING','files':{str(p.relative_to(O)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
(O/'plot-manifest.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'new_pairs':5,'files':len(files)}))
