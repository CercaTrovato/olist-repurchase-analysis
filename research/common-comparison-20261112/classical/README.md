# 统一经典模型矩阵

固定65格已完成：WLR10、未加权LR桥接10、统一编码CatBoost30、原生类别CatBoost桥接15。所有模型、信息档、训练划分与seed完整保留；不依据一月调参或挑种子。本目录只负责经典矩阵，跨家族/跨划分的配对结论由根统计统一汇总，不自动更换正式模型。

## 输入与公平比较范围

五个80/20分层划分来自根shared loader，split20261111..20261115。各fit16928/169正例、cal4232/42正例，Jan29368/230全量评分，权威久单H05 cluster1=12330/90、独立top79。编码X均float64，维度依次808/813/817/813/812；base8保留原8独立log1p/StandardScaler/state-OHE的34个编码列，其他列由根loader置0。WLR/ULR/编码CB读取与神经分支完全相同的信息档X，不自行split/重编码。

nativeCB是单列桥接：原141列、8个原生类别，类别缺失__MISSING__，数值只用fitmedian填补、不log/scale；因此与编码CB不同输入表达，不能当完全相同X的模型效应。原静态/录入回写假设承接P2，不声称恢复严格生产历史时点。

WLR C1/balanced、ULR只把class_weight改None，均LBFGS tol1e-10 max5000。CB depth3/iterations300/lr.03/l2_leaf_reg10/unweighted/CPU2；无eval_set、无earlystop。原全Oct训练50命中存档未覆盖，不能与本轮80%fit当同训练信息的模型效应。

## 求解与实测收敛

20个LR中实际归一化梯度inf<=1e-10有0个；有warning的0个。真实停止message分布：{'CONVERGENCE: REL_REDUCTION_OF_F_<=_FACTR*EPSMCH': 20}。无warning/优化器success不代表满足配置gtol。详见LR-optimization-diagnostics.csv与私有完整梯度。

LR独立核sum weighted BCE+0.5||coef||²/C，intercept不罚。WLR正/负样本权重为N/(2*Nclass)，ULR均为1；完整sum目标梯度与求解器加权均值尺度梯度同时报告，二者相差weight_sum16928。捕获SciPy返回fun/jac/options，验证fun*weight_sum与独立sum目标、内部jac_inf与独立归一化梯度吻合。优化器因ftol停止时照实保留，没有临时更改参数或追加拟合挑赢家。

所有45个CB都实际训练300轮，完整13500行fit Logloss在CB-fit-loss.csv；fit loss只是训练曲线，不是Jan科学验证。CPU2时间见training-summary.csv，小试4个正式格保存后直接复用，未额外重训。

## 统一校准、输出与核验

每个run均调用根eval_harness.write_run，使用同4232自然分布cal进行受约束单调Platt，概率/排序/全体与群域由根统一计算。WLR raw为训练先验尺度诊断，prior修正与calibrated版本分开。cal的calibrated指标为校准拟合内读数，不称无偏。主策略按根协议使用raw logit；校准输出的实际名单差异也保留。

本目录已核65模型×fit/cal/Jan=195次重载，logits误差全部0，三期raw logits与根scoreNPZ逐元素一致，均float64；根score文件SHA、1400指标行/560容量行及所有输入SHA在收尾回读。raw→calibrated全局K2937名单有非零选择差异的模型数=0，这是实际有限精度/极小斜率读数，不能未经核对概括为一律不变。

公共聚合为metrics.csv、capacities.csv、training-summary.csv、LR-optimization-diagnostics.csv、calibration-diagnostics.csv、CB-fit-loss.csv；单run-record.json包含相同根级聚合。private保留model.joblib/model.cbm、原始float64三期logits、完整sum梯度、每轮fit loss、native填补值和根统一校准分数/参数。公共文件不含客户键/逐人分数。

代码为本机执行记录：依赖根eval_harness.py、shared/data-manifest.json及其私有矩阵/原表，不是独立可下载一键复现包。最终训练源码/参数/根schema SHA在frozen-config.json，源输入/每split文件SHA在metadata.source。classical_engine原语不做校准，只有根harness拟合Platt；未更改共享数据或候选科学配置。

本目录图只说明训练曲线与求解器；三seed/五训练划分都不是独立未来时期。科学质量、共同久单、配对差/名单稳定性与固定分数区间由根statistics按预先规则汇总，不把某个最高seed或旧全Oct成绩当稳定提升。没有April新评分/标签解析、Git、看板、依赖安装或外部写入。
