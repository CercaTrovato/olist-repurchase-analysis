# 仅簇成员预测头：优化充分性控制

冻结于2026-11-11，先于本项任何新Jan评分。触发证据是P4C原50epoch仅成员线性头的fit BCE高于fit基率常数0.0559255（optimization-audit.csv），尚不足以归因表征。该控制只检查已冻结成员的预测头优化，不改变表征、聚类、K、学习率或seed，不依据Jan挑选配置，原50epoch矩阵完整保留。

## 固定12格

读取 representations/private 下实际文件名 `{rfm,deep}-{hard,soft}-{2026,2027,2028}-{fit,cal,january}-memberships.npy`。成员顺序对应P4C `october-split.csv` 中按原顺序的fit/cal、源Jan CSV行序；标签取保存fit/cal-matrix.npz，并核源键／y；所有成员只读。

每格仅一次 LogisticRegression(C=1,solver='lbfgs',tol=1e-10,max_iter=5000,fit_intercept=True,class_weight=None)。不标准化或重构成员，不重新训练编码器／KMeans。模型仅fit成员16928人／169正例；cal4232人／42正例仅拟合Platt(C=1e6,solver=lbfgs,max_iter=2000,class_weight=None,tol=1e-10)。Jan29368/230只评估。保留实际objective、sum和mean梯度、迭代、warning、耗时；请求tol不等于证明达到该梯度。

主对照严格为同一格原50epoch raw、新LR raw、新LR Platt，共36版本；不把额外12格称新表征。原raw的LL/AP沿用原保存概率，容量沿用原raw_logit排序；新raw使用新logit排名，新Platt使用其校准概率排名，斜率若为负明确报告方向变化，不概称校准保序。旧Platt仍留原目录，仅附参照不新增拟合或更换旧策略。

额外两种直观基率参照：fit全局169/16928；按权威H05三个群的fit标签估计固定Beta(1,99)平滑基率 p_g=(positive_g+1)/(fit_n_g+100)。fit群来自原train_clusters.csv按双键连接；cal/Jan只分配已有权威群，不按新聚类编号冒充久单。两参照不新fit Platt。

## 评估／证据

全体自然LL/Brier/AP/AUC；global5/10/20%固定K1469/2937/5874及共同H05 group1的12330/90内固定79。每格训练fit BCE与常数、原50epoch最后记录并列，拟合内指标只说明优化，不声称泛化。cal原／校准读数均仅诊断，校准后同cal标签再代入不称无偏。三seed全部保留，确定性相同成员若得到相同结果如实记录，不择优seed。

保存private模型、训练键、cal/Jan所有分数；外层聚合CSV、简单PNG/SVG、源码／运行回执。CPU2threads。完成计算先向根汇报结果，再进行独立落盘材料读回。所有来源SHA保持不变；不Git／看板／安装／外发，April行读取0。
