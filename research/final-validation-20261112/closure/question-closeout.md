# 二十项质疑最终结案

原18项原文保留，新增Q19/Q20。冻结范围的计算已完成；有限证据、资料缺失和现实采用决定分别结案，不留“待用户开测”的实验欠账，也不以训练数量强行证明赢家。

全体概率→价值→经理名单已实际闭环：6个Gamma正支、18套全体经理私表、1,296容量行、36金额误差行及840条件区间已交付。独立回算覆盖6模型/18私表/144分数列/全部容量和金额误差；840区间仅独立核结构与数量，没有第二次重跑bootstrap。

固定10%下，原pFM与预计金额各15/18组合捕获商品额高于p，预计金额11/18高于pFM。组合来自3个重叠已见窗口，不能当18次独立验证；大多条件区间含0，没有统一赢家。

|编号|问题|结案分类|可支持结论|
|---|---|---|---|
|Q01|原八字段与原始数据|限定范围已验证|原八字段是模型选择的 7 数值+state 客户摘要，不是原始数据仅有八项。141 是逻辑摘要数，编码矩阵维度随 fit 词典变化；不能把原 P2 的 913 维当所有后续划分固定维数。|
|Q02|字段数量与效果|限定范围已验证|“字段越多效果越好”的单调说法不成立。同为 LR 增字段会下降；神经/树的取舍不同。AE 去行为块在 Jan 参考全局 51→58，但区间含 0，久单并未同步稳定提高。|
|Q03|全量输入与固定名单|限定范围已验证|固定 K 从来只截输出名单，不能限制输入人数；全量客户概率与经理选多少人是两个模块。|
|Q04|合规全字段与地理特征|限定范围已验证|卖家地区和买卖距离已经纳入；合适的“全字段”应是经时间与身份隔离后的可用输入对照，不是原表任意列全塞。|
|Q05|群内统计初始化可学习权重|现有数据证据不足|统计初始化已实际试过。零与相关初值收敛至近同凸解，同为 40 命中；没有可宣称的初始化收益。群偏移没有形成概率/名单同时稳健改善。|
|Q06|群独立分支与主网|现有数据证据不足|共享主网加群分支已经做有界比较。ReLU 没有概率/名单同时稳定优于同参数 identity；独立分支不是必然增益。|
|Q07|最终系统消融|限定范围已验证|用户要求的候选后系统消融已在冻结 AE 对象上执行，早期“后置/未开始”只属历史。额外监督预算未复现 AE 候选表现，但配对重建机制的收益仍无明确名单证据。|
|Q08|注意力机制|限定范围已验证|已验证若干明确 attention/门控定义，没有因名字复杂就获益。样本视图 attention 在原规格较差；列门相对等权参照没有一致全面优势。|
|Q09|异常检测与目标重合|限定范围已验证|原八字段 LOF/IF 全局命中30/26/35/32，低于既有 weightedLR50且AP较低；异常度不等于复购概率。按用户“低就算”要求结案。|
|Q10|一次购买预测是否成立|现有数据证据不足|从相似客户学习群体风险在统计上可以做，但多数单单/久单增量概率收益区间跨0；不能承诺识别每个久单个体。|
|Q11|最终验收和排序价值|限定范围已验证|概率误差验收覆盖全体客户，排序是下游策略。固定10%下 pFM 和预计金额各在15/18组合捕获商品额高于p，预计金额11/18高于pFM；概率、命中、商品额与金额误差存在取舍，没有统一赢家。|
|Q12|神经分类损失|限定范围已验证|普通二元神经分类主损失通常是 BCE，本项目须按实际版本说明：BCEWithLogitsLoss接logit，权重/对比辅助项另列；本批原生CB用Logloss。|
|Q13|纯预测与商业二阶段|限定范围已验证|“先纯预测，再商业选择”已经成为实际两阶段接口。改变名单K不需重新限制模型输入。|
|Q14|目标不平衡与潜空间伪样本|现有数据证据不足|不平衡并未忽略，但这些方法没有一致获胜。论文借鉴已落实为明确定义的MVSIB-inspired简化，不是完整MVSIB复现，也没有为复购正类生成真实带标签交易。|
|Q15|三群、深度/软聚类和未知簇数|限定范围已验证|三群不是已证明最优。有限训练几何偏好K2，GMM BIC偏好搜索上界K8；这些回答几何/密度，不能当复购最优K。|
|Q16|不同视图影响分群|限定范围已验证|不同视图确实改变表示空间和分区；不能用跨空间silhouette绝对值直接裁定哪个商业分群正确。|
|Q17|其他机器学习方向|明确不在当前必要范围且理由|生存分析、全部图注意力与所有排序目标不构成本次穷尽义务。当前固定任务是90天是否复购及商品额，已给对应合理模型与反例，继续加名字不自动增加可验证结论。|
|Q18|研究过程与执行门禁|限定范围已验证|旧设计阶段“等待/新增0”是历史，不是当前门禁。最后批是一次冻结收束，不能因理论不确定性无限追加搜索。|
|Q19|全体概率→原pFM/预计金额价值→经理名单|限定范围已验证|全体概率→价值分数→经理名单闭环已执行。主参考 p×F×M、字面敏感性 p×max(F−1,0)×M 与 p×发生购买条件下未来90天商品总额预测并列。固定10%时，pFM和预计金额各15/18组合捕获额高于p，预计金额11/18高于pFM；不能据此选唯一赢家。|
|Q20|全量输入、全量字段、100%名单与10%的区别|限定范围已验证|全量客户是行维度，全可用字段是列维度，名单百分比是输出容量。100%选择全部合格客户，覆盖全部已观察复购与商品额，precision等于群体复购率，排序不改变该端点。10%用于资源有限场景及旧项目可比，从未限制概率模型输入。|

