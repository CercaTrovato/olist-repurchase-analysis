# P4B：不平衡处理与目标函数的受控验证

预定矩阵已完成：20 个实际模型运行、50 个分数版本。不是 50 次独立训练，也没有新增超参搜索。Oct 同一80/20划分：fit16,928人／169正例，cal4,232人／42正例；Jan29,368人／230正例全部评分，久单12,330人／90正例。April快照／标签读取0行。所有数据变换只fit于16,928人，所有Platt只fit于Octcal，Jan未用于拟合或选择。

结果没有支持“改成过采样／focal／排序损失就能普遍胜过原LR”。未加权LR原概率的Jan Logloss/Brier仍是本矩阵数值最佳；focal+Platt的AP稍高，但Top10%命中反而略少，不能据单个指标自动更换模型。负结果、原始失校准输出和全部seed均保留。

## 共同对照结果

下表随机方法为seed2026/2027/2028均值；确定性LR各只运行一次，SD为空，不伪造seed波动。完整SD、范围与三个群域在 `seed-summary-metrics.csv`，全部原始值在 `metrics-all-scopes.csv`。

| 家族／概率输出 | Jan Logloss ↓ | Brier ↓ | AP ↑ | AUC ↑ | Top10%命中均值／范围 |
|---|---:|---:|---:|---:|---|
| 未加权LR raw | 0.045268 | 0.007722 | 0.029553 | 0.57045 | 47／单次 |
| 未加权LR + Platt | 0.045455 | 0.007758 | 0.029553 | 0.57045 | 47／单次 |
| balanced LR raw | 0.652310 | 0.230842 | 0.026074 | 0.56630 | 42／单次 |
| balanced LR + prior | 0.045933 | 0.007734 | 0.026074 | 0.56630 | 42／单次 |
| balanced LR + Platt | 0.045815 | 0.007770 | 0.026074 | 0.56630 | 42／单次 |
| ROS-LR + prior | 0.046102 | 0.007736 | 0.026117 | 0.56756 | 43.67／43–44 |
| ROS-LR + Platt | 0.045859 | 0.007771 | 0.026117 | 0.56756 | 43.67／43–44 |
| SMOTENC-LR + prior | 0.048080 | 0.007741 | 0.028111 | 0.56122 | 46／45–47 |
| SMOTENC-LR + Platt | 0.045916 | 0.007769 | 0.028111 | 0.56122 | 46／45–47 |
| torch BCE raw | 0.045982 | 0.007747 | 0.027914 | 0.55100 | 40.33／40–41 |
| torch BCE + Platt | 0.045762 | 0.007768 | 0.027914 | 0.55100 | 40.33／40–41 |
| torch weighted-BCE + prior | 0.045500 | 0.007734 | 0.026574 | 0.56946 | 42／41–44 |
| torch weighted-BCE + Platt | 0.045690 | 0.007766 | 0.026574 | 0.56946 | 42／41–44 |
| torch focal raw | 0.175907 | 0.028122 | 0.031636 | 0.56680 | 45／43–46 |
| torch focal + Platt | 0.045315 | 0.007747 | 0.031636 | 0.56680 | 45／43–46 |
| torch pairwise + Platt | 0.045658 | 0.007765 | 0.026456 | 0.56921 | 42.33／41–44 |

自然fit常数基率169/16928=0.99835%，Jan Logloss/Brier=0.046034/0.00777495。多数合理概率版本优于这个全局常数，但这不等于彼此显著优胜，更不等于在单单／久单里可靠识别个人。此次未新增候选之间的统计检验，seed SD只反映初始化／采样波动，不涵盖时间漂移或数据抽样不确定性。

久单 Platt后AUC：未加权LR0.5093、balanced0.4995、ROS0.5019、SMOTENC0.5175、BCE0.4892、weighted-BCE0.4972、focal0.5104、pairwise0.5000；固定79人命中依次2、1、1、1、0、1（0–2）、1、1.67（1–2）。本矩阵仍未给出久单显著改善的证据。long proper metrics及5/10/20%完整策略均单独保存，不只展示有利结果。

## 这些动作改变的是什么

balanced BCE／LR把正例错误赋更大训练代价；ROS复制正例至一比一，它与加权的目标方向相近，但有限复制、solver正则化的样本总权重口径和随机抽样会改变系数，不能要求逐人分数完全相同。它们改变训练数据／损失；prior修正和Platt则改变已经拟合分数的概率尺度，二者不是同一件事。

解析prior修正扣去log(16759/169)=4.59679左右的训练权重比，假设主要变化是类别先验。SMOTENC还改变正例特征的条件分布，单纯减一个先验offset无法逆转这种改变：本轮SMOTENC prior的LL反而0.04808，比全局常数差；Platt修复主要尺度错误，但仍没有超过未加权LR。它是实际特征空间合成对照，不是论文里的潜空间增强。

