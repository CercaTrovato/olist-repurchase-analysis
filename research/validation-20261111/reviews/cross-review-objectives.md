# P4B 独立交叉方法审查

范围：objectives 的预定不平衡/损失矩阵。本审查未参与 P4B 的撰写、训练或参数选择；只读模型、fit/cal隔离、采样产物和分数，未调用任何 fit、未训练新模型、未解析 April。未把本人参与的 P4C 当作独立审查对象。

结论：未发现阻塞这份固定矩阵作为开发比较归档的来源隔离或计算错误。独立重放20模型×cal/Jan共40次，独立重算400行LL/Brier/AP/AUC与200行容量，均与输出相符；最大logit和概率误差均为0。本结论不代表模型采用、显著优势、跨期稳定或最终系统消融已完成。

## 实际核查与证据

- 只通过原 bounded read_dev 取 Oct/Jan 50528行，Oct21160/211、Jan29368/230；未读取April快照/标签。6项源SHA与运行回执一致；10个核心矩阵/分数/脚本文件在本审查开始与结束时哈希未变。
- fit16928/169正例与cal4232/42正例客户键完全不交叉；原始fit/cal索引与保存manifest一致。保存preprocessor的fit_keys精确等于fit集合，数值scaler均值独立与fit的log1p值核对，OHE类别等于fit类别，保存fit矩阵逐元素复算相符。未发现cal/Jan参与变换拟合的迹象。
- 独立用保存权重手算线性decision score，不调用作者predict_logit或infer；随后独立计算sigmoid、prior offset和Platt。40次重放匹配两期落盘分数。作者independent-verification.json所称40次/400指标/200策略的工程证据又被本次独立核实；作者脚本自身仍不是另一代理审查，本报告才是本次交叉审查。
- Jan共同久单逐键连接权威validation_clusters.csv，cluster_id=1，12330人/90正例；没有用本地重新聚类的群号代替。Top2937和久单79均按score降序、customer_unique_id升序重算。
- 所有20个Platt斜率为正；本次额外逐名单检查raw→Platt/prior在K2937与久单79的选择状态，全部0变化。这一事实只覆盖P4B，不能推广到P4C或其他负斜率校准。

## 指定主表逐seed独立重算

确定性未加权LR仅一份；SMOTENC、focal、pairwise逐seed列出。pairwise原始分数不是自然概率，LL留空。下表全部与metrics-all-scopes.csv及strategy-capacities.csv一致。

| 方法 | Seed | 概率/分数 | LL | AP | K2937 Hits | 共同久单79 Hits |
|---|---:|---|---:|---:|---:|---:|
| LR-unweighted | 单次 | raw | 0.045268279 | 0.029552817 | 47 | 2 |
| LR-unweighted | 单次 | Platt | 0.045455061 | 0.029552817 | 47 | 2 |
| SMOTENC-LR-seed2026 | 2026 | raw | 0.634625708 | 0.028067345 | 45 | 1 |
| SMOTENC-LR-seed2026 | 2026 | prior | 0.048055914 | 0.028067345 | 45 | 1 |
| SMOTENC-LR-seed2026 | 2026 | Platt | 0.045915316 | 0.028067345 | 45 | 1 |
| SMOTENC-LR-seed2027 | 2027 | raw | 0.633174870 | 0.028013405 | 47 | 1 |
| SMOTENC-LR-seed2027 | 2027 | prior | 0.048104540 | 0.028013405 | 47 | 1 |
| SMOTENC-LR-seed2027 | 2027 | Platt | 0.045916373 | 0.028013405 | 47 | 1 |
| SMOTENC-LR-seed2028 | 2028 | raw | 0.634058410 | 0.028250786 | 46 | 1 |
| SMOTENC-LR-seed2028 | 2028 | prior | 0.048080797 | 0.028250786 | 46 | 1 |
| SMOTENC-LR-seed2028 | 2028 | Platt | 0.045916598 | 0.028250786 | 46 | 1 |
| torch-focal-seed2026 | 2026 | raw | 0.176840113 | 0.031788025 | 43 | 1 |
| torch-focal-seed2026 | 2026 | Platt | 0.045324313 | 0.031788025 | 43 | 1 |
| torch-pairwise-seed2026 | 2026 | raw-ranking | —（排序分数） | 0.025882129 | 44 | 2 |
| torch-pairwise-seed2026 | 2026 | Platt | 0.045683905 | 0.025882129 | 44 | 2 |
| torch-focal-seed2027 | 2027 | raw | 0.175817231 | 0.031256769 | 46 | 1 |
| torch-focal-seed2027 | 2027 | Platt | 0.045340669 | 0.031256769 | 46 | 1 |
| torch-pairwise-seed2027 | 2027 | raw-ranking | —（排序分数） | 0.025827394 | 42 | 2 |
| torch-pairwise-seed2027 | 2027 | Platt | 0.045666174 | 0.025827394 | 42 | 2 |
| torch-focal-seed2028 | 2028 | raw | 0.175064243 | 0.031864704 | 46 | 1 |
| torch-focal-seed2028 | 2028 | Platt | 0.045280035 | 0.031864704 | 46 | 1 |
| torch-pairwise-seed2028 | 2028 | raw-ranking | —（排序分数） | 0.027657258 | 41 | 1 |
| torch-pairwise-seed2028 | 2028 | Platt | 0.045624433 | 0.027657258 | 41 | 1 |

