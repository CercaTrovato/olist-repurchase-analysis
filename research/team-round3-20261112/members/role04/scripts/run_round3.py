"""Aggregate-only round 3; reuse frozen clusters; never fit a model."""
from pathlib import Path
from zipfile import ZipFile
import io,json,hashlib,math,platform
import pandas as pd
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
ROOT=Path(__file__).resolve().parents[1]; O=ROOT/'outputs/round3_role04'
for d in ['docs','results','audit','images/zh','reproduce']: (O/d).mkdir(parents=True,exist_ok=True)
K=['customer_unique_id','snapshot_date']; U=K[0]; hashes=[]; checks=[]
def digest(name,b): hashes.append(dict(source=name,sha256=hashlib.sha256(b).hexdigest()))
def read(p):
 b=(ROOT/p).read_bytes();digest(p,b);return pd.read_csv(io.BytesIO(b))
def check(name,actual,expected):
 checks.append(dict(check=name,actual=actual,expected=expected,passed=bool(actual==expected)));assert actual==expected,(name,actual,expected)
def align(a,b,name):
 for x,n in [(a,'left'),(b,'right')]:
  check(name+n+' duplicates',int(x.duplicated(K).sum()),0);check(name+n+' null keys',int(x[K].isna().any(axis=1).sum()),0)
 m=a[K].merge(b[K],on=K,how='outer',indicator=True,validate='1:1');check(name+' unmatched',int(m._merge.ne('both').sum()),0)
z=ZipFile(ROOT/'data/H02_candidate_v2.zip');digest('H02_candidate_v2.zip',(ROOT/'data/H02_candidate_v2.zip').read_bytes())
def member(name):
 b=z.read('H02_candidate_v2/'+name);digest(name,b);return pd.read_csv(io.BytesIO(b))
s=member('snapshot_features.csv');l=member('snapshot_labels.csv')
cl=read('outputs/H05-km3-v1/local_data/validation_clusters.csv')
t=read('outputs/feedback_round1/local_data/train_audit.local.csv')
v=s[s.snapshot_date.eq('2018-01-01')].copy();align(v,cl,'H05');v=v.merge(cl,on=K,validate='1:1')
for d in [t,v]:
 lab=l[l.snapshot_date.eq(d.snapshot_date.iloc[0])];align(d,lab,'labels '+d.snapshot_date.iloc[0])
 if 'y' in d: check('cached train labels',int(d.merge(lab[K+['y']],on=K,suffixes=('','_source')).eval('y != y_source').sum()),0)
 else: d['y']=d[K].merge(lab[K+['y']],on=K).y.to_numpy()
 check('version '+d.snapshot_date.iloc[0],','.join(d.data_version.unique()),'H02-v2-candidate-reviewed')
train_source=s[s.snapshot_date.eq('2017-10-01')];align(t,train_source,'cached train')
for f in ['R','F','M']: check('cached train '+f,float(np.round(np.max(np.abs(t.merge(train_source,on=K,suffixes=('','_source'))[f]-t.merge(train_source,on=K,suffixes=('','_source'))[f+'_source'])),10)),0.)
check('January N',len(v),29368);check('January positives',int(v.y.sum()),230)
check('group1 N',len(v[v.cluster_id.eq(1)]),12330);check('group1 positives',int(v[v.cluster_id.eq(1)].y.sum()),90)
expected=['3b58f4e493e825a76ccc569f205cfa0db5d27e22b13389c3c00ff958a316419a','ce62dedacb5af0e08c419586ff55e45043de56771553620ef3f08100e12712b9','5e75eae468449bb9810e8ac0b796bea588762dd6c3335f2923da91a46220888f','509e6df79c758be73c693ea63a5e1ff9a33db97bcbc168d218b47dfe02d55f85']
for h,e in zip(hashes[:4],expected):check(h['source']+' fingerprint',h['sha256'],e)
old=read('outputs/feedback_round1/results/segment-errors-recomputed.csv')
check('legacy selected sum',int(old.selected.sum()),2937)
rows=[]
for d,part in [(t,'train'),(v,'validation')]:
 pairs=read('outputs/feedback_round1/local_data/historical_pairs_'+part+'.local.csv');check(part+' pair duplicates',int(pairs.duplicated([U,'category']).sum()),0)
 check(part+' history pool',len(set(d[U])^set(pairs[U])),0)
 for cat in sorted(pairs.category.unique()):
  ids=set(pairs.loc[pairs.category.eq(cat),U]);alln=len(d);allk=int(d[U].isin(ids).sum())
  for g,a in d.groupby('cluster_id'):
   k=int(a[U].isin(ids).sum());n=len(a);otherk=allk-k;othern=alln-n
   se=(1-n/alln)*np.sqrt((k/n)*(1-k/n)/n+(otherk/othern)*(1-otherk/othern)/othern)
   rows.append(dict(snapshot_date=d.snapshot_date.iloc[0],cluster_id=g,category=cat,buyers=k,denominator=n,share=k/n,all_buyers=allk,all_denominator=alln,all_share=allk/alln,gap_pp=100*(k/n-allk/alln),gap_low_pp=100*(k/n-allk/alln-1.96*se),gap_high_pp=100*(k/n-allk/alln+1.96*se),window_start='2017-04-01' if part=='train' else '2017-07-01',window_end=d.snapshot_date.iloc[0]))