## Q01 原八字段与原始数据

> 原八字段是什么意思？是原数据只有八个特征吗？

**实际完成：** 完成九表 52 字段位置处置目录、订单至客户快照血缘、141 历史结构字段及类别/编码口径。

**结论：** 原八字段是模型选择的 7 数值+state 客户摘要，不是原始数据仅有八项。141 是逻辑摘要数，编码矩阵维度随 fit 词典变化；不能把原 P2 的 913 维当所有后续划分固定维数。

**边界：** 键、事件时间、预测日未知结果及重复语义不能机械全部塞入 X。

**现实决策：** 小组选择展示多少字段解释即可；不需要补算法。

**缺外部资料：** 静态维表/录入回写日志不存在，不能从字段多推断历史全部已知。

**证据：**
- [field-catalog-52.csv](../../validation-20261111/features/field-catalog-52.csv)
- [feature-views.json](../../validation-20261111/features/feature-views.json)
- [data-manifest.json](../data/data-manifest.json)

## Q02 字段数量与效果

> 目前是不是发现字段越多效果越好？

**实际完成：** 原 P2 五候选、同口径 base8/full141 × 多模型/五重叠 split，以及 AE 六块逐块置零和预算控制均已完成。

**结论：** “字段越多效果越好”的单调说法不成立。同为 LR 增字段会下降；神经/树的取舍不同。AE 去行为块在 Jan 参考全局 51→58，但区间含 0，久单并未同步稳定提高。

**边界：** 信息块有语义代理、置零分支仍能学常量，块贡献不是因果作用且不能相加。

**现实决策：** 若正式展示采用某套输入，须按目标与整套策略证据选择；无需继续扫组合挑分。

**缺外部资料：** 没有新独立未来样本，无法证明某删块方案跨期稳定。

**证据：**
- [controlled-paired-differences-by-split.csv](../../common-comparison-20261112/statistics/controlled-paired-differences-by-split.csv)
- [README.md](../../ae-ablation-20261112/feature-groups/README.md)
- [canonical-paired-bootstrap-intervals.csv](../../ae-ablation-20261112/statistics/canonical-paired-bootstrap-intervals.csv)

