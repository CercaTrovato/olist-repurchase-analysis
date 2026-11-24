from pathlib import Path
import json,re,hashlib,sys
sys.dont_write_bytecode=True
from PIL import Image
out=Path('E:/app-data/codex/outputs/is6400-classroom-ppt-20261125')
sys.path.insert(0,'D:/上课资料/CityU/_meta/tools');from safe_write import atomic_write
notes=json.loads((out/'speaker-notes.json').read_text(encoding='utf-8'))
owners={1:'6号',2:'6号',3:'1号',4:'2号',5:'3号',6:'3号',7:'5号',8:'4号',9:'6号'}
budgets={1:25,2:35,3:60,4:50,5:70,6:70,7:55,8:60,9:35}
guide=['# 11 月 25 日课堂新版：中英讲稿与转场','','15 页：前9页主讲、后6页备查。主讲分工保持原1–6号安排；本人6号仍负责1、2、9页。预算460秒正文加20秒换人，不代表真人计时。正式要求8分钟展示另2分钟Q&A。','',
'已提交的11/15原件仍为13页；本文件对应新课堂稿，不表示替换Canvas附件。所有15页PPT备注已写入同版英文与中文提示。','',
'本人阅读顺序：第1页先介绍Olist历史订单与复购主题；第2页讲预测/分群、训练/验证/冻结测试如何衔接；第9页用一月和四月结果收尾。测试数与参数追问分别开第14、15页。','']
for n in range(1,16):
 d=notes[str(n)];count=len(re.findall(r"\b[\w]+(?:['-][\w]+)*\b",d['en']))
 guide += [f'## 第 {n} 页 · '+(owners[n]+f' / 建议{budgets[n]}秒' if n<=9 else '备查，不计主讲预算'),'',d['en'],'','中文提示：'+d['zh'],'']
 if n==1:guide += ['转到第2页：Let me show how the analysis fits together.','']
 if n==2:guide += ['交给1号第3页：Next, my teammate will explain our customer snapshots and the training, validation and test periods.','']
 if n==9:guide += ['接回结论：To bring the findings together, we have three conclusions.','结束：We are happy to take your questions.','']
guide += ['## 本人练习记录','','实际日期____；第1页____秒；第2页____秒；第9页____秒；全组____秒；仍卡住的问题____。','',
'本次是材料更新，不代填本人已掌握、排练、展示或正式提交。参数、数据与测试细节见QA；15页PDF用于核对显示。','']
atomic_write(str(out/'Speaker-Guide-20261125.md'),'\n'.join(guide))