c=pd.DataFrame(rows);c.to_csv(O/'results/category-support.csv',index=False)
# Freeze choice by training support, without labels or validation ranking.
candidates=c[(c.snapshot_date=='2017-10-01')&(c.cluster_id==1)&(c.category!='UNKNOWN')].sort_values(['buyers','category'],ascending=[False,True]);candidates.to_csv(O/'results/theme-candidates.csv',index=False)
theme=candidates.iloc[0].category
profiles=[];md=['# 三群画像｜H05-km3-v1','2018-01-01；历史 [2017-07-01,2018-01-01)，标签 [2018-01-01,2018-04-01)。全体基线 230/29368。','R=(快照−最近批准时间)/86400，单位天；F=历史不同合格订单数，单位笔；M=历史商品价合计，不含运费，单位BRL。合格订单批准时间非空且商品金额>0，不按最终状态过滤。','模型数字仅为首轮已核汇总复用，H04 v0.4逐人分数缺失，不能确认本轮版本或重新核名单。全局2937切片不是每群10%；久单79独立诊断未执行。']
names=['购买较近的单单群','购买较久的单单群','历史多单群']
font_manager.fontManager.addfont('C:/Windows/Fonts/msyh.ttc');plt.rcParams.update({'font.family':font_manager.FontProperties(fname='C:/Windows/Fonts/msyh.ttc').get_name(),'svg.fonttype':'none'})
for g,a in v.groupby('cluster_id'):
 r=dict(cluster_id=g,n=len(a),positives=int(a.y.sum()),share=len(a)/len(v),rate=a.y.mean());legacy=old[old.cluster_id.eq(g)].iloc[0]
 for f in ['R','F','M']:
  for q,label in [(.25,'p25'),(.5,'median'),(.75,'p75')]:r[f+'_'+label]=a[f].quantile(q)
  r[f+'_missing']=int(a[f].isna().sum())
 for f in ['selected','hits']:r['legacy_'+f]=int(legacy[f])
 cat=c[(c.snapshot_date=='2018-01-01')&(c.cluster_id==g)&(c.category==theme)].iloc[0];unknown=c[(c.snapshot_date=='2018-01-01')&(c.cluster_id==g)&(c.category=='UNKNOWN')].iloc[0]
 lines=[f'群{g}：{names[g]}',f'H05-km3-v1 | 2018-01-01 | {len(a):,}/{len(v):,} ({len(a)/len(v):.2%})',f'复购 {int(a.y.sum())}/{len(a)} = {a.y.mean():.2%}；全体 230/29368 = {230/29368:.2%}',*[f'{f} P25 / 中位 / P75：{r[f+"_p25"]:.2f} / {r[f+"_median"]:.2f} / {r[f+"_p75"]:.2f}；缺失 {r[f+"_missing"]}/{len(a)}' for f in ['R','F','M']],f'旧版全局2937切片：入选 {int(legacy.selected)}；命中 {int(legacy.hits)}',f'覆盖 {int(legacy.selected)}/{len(a)}={legacy.selected/len(a):.2%}；命中率 {int(legacy.hits)}/{int(legacy.selected)}={legacy.hits/legacy.selected:.2%}',f'复购者召回 {int(legacy.hits)}/{int(a.y.sum())}={legacy.hits/a.y.sum():.2%}',f'{theme}：{int(cat.buyers)}/{len(a)}={cat.share:.2%}',f'全体同品类 {int(cat.all_buyers)}/{len(v)}={cat.all_share:.2%}；差 {cat.gap_pp:+.2f}百分点',f'未知品类客户 {int(unknown.buyers)}/{len(a)}；保留在分母', '解释：记录描述购买节奏，不代表价值、意愿或营销敏感度。','假设：与历史购买相关的选购指南可能提高90天复购，须随机试验。','局限：既有验证已查看；H04 v0.4缺失；历史相关非因果。']
 md+=['\n## '+lines[0]]+lines[1:];profiles.append(r)
 fig=plt.figure(figsize=(13,9));fig.patch.set_facecolor('#f4f7fb')
 for i,line in enumerate(lines):fig.text(.05,.95-i*.061,line,fontsize=18 if i==0 else 12,va='top',color='#172b4d')
 fig.text(.05,.025,'R: 天 | F: 笔 | M: BRL | 历史 [2017-07-01,2018-01-01) | 标签 [2018-01-01,2018-04-01)',fontsize=10)
 fig.savefig(O/f'images/zh/profile-{g}.svg');fig.savefig(O/f'images/zh/profile-{g}.png',dpi=150);plt.close(fig)