## Q03 全量输入与固定名单

> 你确定固定长度名单对于最终目的是必须的吗？为什么不能固定时间段内的客户全量当输入？

**实际完成：** 全部合格客户训练/评分已落实；最后批 Nov/Dec/Jan 分别给 23,260/26,848/29,368 位客户输出全部三种主概率。

**结论：** 固定 K 从来只截输出名单，不能限制输入人数；全量客户概率与经理选多少人是两个模块。

**边界：** “全体”指固定 H02 六自然月有合格历史订单 cohort，不是数据库里所有人或半年无订单的另一目标总体。

**现实决策：** 经理依据精力/预算/目标设置容量，小组决定正式采用的模型；不是等待开测。

**缺外部资料：** 真实触达成本与人力约束未提供。

**证据：**
- [README.md](../probability/README.md)
- [window-summary.csv](../data/window-summary.csv)
- [manager-guide.md](../value/manager-guide.md)

## Q04 合规全字段与地理特征

> 如果原数据特征足够多，应尝试全输入对照。没有看见卖家地区。

**实际完成：** 52 原字段位置已逐项处置；141 可计算摘要包括买卖双方城市/州/邮编、近似经纬度与距离、商品/支付/已知服务等；历史文本也曾单独比较。7 日期重建并对旧 July/Oct/Jan逐键核验。

**结论：** 卖家地区和买卖距离已经纳入；合适的“全字段”应是经时间与身份隔离后的可用输入对照，不是原表任意列全塞。

**边界：** 141 字段包含派生和冗余，不等于 141 项独立信息；地理静态维表、付款等字段依赖既有历史已知/未回写假设。

**现实决策：** 正式材料须展示字段定义与假设，不宜宣称生产时点认证。

**缺外部资料：** 缺属性变更、真正入库与回写日志；无法认证全部源字段当时可恢复性。

**证据：**
- [README.md](../../validation-20261111/features/README.md)
- [historical-feature-reproduction.csv](../data/historical-feature-reproduction.csv)
- [date-construction-audit.json](../data/date-construction-audit.json)

## Q05 群内统计初始化可学习权重

> 无监督分群后分析群内特征与目标关系/协方差，给特征群分数，再把分数变成可学习参数加到统一权重。

**实际完成：** fit 内计算硬群/软群加权相关与收缩；比较固定相关偏移、零初值/相关初值可学习群斜率、共享权重加群偏移和仅群截距。

**结论：** 统计初始化已实际试过。零与相关初值收敛至近同凸解，同为 40 命中；没有可宣称的初始化收益。群偏移没有形成概率/名单同时稳健改善。

**边界：** 这是群内相关/协方差加收缩及监督群斜率，不是控制变量 ANCOVA，不是因果分析；固定正则 eta=.1 的负结果不排除所有群模型。

**现实决策：** 正式采用没有必须引入该模块的证据；权重/统计定义已给可解释实现。

**缺外部资料：** 不存在支持因果识别的干预/混杂设计；这一缺口不列为未完训练。

**证据：**
- [README.md](../../validation-20261111/group-learning/README.md)
- [correlation_initialization.csv](../../validation-20261111/group-learning/correlation_initialization.csv)
- [convex_initialization_comparison.json](../../validation-20261111/group-learning/convex_initialization_comparison.json)

## Q06 群独立分支与主网

> 对每组建立独立网络分支，如何加主网或作为模块需要思考。

**实际完成：** 共享 hidden16、群残差 identity/ReLU 各三 seed；另比较硬/软成员后端并控制原头优化不足。

**结论：** 共享主网加群分支已经做有界比较。ReLU 没有概率/名单同时稳定优于同参数 identity；独立分支不是必然增益。

**边界：** 三 seed 仅初始化波动，固定预算不证明非凸全局最优；小群正例少使自由分支易不稳。

**现实决策：** 没有必要为交付强行保留群分支；采用与否由小组按目标决定。

