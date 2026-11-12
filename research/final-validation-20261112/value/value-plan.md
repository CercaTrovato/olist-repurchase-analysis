# 价值层冻结执行单

2026-11-12。唯一写入者 final_value；仅 value/ 及对应 scratch。主代理核 data READY 并明确放行后先完成 6 个金额模型；等待 probability manifest 也 READY 才联合评价及 bootstrap。不访问四月快照或标签，不修改旧源，不执行 Git、看板或外部消息。

依赖：data/private/cells/{V}__{single|pooled}/{fit,cal,eval}.csv，双键 customer_unique_id,snapshot_date。金额输入 F/M/average_order_value/max_order_value；标签 y/future_gmv/future_orders；R 为历史最近购买间隔；cluster=1 为 long。概率来自 probability/private/cells/{cell}/primary-eval-probabilities.csv，p_wlr/p_ulr/p_catboost（已校准且 CB 三 seed 均值）。全部连接按双键一对一，逐项核 SHA。

金额模型严格 6 个 cell 各 1 个：仅 fit 的 future_gmv>0 行，log1p+StandardScaler 只 fit 此正支；GammaRegressor(alpha=1,max_iter=2000,tol=1e-8)，G 除训练正支均值再拟合，回乘后限于 [0,训练正支最大 G]。保留异常、拟合警告、未限幅输出与限幅计数；失败使用训练正支均值，禁止根据 eval 选择参数。保留重复客户/原订单按预测机会等权的支持统计。

每 p 固定 6 分数：p；p*max(F-1,0)*M；p*F*M；p*M；p*(M/F)；p*Ghat_conditional。另历史 M、-R、随机期望参照。F>=1 才能定义 AOV，遇不满足即停止而不悄悄改式。仅 p*Ghat 与 p*训练正支 G 均值作 E[G] 金额预测指标，其余只是排序分。

容量固定 1/2/5/10/20/50/100%，K=ceil(N*比例)，同分按双键升序。long79 是 cluster=1 内另外独立排序的固定 79 席，单独报告，不能与全局名单中的 long 席位混淆。每项报告 hits、precision/recall、G/份额、N、long 席位/hits/G、边界同分及零分。100% 必等实际总体，precision 为群基率。

bootstrap 已冻结为仅 canonical Jan：single/pooled × 3 概率家族，共用 Jan 全体 2000 次配对复制客户 counts、重排全局 10%（K2937）；long 群另外 2000 次配对 counts、K79。7 容量全部只做点估计，禁止据最好 K 选择规则。每个同概率家族/策略下，各非 p 规则 vs p，及各不同规则 vs 主原式 p*F*M；p*max(F-1,0)*M 是字面复购次数的敏感性，不是唯一原式参照。所有金额/份额/命中/订单/long 金额/long 命中/long 席位比较共用同次 counts。区间只反映固定分数下评价客户重抽样，不含重训、搜索或漂移；三个相邻窗口不构成三个独立未来实验。

主科学计划冻结 SHA256：c6d0ff58feed195bc4db1a803813faaedebb4fd7902874168d4139faeb24c1f4。金额正支少、极端金额可能支配结果，必须报告最大金额客户与 Top1% 真实 G 贡献。Gamma 的 alpha/tol/迭代次数、4 输入、正支训练、目标缩放、限幅和失败保留均不依据评价结果改变。

经理私表只含截至预测日可知字段、模型预测、排序及分数，真实未来 y/G/N 在独立私有评估旁表。公共仅聚合、图、代码和 manager-guide.md。