p=pd.DataFrame(profiles);p.to_csv(O/'results/profile-summary.csv',index=False);check('profile sum',int(p.n.sum()),len(v));check('positive sum',int(p.positives.sum()),int(v.y.sum()))
(O/'docs/profile-cards.md').write_text('\n\n'.join(md),encoding='utf-8')
p0=float(v[v.cluster_id.eq(1)].y.mean());pool=int((v.cluster_id==1).sum())
def sample(delta):
 p1=p0+delta;bar=(p0+p1)/2
 return (norm.ppf(.975)*np.sqrt(2*bar*(1-bar))+norm.ppf(.8)*np.sqrt(p0*(1-p0)+p1*(1-p1)))**2/delta**2
sc=[]
for rel in [.25,.5,1.]:
 delta=p0*rel;n=math.ceil(sample(delta));sc.append(dict(baseline=p0,relative_lift=rel,absolute_pp=100*delta,n_per_arm=n,total=2*n,available_upper_bound=pool,shortfall=max(0,2*n-pool)))
pd.DataFrame(sc).to_csv(O/'results/sample-size-scenarios.csv',index=False)
mde=[]
for reach in [1.,.75,.5]:
 n=int(pool*reach)//2;delta=brentq(lambda x:sample(x)-n,1e-6,.5);mde.append(dict(reachable_fraction_assumed=reach,n_per_arm=n,mde_pp=delta*100,mde_relative=delta/p0))