**缺外部资料：** 没有新时期独立标签证明稳定收益。

**证据：**
- [README.md](../../validation-20261111/group-learning/README.md)
- [seed_summary.csv](../../validation-20261111/group-learning/seed_summary.csv)
- [README.md](../../validation-20261111/cluster-head-control/README.md)

## Q07 最终系统消融

> 消融必须做，可以等最终最好方案出来后再做。

**实际完成：** 先完成同口径候选，再冻结 full141 AE；执行 mean70、mean3040、AE-shuffled 预算/配对控制与六信息块逐一置零；五重叠 split、三 seed 和条件区间已保存。

**结论：** 用户要求的候选后系统消融已在冻结 AE 对象上执行，早期“后置/未开始”只属历史。额外监督预算未复现 AE 候选表现，但配对重建机制的收益仍无明确名单证据。

**边界：** 这不是所有潜在组合的穷尽删减；不据 Jan 去行为最高分继续扫组合。AE 在 July→Oct 31/1 低于基线36/2，不能升级稳定方案。

**现实决策：** 正式系统采用须由本人/小组明确；未采用不等于消融未做。

**缺外部资料：** 当前没有独立未来样本认证升级。

**证据：**
- [task_plan.md](../../ae-ablation-20261112/task_plan.md)
- [README.md](../../ae-ablation-20261112/budget/README.md)
- [README.md](../../ae-ablation-20261112/feature-groups/README.md)
- [README.md](../../ae-ablation-20261112/temporal/README.md)

## Q08 注意力机制

> 普通注意力、特征注意力或者更合适更复杂注意力机制都可尝试。

**实际完成：** 全局视图权重、样本视图 attention、列门控均已三 seed 比较；后续统一输入/校准/五 split 对照，列门未显示稳定额外收益。

**结论：** 已验证若干明确 attention/门控定义，没有因名字复杂就获益。样本视图 attention 在原规格较差；列门相对等权参照没有一致全面优势。

**边界：** GCN 不是 GAT；GAT 没有训练过。用户要求分析合适性而非必须穷尽实现，既有 GCN 无一致收益，故没有优先再扩 GAT。注意力权重不是因果重要性。

**现实决策：** 目前无需为完成研究追加 GAT；若正式解释模型须用实际实现名称。

**缺外部资料：** 无外部缺数据是本项必要计算阻塞；更多架构属于无限候选空间。

**证据：**
- [README.md](../../validation-20261111/representations/README.md)
- [README.md](../../common-comparison-20261112/README.md)
- 本地证据 `README.md`（未纳入公开包，需内部来源）
- 本地证据 `README.md`（未纳入公开包，需内部来源）

## Q09 异常检测与目标重合

> 试LOF等异常检测，看看与目标客户的重合率，低就算。

**实际完成：** LOF novelty 10/30/60 邻居、IsolationForest、RFM 诊断及随机/近期性/LR参照全部已跑；按预定弱支持规则停止异常后端。

**结论：** 原八字段 LOF/IF 全局命中30/26/35/32，低于既有 weightedLR50且AP较低；异常度不等于复购概率。按用户“低就算”要求结案。

**边界：** 个别略超随机不说明可替代预测器；没有将异常分数送新监督后端继续追分，也不证明所有异常方法无效。

**现实决策：** 本线停止无需再等本人开测。

**缺外部资料：** 无额外资料是本线结案前提。

**证据：**
- [README.md](../../validation-20261111/structure/README.md)
- [anomaly_outcomes.csv](../../validation-20261111/structure/anomaly_outcomes.csv)

## Q10 一次购买预测是否成立

> 135天前只买过一次，只有一次数据，预测未来90天复购会不会太荒谬？

**实际完成：** 区分六个月仅一单与终身仅一单、135天recency与次数；与同切片训练常数基率比较，给单单/久单 proper loss 与条件区间。

**结论：** 从相似客户学习群体风险在统计上可以做，但多数单单/久单增量概率收益区间跨0；不能承诺识别每个久单个体。

