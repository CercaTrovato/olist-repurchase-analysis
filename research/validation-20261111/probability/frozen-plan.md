# P1 概率质量与分类／策略分离：冻结方案

冻结日期 2026-11-11。仅调用已核 bounded read_dev：前 50,528 行，Oct 21,160／211、Jan 29,368／230；April 快照标签行解析数 0。所有客户参与评价，不先按群／高分筛选。

1. 完整承接既有 17 方法；按一对一 customer_unique_id + snapshot_date 对齐并验证 y、cluster_id。11 个 predict_proba 原输出可算 Logloss/Brier；recency、simpleMulti、3 个 rank blends 只作排序，不能把 0–1 rank 当概率。group-shrink100 是 logit，保留原策略另显式新增 sigmoid(logit) 概率候选。balanced 输出不隐去失校准。
2. 增加 Oct 常数基率、未加权 LR3／LR8、weightedLR raw、解析先验修正 p=sigmoid(logit(raw)-log(nneg/npos))、weightedLR Oct OOF Platt。Oct 3 折 StratifiedKFold(shuffle=True,random_state=20261111)，每折单独拟合预处理与模型，保持原 LR 参数；Jan 预测用全 Oct 拟合模型。Platt 为 C=1e6 的单变量 logit LR，原始 Oct 自然类别比例，不加权。Jan 不 fit 校准或选阈值。
3. 每个概率候选报告全体／cluster 0／long cluster 1／cluster 2 的自然 Logloss、Brier、AP/AUC、0.5 Accuracy/F1/MCC／混淆矩阵；有 Oct OOF 的新增系列额外报告 Oct OOF maxF1 固定阈值，阈值并列时取最高阈值。Platt 后 OOF 是开发读数：校准器使用同一 OOF 标签拟合，不声称嵌套无偏内部性能；maxF1 仅开发选择，不用 Jan。
4. 概率校准 10 分位 bins，边界只用 Oct 分数。新系列用 OOF 分数；既有方法用已存全 Oct 模型的 Oct 拟合分数（只决定边界，不评价训练准确度）。重复边界保留空 bins，外端扩为 +/-inf；输出每个 bin 原边界、n、events、mean_probability、observed_rate、95% Wilson CI，含空 bins。预测总数与事件逐表守恒。
5. 旧 17 及新增候选 AP/AUC 和全体 Top10%=2937、long79 独立保留；不以 Accuracy 为唯一主指标，不把容量选择当 0.5 分类。不增加模型采用结论。
6. 关键概率候选相对 Oct 常数／LR8／weightedLR raw 的 Logloss 和 Brier 均值差，所有四个群域各 2,000 次配对客户 bootstrap(seed=20261111+scope_index)。固定模型／分数不重训，95% percentile CI；负值表示 proper loss 改善。多个候选探索，不称未见时间泛化或校正多重检验。
7. 所有分数、OOF、折号、模型 joblib／重评分器、bins／曲线 CSV、PNG/SVG、代码与输入／输出 SHA256 落盘。只写 probability 目录，不改原件、不 Git／看板／外部消息、不安装。

先验修正是假设权重只改变先验下的解析调整，正则化和模型误设下不保证校准；Platt 是经验拟合。单单／久单信息不足只按本组数据的 proper/ranking 证据给有限结论，不能称无可学习信息。Q01／Q03／Q12 事实承接，不另造新时间窗。

补充预定诊断（不据 Jan 选模型）：为直接回答单单信息质疑，另列 F=1 全体；比较 Oct 同切片常数与始终预测负类，给全体／三个群／F=1 的 proper 与分类读数。Jan 同切片真实基率只作理论最佳常数诊断，明确不可部署；关键候选相对 Oct 同切片常数的固定分数配对 bootstrap 2,000 次（seed=20261121+scope_index）。不改变主 21 方法或原冻结候选。