pd.DataFrame(mde).to_csv(O/'results/available-pool-mde.csv',index=False)
train=candidates.iloc[0];val=c[(c.snapshot_date=='2018-01-01')&(c.cluster_id==1)&(c.category==theme)].iloc[0]
doc=f'''# 内容试验设计（未开展）
目标：H05群1全群；主题：{theme} 实用选购指南。训练侧按已知品类购买人数降序、同数按品类名升序选择，候选全表见theme-candidates.csv；不按复购率筛主题。选择覆盖面而非声称偏好显著高于全体。
训练购买 {int(train.buyers)}/{int(train.denominator)}，全体 {int(train.all_buyers)}/{int(train.all_denominator)}，差{train.gap_pp:.3f}百分点；验证 {int(val.buyers)}/{int(val.denominator)}，全体{int(val.all_buyers)}/{int(val.all_denominator)}，差{val.gap_pp:.3f}百分点。运动休闲、香水及其他候选均保留比较，不因验证反复换题。一月和首轮筛查已看过，此规则属于透明的开发期选择，不能恢复独立验证。四月不参与选择，也不是新盲测。
品类字段products.product_category_name；按订单商品price总和>0、批准时间落在六自然月历史窗筛选，经customer_id映射customer_unique_id，再去重客户/品类。客户可跨品类，比例之和可超过100%。UNKNOWN保留；缺失客户数见UNKNOWN行，全部客户都有历史匹配。比例差区间采用群与其余客户独立二项近似，再乘其余客户占比，避免把群与全体误作独立；仅描述性未校正筛选，多重比较及小计数使证据有限。源静态品类缺少修订日志，假设历史可得。
## 入组与随机化
正式启动日按冻结H05映射确认群1，有同意接收邮件且地址有效；排除退订、测试账户、员工、已参加冲突活动者。客户键去重，同人多地址只留预先指定主地址。资格名单在随机化前冻结，触达资格目前未知，12330仅历史上限，不能直接发送。随机单位客户，1:1，种子20261112；不分层，按匿名键排序后用numpy.default_rng(seed).permutation分配，奇数额外一人给对照。冻结分配后送达失败仍留ITT分母；不按打开或点击筛选。
处理组：收到{theme}主题指南。示例：“挑选家居用品前，先测量使用空间，再核对尺寸、材质和清洁要求。比较同预算的选项时，可把耐用性和维护成本列成清单。点击查看完整选购指南。”（正式上线将葡语文案和该原始品类逐项校对。）
对照组：同版式通用购物指南。示例：“购物前先列出所需物品和预算，核对商品说明、配送范围及退换货条件。比较选项后再做决定。点击查看完整购物指南。”
两组同邮件渠道、同一当地时区周二10:00、仅一封、相同字数范围及CTA位置；同一落地页模板。无优惠券、无差别折扣；每人发送成本上限相同，设计预算各占50%，随机化前由运营冻结金额和素材。停止其他差异化促销。仅改变主题内容，记录实际发送成本、失败及串组。
## 指标与预先判断
唯一主指标：随机化起90天内至少一笔批准时间非空、商品price合计>0订单的客户比例。时间区间[t,t+90天)，分子各组符合事件的人数，分母全部随机分配客户（ITT）。不以点击归因订单，沿用H02批准事件口径；不称净留存或净收入。观察成熟并等待预先确定的7天数据入库缓冲后锁库，仅分析一次，不因中途显著而提前停。
主报告处理减对照的绝对百分点、相对变化(pT/pC−1)，95% Newcombe-Wilson风险差区间及对数风险比区间；零事件时相对变化不定义，使用精确区间，不加伪事件。双侧0.05，风险差区间下界>0且护栏无恶化才支持继续推广，否则证据不足或负向，不将不显著等同无效。
次指标：点击人数/分配人数、每分配客户90天商品金额；探索性不改变主结论。护栏：退订、投诉、退款客户/分配人数以及送达失败/分配人数；投诉绝对增加0.2百分点或退订增加0.5百分点触发安全复核，不作为提前宣称有效依据。实际部署前运营确认这些阈值。
## 人数与可行性
基线90/12330={p0:.6%}，同群同90天事件；并非已确认可触达人群基线，存在年代、季节和渠道差异。训练同群基线仅作敏感性背景，不能换成更有利基线。
双侧α=.05、功效.80、1:1，独立两比例正态近似：每组n=[z.975√(2p̄(1−p̄))+z.8√(p0(1−p0)+p1(1−p1))]²/(p1−p0)²，向上取整。低事件率建议正式试验前再做精确/模拟功效核查。
'''
for r in sc:doc+=f"\n相对提升{r['relative_lift']:.0%}，绝对+{r['absolute_pp']:.3f}百分点：每组{r['n_per_arm']}，共{r['total']}，比历史上限缺{r['shortfall']}人。\n"
for r in mde:doc+=f"\n假定可触达{r['reachable_fraction_assumed']:.0%}：每组{r['n_per_arm']}，MDE +{r['mde_pp']:.3f}百分点（相对{r['mde_relative']:.1%}）。\n"
doc+='\n因此不能无条件认定可行；小提升所需人数不足。可延长招募并按客户只入组一次，或预先扩大人群后重新估计混合基线，不能试验中途改人群或为可行而调基线。不增加附加群：现有证据没有明确额外定位收益；72类未发现可靠单字段不等于全部特征工程无空间。历史相关、样本量和分组方案均不代表已验证营销提升。\n'
(O/'docs/content-experiment.md').write_text(doc,encoding='utf-8')
digest('scripts/run_round3.py',Path(__file__).read_bytes());pd.DataFrame(hashes).to_csv(O/'audit/source-hashes.csv',index=False);pd.DataFrame(checks).to_csv(O/'audit/checks.csv',index=False)
(O/'audit/environment.json').write_text(json.dumps(dict(python=platform.python_version(),pandas=pd.__version__,numpy=np.__version__,matplotlib=matplotlib.__version__),indent=2))
print('PASS',len(checks),'checks; theme',theme);print(pd.DataFrame(sc).to_string(index=False));print(pd.DataFrame(mde).to_string(index=False))