**边界：** 整体 Accuracy 约99.2%可由全不复购达到，不能代替概率误差和罕见事件诊断。

**现实决策：** 经理只能把名单视为风险/价值排序依据，不能当个体确定事实。

**缺外部资料：** 更长客户历史、真实触达和新独立未来标签缺失；不是未跑模型欠账。

**证据：**
- [no-information-and-single-order.csv](../../validation-20261111/probability/no-information-and-single-order.csv)
- [bootstrap-vs-scoped-no-information.csv](../../validation-20261111/probability/bootstrap-vs-scoped-no-information.csv)
- [proper-metrics.csv](../probability/proper-metrics.csv)

## Q11 最终验收和排序价值

> 最终是否验收所有客户预测误差？为何关心排序？是否预测准确后再按金额、频率、概率排序？

**实际完成：** 已对全体客户计算 LL/Brier/AP/AUC、校准和 sum(p)；最后批实际完成 6 个 Gamma 正支、18 套全体经理私表、1,296 行容量、36 行金额误差和 840 行 Jan 固定分数条件区间。

**结论：** 概率误差验收覆盖全体客户，排序是下游策略。固定10%下 pFM 和预计金额各在15/18组合捕获商品额高于p，预计金额11/18高于pFM；概率、命中、商品额与金额误差存在取舍，没有统一赢家。

**边界：** 18组合不是18个独立时期；大多条件区间含0。概率/价值执行已收完，正式采用和预算属于现实决策。100%覆盖不证明概率准、利润高或触达增量。

**现实决策：** 本人/小组决定正式采用版本；经理决定关心复购人数、商品额或触达成本。

**缺外部资料：** 缺毛利/退款/成本及干预对照，不能验证利润最大化或营销增量。

**证据：**
- [primary-eval-metrics.csv](../probability/primary-eval-metrics.csv)
- 本地证据 `amount-stage-manifest.json`（未纳入公开包，需内部来源）
- [amount-prediction-metrics.csv](../value/amount-prediction-metrics.csv)
- [capacity-results.csv](../value/capacity-results.csv)
- [value-report.md](../value/value-report.md)
- 本地证据 `independent-readback.json`（未纳入公开包，需内部来源）
- 本地证据 `value-manifest.json`（未纳入公开包，需内部来源）
- [jan-paired-bootstrap.csv](../value/jan-paired-bootstrap.csv)
- [original-formula-zero-analysis.csv](../value/original-formula-zero-analysis.csv)

## Q12 神经分类损失

> 分类神经网络是不是二元交叉熵损失？

**实际完成：** 既有MLP/GCN源码损失审计及P4 BCE、加权、focal、pairwise实现与结果已保存；GCN对比版另加.005双向InfoNCE。

**结论：** 普通二元神经分类主损失通常是 BCE，本项目须按实际版本说明：BCEWithLogitsLoss接logit，权重/对比辅助项另列；本批原生CB用Logloss。

**边界：** 不同加权/辅助项改变优化对象和概率尺度；成功停止不等于达到请求梯度或数学精确最优。

**现实决策：** 正式演示使用对应源码实际损失，避免把所有候选都叫同一BCE。

**缺外部资料：** 无需更多外部数据回答实现问题。

**证据：**
- 本地证据 `current-method-audit.md`（未纳入公开包，需内部来源）
- [README.md](../../validation-20261111/objectives/README.md)
- [training-status.csv](../probability/training-status.csv)

## Q13 纯预测与商业二阶段

> 不关心排序就没有容量，先纯机器学习再商业选择是否更好？

**实际完成：** 预测层输出全体 p；策略层接 p、历史F/M和条件金额，分别给概率/原式/预计金额排序及私有经理表；未来真值放另表。

**结论：** “先纯预测，再商业选择”已经成为实际两阶段接口。改变名单K不需重新限制模型输入。

**边界：** 能分层不保证商业层现实有效；pFM是手工偏好分，p×发生购买条件下未来90天商品总额预测才估计未来90天商品额。

