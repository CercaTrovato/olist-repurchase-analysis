# P4B 不平衡处理／目标函数冻结矩阵

2026-11-11，按主任务授权开始。只写 objectives 目录。无 Git／看板／外部写入／安装；不解析或评分 April。Jan 已见，所有结果为开发比较，不能宣称新时间盲测或自动采用。

## 共同数据与评估

- bounded read_dev 前 50,528 行，Oct21160/211、Jan29368/230。Oct train_test_split(test_size=.2,stratify=y,random_state=20261111)，fit16928、cal4232，保留每个键、split、训练变换和模型。
- 原8：R,F,M,average_item_rows,freight_share,recent30_orders,recent30_spend,state。数值 log1p + StandardScaler、state OHE(handle_unknown=ignore)；所有变换只 fit 于 fit，Jan／cal只 transform。H05原群只诊断，long cluster1 Jan12330/90。
- Jan全量评分，科学LL/Brier/AP/AUC，全体及三个群；策略global5/10/20%（K=1469/2937/5874）与long79。固定0.5分类Accuracy/F1/MCC作为补充，不当唯一依据。
- 每个base模型都在自然类别比例 Octcal 4232人上拟合Platt：单变量 logit/decision score → LogisticRegression(C=1e6,class_weight=None,max_iter=2000)。不合并fit+cal重训，不看Jan调参；Octcal raw仅诊断，Platt使用同一cal标签后的读数为拟合内，不能称无偏。无新增OOF或超参搜索。
- 自然Oct-fit常数基率为最低无信息参照。所有候选及负结果完整保留，三个seed=2026,2027,2028；确定性LR仅一次，不伪造3seed波动。

## 固定候选

1. LR unweighted：原固定C=1、max_iter=2000、lbfgs。原输出+统一Platt。
2. LR balanced：class_weight=balanced。原输出+sigmoid(logit-log(nneg/npos))解析先验修正+统一Platt。
3. RandomOverSampler 仅fit内复制正例至1:1，3seed；同一LR。原输出+解析先验修正+统一Platt。prior correction扣除log((resampled_pos/resampled_neg)/(original_pos/original_neg))，原先验来自fit。
4. SMOTENC 仅fit内，3seed：fit-only log1p/scale数值与fit-only state OrdinalEncoder后采样，state为categorical_features，k_neighbors=5、sampling_strategy=auto；采样完仅在原fit的state类别fit OHE，再接LR。不对OHE浮点类别做普通SMOTE，不跨cal合成。可用安装依赖核验后严格运行；原输出+同一解析修正+统一Platt。明确这是实际特征空间合成，并非论文潜空间增强。
5. 四种同一线性torch head（无隐藏层，input→1），同一fit-only原8变换，3seed；linear.weight Xavier uniform，bias=0；Adam(lr=.01)、150epochs、显式L2=.001*||w||²/2，不罚bias。
   - BCEWithLogitsLoss；weighted BCE以fit nneg/npos作为pos_weight；focal gamma=2,alpha=.5，逐样本0.5*(1-pt)^2*BCE；pairwise logistic ranking用softplus(-(zpos-zneg))。
   - 每epoch BCE全fit随机序列以batch1024分成17updates；ranking每epoch169正例各配50个随机负例（放回，8450pairs），重新随机顺序后分17个不超过1024的batch。因此四种均150×17=2550优化steps。ranking实际每步pair数不同，样本／pair曝光量单列，不把其损失数值跨目标直接比较。
   - 每epoch ranking仅用fit正负键，无calpair；每epoch所有169正例都出现50次。raw ranking只报AP/AUC/策略，sigmoid(raw)也不当真实概率；必须仅Octcal Platt后才报概率LL/Brier。其余torch原sigmoid均报自然概率诊断及统一Platt，weighted额外解析修正。

## 结果保存与校验

保存Oct fit/cal manifest、原／重采样／合成数量、种子、耗时、参数、各模型和变换、cal/Jan全部分数、所有聚合结果与PNG/SVG。balanced LR使用同一fit的原保存full-Oct模型仅另作共同fit与历史的近数值tie检查；原矩阵不混用21160训练结果。实际新balanced全fit与本轮fit-only的名单变化单列，不能把训练范围变化归因数值噪音。近数值tie在本轮固定分数两个直接重复fit和两个线程设置中核名单、边界间隔与最大误差。

独立read-back验证检查分数键／人数／事件、策略K与命中、loss复算、模型重载预测误差和所有source哈希。所有失败保留准确错误，不以补跑更多参数找赢家。本任务训练上限为预定矩阵，未保证任何方法改善。