## 合成、参数与预算审查

SMOTENC的categorical_features=[7]、k_neighbors=5、1:1目标与代码/保存sampler一致。每seed的原始前16928行精确等于原fit的7个已变换数值+state ordinal，原标签前缀一致；16590条新增行全为训练正类，邻居模型只含169个fit少数样本，合成state均属于原fit合法类别。未发现cal/Jan被当合成源。ROS索引亦全部落在0..16927。

| Seed | SMOTENC新增行 | 逆变换F非整数 | 逆变换recent30_orders非整数 |
|---|---:|---:|---:|
| 2026 | 16590 | 347 | 388 |
| 2027 | 16590 | 369 | 360 |
| 2028 | 16590 | 377 | 357 |

上述非整数不是本次落盘结果的计算错误，而是将计数当连续数值插值的既定SMOTENC假设。它能作为统计训练对照，但不能称合成了真实、逐笔合法的交易客户；state合法不等于全部业务约束成立。建议发布叙述补这条边界，不为改善成绩临时取整/重采样。此路线也不是论文的潜空间少数簇增强。

四个torch目标均34输入、35参数、无隐藏层、150epoch、17updates/epoch、共2550updates；12个torch run的history合计30600steps。BCE/focal/weighted-BCE每epoch16×1024+544个客户；pairwise每epoch8450pairs（169正例每人50个负对，放回抽负例），分498+16×497，且仅fit。所有数据与参数记录可追溯。

相同步数不等于相同统计曝光：BCE每个正例每epoch一次，pairwise每个正例50次，约16900客户端点曝光与16928接近也不能消除这一差异。focal的alpha=.5是对所有类别共同乘.5，再乘难度项；即使固定L2=.001，不同损失尺度下的有效正则化强度也不等价。因此可以称“同一线性头、固定更新预算的目标对照”，不能声称所有优化条件完全等价或把收益仅归因某个抽象损失名字。sklearn C=1/LBFGS与torch显式L2/Adam更不能作为完全相同优化轨迹。

## 概率、排序与结论边界

1. focal+Platt三seed AP均值约.031636高于未加权LR的.029553，但K2937为43/46/46，低于或等于LR47，久单均1低于LR2；AP不是固定容量命中的替代品。其Platt LL均值.045315仍高于本矩阵LR raw .045268，不能由单项AP自动改用focal。
2. SMOTENC改变正类条件分布，不只是改变先验。减log(16759/169)是有限假设下的尺度修正，不能保证修复合成偏差；其prior LL约.048080较全局常数更差、Platt后仍未胜LR，现有README对此解释合理。
3. pairwise原始截距可平移，原排序分数不报LL/Brier；仅Octcal Platt后计算proper指标，代码与表格一致。P4B全部校准正斜率且名单未变，只能说概率尺度被改变，不是新增信息或命中。
4. cal只有42正例，Octcal Platt读数在用于拟合校准的同一标签上，属于拟合内诊断。Jan已见、没有新增未见时间验证；三seed SD/范围仅初始化或重采样波动，非置信区间，不包含数据抽样/时间漂移/候选搜索不确定性。确定性LR未虚构三个seed。

## 待跟进与本审查的边界

P4B未加权LR的47与P4A严格优化参照44之间差异，作者正在单列数值诊断；本审查确认P4B保存模型确实重现47，不把尚未完成的跨矩阵诊断认定为原矩阵算错。诊断应保留原矩阵、指出实际tol/预处理/求解器/行序/边界名单证据，不能未经核实写成纯浮点噪音。完成后由主代理核其诊断与发布叙述。

审查时主文validation-execution.md尚未合入P4最终结果，本任务已明确该文处于汇总中，故未将其缺少最终P4结果记为缺陷。此前P2“极小浮点差”的表述与本次P4B审查分开，由主代理维护；不因此重训或扩大本矩阵。

本次未检查所有真实订单约束、训练标签是否足以支持未来营销增量、外部部署、最终候选消融或其他矩阵本身；这些不是本报告已放行范围。

## 本次审查留痕

- 独立脚本：E:/app-data/codex/scratchpad/is6400-validation-20261111/cross-review-objectives/audit.py；SHA256=9412ad389fb99c9f688243c1d27d4ec4d226f2e8c003f28fa3f2d7fc542e4b6f。
- 该脚本仅读取bounded源、保存模型和分数，无fit调用；不执行作者run_objectives.main或verify_and_summarize.main。
- 独立回执：E:/app-data/codex/scratchpad/is6400-validation-20261111/cross-review-objectives/receipt.json。
- 指定主表精确重算CSV：E:/app-data/codex/scratchpad/is6400-validation-20261111/cross-review-objectives/requested-main-table-recomputed.csv。
- 校准前后名单逐项核查：E:/app-data/codex/scratchpad/is6400-validation-20261111/cross-review-objectives/list-order-audit.json。
- 输出仅本报告与scratch审查证据；无模型/分数/原件/Git/看板/安装/外部写入。