**现实决策：** 经理按实际目标和名额选视图；正式采用仍由本人/团队确认。

**缺外部资料：** 无真实运营成本/干预数据，无法推出触达ROI。

**证据：**
- [README.md](../probability/README.md)
- [manager-guide.md](../value/manager-guide.md)
- [run_value.py](../value/run_value.py)
- [value-report.md](../value/value-report.md)
- 本地证据 `independent-readback.json`（未纳入公开包，需内部来源）
- 本地证据 `value-manifest.json`（未纳入公开包，需内部来源）
- [capacity-results.csv](../value/capacity-results.csv)
- [amount-prediction-metrics.csv](../value/amount-prediction-metrics.csv)
- [jan-paired-bootstrap.csv](../value/jan-paired-bootstrap.csv)
- [original-formula-zero-analysis.csv](../value/original-formula-zero-analysis.csv)

## Q14 目标不平衡与潜空间伪样本

> 是否有不平衡却没预处理？采样或参考论文在对比潜空间生成伪样本。

**实际完成：** 已做class_weight、ROS、SMOTENC、focal、pairwise与自然分布校准；做AE/NCE/同伪簇负对降权/潜原型一致性/中心对齐简化及负结果。

**结论：** 不平衡并未忽略，但这些方法没有一致获胜。论文借鉴已落实为明确定义的MVSIB-inspired简化，不是完整MVSIB复现，也没有为复购正类生成真实带标签交易。

**边界：** 少数伪簇不是y=1；SMOTENC非整数计数只是插值。原论文HN hinge方向、gate、中心参照和逐簇/汇总MMD口径有待资料澄清；旧官方快照缺model.py总训练函数。

**现实决策：** 用户要求借鉴，完整严格复现不构成当前必须追加工作。正式材料保留简化名称。

**缺外部资料：** 若要认证完整MVSIB，需要作者完整一致实现/公式解释与相应协议；当前资料不能支持此声称。

**证据：**
- [README.md](../../validation-20261111/objectives/README.md)
- [README.md](../../validation-20261111/representations/README.md)
- 本地证据 `paper-transfer.md`（未纳入公开包，需内部来源）
- 本地证据 `mvsib-transfer-notes.md`（未纳入公开包，需内部来源）

## Q15 三群、深度/软聚类和未知簇数

> 三群和kmeans硬划分是否合理？先深度嵌入，silhouette/elbow搜索K或不指定K方法。

**实际完成：** RFM/original8的K2..8、silhouette/elbow相关几何指标、GMM BIC软群、HDBSCAN、抽样稳定性、深latent K搜索及成员后端优化控制已完成。

**结论：** 三群不是已证明最优。有限训练几何偏好K2，GMM BIC偏好搜索上界K8；这些回答几何/密度，不能当复购最优K。

**边界：** HDBSCAN本地实现无训练外predict，不伪造Jan密度标签；深群原头预算不足已另做同成员高精度LR控制。

**现实决策：** H05 K3保留作共同诊断，不必为最终展示声称唯一真实分群。

**缺外部资料：** 未知真实簇结构没有标注，不能验证天然最佳群数；模型API训练外分配缺口已明确。

**证据：**
- [README.md](../../validation-20261111/structure/README.md)
- [README.md](../../validation-20261111/representations/README.md)
- [README.md](../../validation-20261111/cluster-head-control/README.md)
- 本地证据 `frozen-group-model.json`（未纳入公开包，需内部来源）

## Q16 不同视图影响分群

> 地区、距离等很多特征可能导致不同群，三群是不是不对？

**实际完成：** RFM与original8几何对照、地区/距离新增输入、多视图与删块对照已完成；最终批以旧H05冻结中心外推Nov/Dec并逐键复现Oct/Jan。

**结论：** 不同视图确实改变表示空间和分区；不能用跨空间silhouette绝对值直接裁定哪个商业分群正确。

**边界：** 冻结H05只作诊断不入X；新增地区不自动证明必须改K3，也不证明每个视图都值得给一套新群。