focal gamma2会压低容易样本的梯度。本轮raw sigmoid的LL约0.176，说明focal输出也不能未经校准直接当自然概率；Platt后LL约0.045315，主要恢复概率尺度。pairwise直接奖励正例分数高于负例，优化的是相对顺序；截距可任意平移，因此raw只报排序／策略，只有Octcal Platt后才评价LL/Brier。所有本轮Platt斜率均为正，校准／先验修正没有改变各自Top10%名单；改善概率损失不等于新增命中。

## 预算与合成边界

- 原8字段经fit-only log1p/StandardScaler + state OHE得到34列。所有torch均同一35参数线性head，无隐藏层；Xavier uniform、bias0，Adam lr.01，150epochs，L2=.001×sum(weight²)/2，bias不罚。LR是固定C=1的独立solver参照，不声称其正则化或优化轨迹与torch完全相同。
- BCE／weighted BCE／focal：每epoch16×1024 + 544条fit客户，共17updates。weighted pos_weight=16759/169；focal gamma2、alpha.5。
- pairwise：每epoch169个fit正例各配50个放回随机负例，8450pairs；分成1×498 + 16×497，共17updates。每epoch约16900客户端点曝光，和BCE16928接近，但pair与单客户不是相同训练单位，损失数值不能跨目标直接比较。无calpair。
- 四个torch目标各3seed，各2550updates；12个run共30600steps。各epoch实际loss、L2、units、steps均在 `training-history.csv`。单run训练约1.4–2.0秒，正式全矩阵实测约32.3秒。
- ROS与SMOTENC只在fit内把169正例扩至16759，与16759负例平衡；各训练33518行。ROS新增16590复制，SMOTENC新增16590合成。SMOTENC先数值fit-only处理+state分类Ordinal编码，再按categorical_features=[7]合成；所有合成state都属于原fit合法类别，最后使用仅原fit类别拟合的OHE。cal与Jan从不参与合成。训练索引／完整合成矩阵留在private。

## 数值tie与历史名单

同一fit-only balanced LR分别用BLAS1／2线程重跑，逐人分数最大差0，Top10%名单变化0，命中均42，边界分差7.85e-6。本轮没有观察到近数值tie导致的名单变化，不把历史问题扩写成本轮问题。

历史full-Oct模型用21160人拟合，本轮为预留校准只用16928；Top10%名单共988个键发生选择状态变化，旧命中50、本轮42。这是训练样本范围不同的比较，不能归因纯数值噪音或拿旧50冒充本轮balanced结果。逐键变更证据保存在private，汇总见 `balanced-LR-list-sensitivity.json`。

## 文件与验证

- `private/october-fit-cal-manifest.csv` 精确保留每个训练键和fit/cal归属；同一个客户键不跨fit/cal。`private/fit-only-preprocessor.joblib` 与变换矩阵证明仅fit拟合。
- `private/jan-scores.csv`、`private/oct_cal-scores.csv`：键customer_unique_id/snapshot_date、cluster_id/y，50个 `score_<base>__<variant>`。raw-ranking的列是排序分数，不是概率。对应logits文件保留20模型原始线性分数。
- 每个 `private/<base>.joblib` 存变换、模型、Platt、参数、采样manifest、prior offset；torch同时存权重／bias／state_dict。可用 `run_objectives.py` 的 `predict_logit` 复用原始评分，或用独立核验脚本的 `infer` 重放全部版本；不调用fit。
- `metrics-all-scopes.csv` 400行：50版本×2时段×4域。Octcal raw是独立于模型fit的诊断，Platt读数在同一cal标签上拟合，明确是拟合内校准读数，不能声称无偏验证。
- `strategy-capacities.csv` 200行，`classification-0.5.csv` 保存概率版本分类补充。`seed-summary-metrics.csv`／`seed-summary-strategy.csv` 只汇总真实seed，`calibration-list-changes.csv`保留校准前后名单变化。
- `figures/`含所有目标的proper/ranking总图、Platt细节及TopK图，PNG/SVG同源生成，误差线为3seed样本SD，不是置信区间。
- `run-metadata.json`有各run实际耗时、全部参数、Platt系数与样本量，`failures.json=[]`，`verification.json`为运行回执。`independent-verification.json`为另一个脚本从落盘材料读回的工程核验，不冒称另一位代理的科学独审。

独立读回重算400项指标／200项策略，重放20模型×cal/Jan共40次；最大分数误差2.22e-16。核验fit-only scaler均值、fit/cal键不交叉、ROS全部原始索引在fit内、SMOTENC类别合法／合成仅正例、12个torch更新预算一致和全部来源哈希不变。源脚本默认不执行main，`-B`全程关闭pycache。

首轮BCE均分batch而非精确1024的实现偏差与核验脚本一次列名冲突均保留在 `execution-notes.md`；首轮完整48文件归档 `private/initial-equal-batches-run.zip`，不混入正式结果，也未删除以隐藏失败。正式结果未扩大搜索、未使用Jan调参。没有Git／看板／外部写入，未安装或修改原件；最终采用仍待主任务结合其余P4/P5证据决定。