qa='''# 课堂新版 Q&A：数据、参数、选模与测试

与15页课堂稿配套。先用20–30秒直接回答，再按追问展开；不要求把全部备查内容塞进8分钟主讲。

## 先把模型和指标名翻成人话

逻辑回归（LR）从历史案例学习各条线索怎样合成客户评分。复购者大约只占1%，普通训练中多数案例是未复购者；加权LR让少数复购案例的拟合错误占更大分量，使模型更加重视它们。这不等于复制正例或减少负例，也不保证每项指标改善。

最近购买规则（recency rule）直接按R从小到大排：距上次购买越近，越优先。它是无需拟合的简单排序参照。

精确率（Precision）看选中的名单里多少人后来复购；召回率（Recall）看全体真实复购者中找到了多少。平均精确率（AP）进一步汇总不同分数阈值下的精确率/召回率表现，帮助判断少数复购者是否靠前；AP=0.02不能读成整体正确率2%。

ROC-AUC看整体成对排序：随机取一位真实复购者和一位未复购者，前者分数更高的概率，并列记半。约0.5表示随机排序水平；它不是只看前10%名单，也不是整体分类准确率。固定名额下最有用的方法不一定拥有最高ROC-AUC。

## 1. How did you split the data?（第3、14页）

We trained on October 2017 and used January 2018 for development and model selection. We then evaluated a saved frozen LR8 pipeline on April, without refitting or changing hyperparameters. May and June are additional temporal checks, reported separately because the ninety-day outcome windows overlap.

中文：按快照日期划分。十月21,160/211，一月29,368/230，四月37,813/299。输入过去6个自然月，结果未来90天。本人已核验四月表现未用于调参；程序本次只加载预测。历史已见记录不删除，也不把本次重跑叫首次打开四月。

## 2. What hyperparameters did you use?（第10、15页）

Logistic regression used C equal to one, balanced or unweighted class weights, a maximum of two thousand iterations and seed 2026. The forest used three hundred trees, depth eight and minimum leaf size twenty. CatBoost used three hundred iterations, depth six and learning rate zero point zero five.

中文：参数表来自实际H04脚本。LR固定C=1，冻结对象中L2/lbfgs/tol1e-4；CatBoost另有l2_leaf_reg=5、随机种子2026。运行线程不是模型质量参数。max_iter是上限，不能说一定训练了2,000轮。

## 3. How were those settings selected?（第15页）

These were fixed configurations for our candidate comparison. We compared model performance on January, rather than claiming that a systematic grid search proved the settings globally optimal.

中文：不能把未执行的GridSearch、随机搜索或自动调参写成已做。正则化帮助限制过大的系数；C越小约束越强，但C=1没有被证明唯一最佳。

## 4. Why select weighted LR?（第5、9页）

Our main objective fixes the list at 2,937 January customers. Weighted LR found fifty repeat buyers, the most among the seven screening methods, and had the highest AP. CatBoost had the highest ROC-AUC, so our choice was specific to the fixed-capacity objective.

中文：同客户池、标签和容量。LR46、CB45、RF44、加权RF36、加权CB35、recency30。不是所有指标最好，也没有用后来的测试成绩重选模型。

## 5. What did the April test show?（第14页）

Among 37,813 customers with 299 repeat buyers, the frozen weighted model selected 3,782 customers and found sixty-five buyers. Precision was 1.72 percent, recall 21.74 percent, AP 0.020365 and ROC-AUC 0.606916. Ordinary LR found sixty-four and the recency rule forty-five.

中文：Precision=65/3782，Recall=65/299。它与一月50/230恰好同为21.74%，不是把一月召回率复制过来。一月Precision约1.70%，四月约1.72%。

## 6. Why not switch to ordinary LR after May?（第14页）

The selected model stays fixed during testing. May found sixty-five buyers with weighted LR and sixty-seven with ordinary LR. We report the unfavorable result, rather than use the test data to reselect a winner. June found fifty-nine and fifty-three respectively.

中文：五月不是加权获胜，三期全部保留。三期客户和90天标签有重叠，不能把样本数相加冒称独立人数，也不当三个独立盲测。

## 7. Does cross-validation favor weighting?（第6、12页）

Not on mean hits. October five-fold stratified cross-validation averaged 7.0 unweighted and 6.8 weighted hits per fold. Each validation fold had 4,232 customers and selected 424. It is an internal diagnostic, not a direct comparison with fifty January hits.

中文：5折shuffle=True、seed2026。每次16,928拟合、4,232核对，预处理折内学习；不是另留20%作概率校准。±是样本标准差，不是置信区间。群模型CV以全十月H05无监督映射为条件，不能称整个聚类流程折内隔离。

## 8. Why three clusters?（第4、15页）

We used a fixed three-cluster solution on historical RFM and checked stability across different initializations. It produced interpretable customer profiles. We do not claim that an undocumented elbow or silhouette search established three as universally optimal.

中文：R保留天数、F/M先log1p，再按十月标准化；k=3、k-means++、n_init20、max_iter300、tol1e-4、seed42，另用7/91检查稳定性。群名是画像而非人工阈值；“一次购买”看历史窗口，不是一辈子只买一次。

## 9. What is the difference between 73 and 79?（第7、11页）

Seventy-three is the number of long-inactive customers inside the later R3 global list. We retained seventy-nine from the existing within-group diagnostic protocol so every method selects the same number. It matches the older H04 global allocation for that group, but is not a claimed optimal operating quota.

中文：当前全局73席/2命中；另固定79，普通1、加权2。79沿用已有群内协议，数值与旧H04该群全局席位一致；R3名单变为73后，群内对照仍保持各方法同样79。本次没有按命中数重新搜索79，也没有证据证明它是最优业务配额或最初选值的唯一理由。群模型全局518席/4命中，但固定79只有1，不直接将4大于2解释成群内算法更好。

## 10. Are the screening and R3 results one fitted model?（第2、5、14页）

They are separate saved stages. Both weighted January lists find fifty buyers, but their scores and selected customers differ. The temporal tests use the actual saved H04-specification LR8 pipeline; the group and extension diagnostics use the later R3 results.

中文：两份2,937人名单共同2,920、各替换17。旧H04全局久单79、R3为73；不能把AP/AUC、群席位、测试权重跨版本拼接。

## 11. How did you prevent leakage?（第3、10页）

Predictors use historical events before the snapshot, while future labels are used to evaluate the predictions. Preprocessing is learned from training data. Later delivery events and review responses are excluded from earlier predictors, and final exported order status is not used to reconstruct past eligibility.

中文：按批准时间和正商品金额定义事件。迟到比例对预计送达日期的历史可知性仍有假设；原数据缺修改日志，不声称源系统绝无漏采或回写。测试时X需要进predict，不能把“输入模型”与“参与fit”混为一谈。

## 12. Did added fields or the content trial establish business improvement?（第6、8页）

The tested January delivery, review and group variants did not exceed fifty Top 10% hits. Newer proposed feature combinations are different and remain untested. The content trial has not run, so marketing uplift and profit have not been established.

中文：试验1:1主题指南vs通用指南，两组都联系，同渠道/版式/时间。分母为全部随机分配客户。+50%是相对提高，既有规划需两组合计21,308，高于12,330历史池；可触达资格未核。

## 13. Is the gain statistically significant?（第9、14页）

We describe the observed counts without claiming stable superiority. In April, the two LR lists share fifty-six observed buyers; weighted LR adds nine and ordinary LR eight, a net difference of one. This does not establish a significant advantage or causal marketing uplift.

中文：四月配对次要检验p=1.0，不证明等效，也不是100%没有差异。测试数据不是实际营销干预；命中更多不等于营销新增更多订单。

本文件为参考回答；本人实际熟练度和真人计时另行记录。新课堂稿可用于投影和问答，不自动替换已提交Canvas附件。
'''
atomic_write(str(out/'QA-20261125.md'),qa)
readme='''# Six Sigma · 11 月 25 日课堂更新版

- [可编辑PPTX](IS6400_SixSigma_Classroom_20261125.pptx)
- [PowerPoint原生PDF预览](IS6400_SixSigma_Classroom_20261125.pdf)
- [中英讲稿与转场](Speaker-Guide-20261125.md)
- [参数、数据划分与测试Q&A](QA-20261125.md)

本版15页：原1–9主讲分工保持，后6页备查；本人仍讲1、2、9页。第1页补Olist研究对象；第2、3页补训练/验证/冻结测试链条；第9页更新一月和四月结论。第14页新增三期测试，第15页新增实际参数。第5、6页同时修复原稿文字溢出，原两张原生图表及嵌入数据保留原字节。

冻结加权LR四月/五月/六月Top10%命中65/65/59，普通64/67/53、recency45/57/48。保留五月反例，不按测试换模型。测试权重为保存的H04规格LR8，后续R3群/扩展诊断分开标注。三期标签窗口重叠，分别报告。

这是课堂新版本，不是重新提交记录。11/15已提交13页原件保持原文件名和字节；没有上传或替换Canvas附件。讲稿时间是预算，不代填已排练或本人已掌握。

15页均已写讲者备注；PDF由原生PowerPoint导出。native-previews目录为PowerPoint直接按9600×5400像素导出的图像，在13.333×7.5英寸的实际使用尺寸下有效分辨率为720 DPI，不以修改DPI元数据或放大旧位图增加细节。审查与三端同步状态以本批回执为准。
'''
atomic_write(str(out/'README.md'),readme)
resolution=[]
for p in sorted((out/'native-previews').glob('slide-*.png')):
 with Image.open(p) as im:
  width,height=im.size
  assert width>=9600 and height>=5400
  resolution.append({'file':p.name,'pixels':[width,height],'dpi_at_13_333x7_5_in':[width/(40/3),height/7.5],'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
assert len(resolution)==15
atomic_write(str(out/'preview-resolution.json'),json.dumps({'renderer':'PowerPoint native PNG','pages':resolution},indent=2)+'\n')
total=sum(len(re.findall(r"\b[\w]+(?:['-][\w]+)*\b",notes[str(n)]['en'])) for n in range(1,10))
mine=sum(len(re.findall(r"\b[\w]+(?:['-][\w]+)*\b",notes[str(n)]['en'])) for n in [1,2,9])
print(json.dumps({'main_words':total,'role06_words':mine,'budget_seconds':460,'role06_budget_seconds':95,'preview_pages':len(resolution)},ensure_ascii=False))