**现实决策：** 是否需要重新定义业务群由正式用途决定；当前共同诊断沿用既有标签。

**缺外部资料：** 缺真实客户意图/业务分群标注；不能把几何簇认证成客户动机。

**证据：**
- [README.md](../../validation-20261111/structure/README.md)
- [README.md](../../validation-20261111/features/README.md)
- [README.md](../../ae-ablation-20261112/feature-groups/README.md)
- [data-manifest.json](../data/data-manifest.json)

## Q17 其他机器学习方向

> 前面提到的合适机器学习方向也可以尝试。

**实际完成：** 已完成适合现目标的LR/树/神经/GCN、pairwise、校准、不平衡、表征和最后Gamma金额回归；没有穷尽所有算法。

**结论：** 生存分析、全部图注意力与所有排序目标不构成本次穷尽义务。当前固定任务是90天是否复购及商品额，已给对应合理模型与反例，继续加名字不自动增加可验证结论。

**边界：** 没有执行生存模型，不能说已比较下一次购买时间；没有GAT训练，不能混称GCN。

**现实决策：** 改变目标为“何时购买”才需要新的风险集/删失/时间指标设计，这是产品目标变化而非当前未完实验。

**缺外部资料：** 利润/增量目标需要成本/干预数据；完整独立未来评估需要新未来样本。

**证据：**
- [README.md](../../validation-20261111/objectives/README.md)
- 本地证据 `README.md`（未纳入公开包，需内部来源）
- [task_plan.md](../task_plan.md)
- 本地证据 `amount-stage-manifest.json`（未纳入公开包，需内部来源）

## Q18 研究过程与执行门禁

> 自由探索拓展，记录过程、分析发现并自主进一步实验；先记质疑，看完建模后统一开测。

**实际完成：** 2026-11-11后明确授权开测；已完成原验证、同口径、多seed/重叠split、AE消融、早期时点及最后滚动/价值固定批次。计划/哈希/失败/负结果/纠正与回放留存。

**结论：** 旧设计阶段“等待/新增0”是历史，不是当前门禁。最后批是一次冻结收束，不能因理论不确定性无限追加搜索。

**边界：** 研究完成与正式采用/本人提交/三端同步状态分别记录。源码、模型、汇总保存不自动等于GitHub/本地/线上已同步。

**现实决策：** 正式采用/成员收件/群稿由真实本人或组员记录；不代发、不把影子研究当成员交付。

**缺外部资料：** 真正盲测、毛利成本与干预证据缺失已结案为不可证明，不留“待用户开测”计算欠账。

**证据：**
- 本地证据 `task_plan.md`（未纳入公开包，需内部来源）
- [task_plan.md](../../common-comparison-20261112/task_plan.md)
- [task_plan.md](../../ae-ablation-20261112/task_plan.md)
- [task_plan.md](../task_plan.md)
- [replay-verification.json](../probability/replay-verification.json)
- 本地证据 `amount-independent-readback.json`（未纳入公开包，需内部来源）

## Q19 全体概率→原pFM/预计金额价值→经理名单

> 先给全体客户预测复购概率，再以购买次数/金额/概率形成价值分数交经理；并比较预计未来90天商品额。

**实际完成：** 6 cell 全体三种概率与6个Gamma正支已完成，全部fallback=false；18套全量经理私表、144个分数列、1,296行容量和36行金额误差由独立脚本回算；840行Jan条件区间已保存并独立核表结构与数量，没有第二次重跑bootstrap。

**结论：** 全体概率→价值分数→经理名单闭环已执行。主参考 p×F×M、字面敏感性 p×max(F−1,0)×M 与 p×发生购买条件下未来90天商品总额预测并列。固定10%时，pFM和预计金额各15/18组合捕获额高于p，预计金额11/18高于pFM；不能据此选唯一赢家。

**边界：** F/M均为历史六自然月，非终身；pFM重复强调频次，不是金额预测。Jan的F−1敏感性使28,665位单单客户零分，久单12,330位全部零分。18组合来自3个重叠已见窗口；大多固定分数条件区间含0，不含重训、搜索和漂移不确定性。预计商品额不含运费、利润或增量。

**现实决策：** 经理根据人数或商品额目标与容量选视图；正式采用由本人/小组确认。

**缺外部资料：** 成本、毛利、退款与触达反事实缺失；无法证明利润最优/营销增量。

**证据：**
- [README.md](../probability/README.md)
- 本地证据 `amount-stage-manifest.json`（未纳入公开包，需内部来源）
- 本地证据 `amount-independent-readback.json`（未纳入公开包，需内部来源）
- [manager-guide.md](../value/manager-guide.md)
- 本地证据 `value-manifest.json`（未纳入公开包，需内部来源）
- [value-report.md](../value/value-report.md)
- 本地证据 `independent-readback.json`（未纳入公开包，需内部来源）
- [capacity-results.csv](../value/capacity-results.csv)
- [amount-prediction-metrics.csv](../value/amount-prediction-metrics.csv)
- [jan-paired-bootstrap.csv](../value/jan-paired-bootstrap.csv)
- [original-formula-zero-analysis.csv](../value/original-formula-zero-analysis.csv)

## Q20 全量输入、全量字段、100%名单与10%的区别

> 澄清全体客户输入、所有可用字段输入、给经理100%或10%名单分别意味着什么。

**实际完成：** Nov/Dec/Jan全部23,260/26,848/29,368位合格客户均获三种概率和全部冻结价值分；base8/full141输入维度有明确allowlist；1/2/5/10/20/50/100%容量均执行。全部100%容量的名单人数、复购召回、金额份额与群基率精确率守恒通过。

**结论：** 全量客户是行维度，全可用字段是列维度，名单百分比是输出容量。100%选择全部合格客户，覆盖全部已观察复购与商品额，precision等于群体复购率，排序不改变该端点。10%用于资源有限场景及旧项目可比，从未限制概率模型输入。

**边界：** 141不含身份键、时间与未来y/G/N；所有全体概率和价值已实际输出，没有待跑容量计算。100%覆盖不能证明更准、利润更大、触达增量或经理能处理全部客户。

**现实决策：** 经理按可承受名额选择容量，科学评价继续覆盖全部客户；无需为容量变动重训概率模型。

**缺外部资料：** 实际人力/触达成本未给，不能认证最优名单长度。

**证据：**
- [data-manifest.json](../data/data-manifest.json)
- [README.md](../probability/README.md)
- [value-plan.md](../value/value-plan.md)
- [capacity-results.csv](../value/capacity-results.csv)
- [value-report.md](../value/value-report.md)
- 本地证据 `independent-readback.json`（未纳入公开包，需内部来源）
- 本地证据 `value-manifest.json`（未纳入公开包，需内部来源）
- [amount-prediction-metrics.csv](../value/amount-prediction-metrics.csv)
- [jan-paired-bootstrap.csv](../value/jan-paired-bootstrap.csv)
- [original-formula-zero-analysis.csv](../value/original-formula-zero-analysis.csv)

## 可证明范围与现实决定

本人/小组仍决定正式采用版本，经理仍决定人数、商品额、工作量与成本目标；这些是现实选择，不是未完成计算。没有真正未见未来、毛利/成本/退款或触达干预数据，无法认证独立未来泛化、利润最优和营销uplift。

GAT未训练，完整MVSIB未严格复现，生存模型未执行；已完成的合适性分析、GCN、注意力/门控、明确MVSIB-inspired简化和固定90天预测已按真实范围交付，不能冒认，也不把所有算法列为穷尽义务。

概率有界源审见 [报告](probability-source-audit.md)。审查者写过数据构造，没有写概率实现；独立于概率作者，不是数据构造未参与作者独审。此源审新增fit0。GitHub/本地/线上操作仍以根代理真实回执为准，本结案不预先宣布同步成功。
