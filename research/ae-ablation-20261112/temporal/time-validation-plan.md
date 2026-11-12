# 七月训练 → 已见十月评价：准入后的独立时间诊断

2026-11-12。本分支是数据恢复和时间口径审计通过后新增的小型时间诊断，不属于原 135 项预算／字段块消融，不修改原计划、一月参数或既有结果。十月目标曾用于开发，不能称新盲测。不得据本分支结果调整架构、字段、超参、预算或再挑窗口。

## 固定数据与信息

直接只读 `../time-audit/private/july-full141.csv` 和 `october-full141.csv`。七月 14,012 人／120 正例，十月 21,160 人／211 正例。唯一分层 80/20 拆分 `random_state=20261111`；fit/cal 客户索引排序后固定并私有保存，人数及正例由实际拆分记录。所有 median、scale、OHE 和原生 CatBoost numeric median 只 fit July-fit，July-cal 只用于校准，Oct 只用于评价。

完整 141 字段和六块划分与父 `feature-views.json` 一致：behavior 11、geography 21、products 30、commerce 51、service 21、seller_context 7。y、客户／快照键及 cluster_id 绝不作为 X。保留 base8/full141 两信息档的共同编码空间；base8 将所有新增编码列置 0、不缩维。这里只在 base8 上拟合一次 WLR；其余四家族只拟合 full141。

编码复制父 `prepare_shared.py`：六块各自数值 fit-median（全缺失回退 0），非负 log1p、负值原值，纬经度保持原值，fit StandardScaler；只为非 base8 数值加固定 missing flag。base8 的 state 独立 OHE、无 rare 合并、未知忽略；其余分类 OHE `min_frequency=20, handle_unknown=infrequent_if_exist`。原生 CatBoost 只做 fit 数值中位数、类别 `__MISSING__`，不 log、不 scale。

十月评价群仅合并既有 H05 `is6400-local-round2-20261110/role-04/train_clusters.csv`；cluster1 须为 9,121 人／78 正例。群号仅诊断，不构造七月群，不作为模型输入。

## 冻结模型：13 次监督拟合 + 3 次 AE 预训

- WLR-base8：一次，`C=1, class_weight=balanced, solver=lbfgs, tol=1e-10, max_iter=5000, random_state=2026`。
- full141 mean：seed 2026/2027/2028；父 `neural_models.py`，六块各 Linear(d,16)+ReLU、等权均值、线性 head；50 个监督 epoch。
- full141 AE20+50：同三 seed、同初始化；20 个重建 epoch 后去 decoder，50 个监督 epoch。父原函数，无目标打乱或新消融。
- full141 encodedCB 与 nativeCB：各三 seed；`depth=3, iterations=300, learning_rate=.03, l2_leaf_reg=10, loss_function=Logloss, CPU/thread_count=2, use_best_model=False`，不传 eval_set、早停或类别权重。

NN 固定 CPU2、Adam lr=.001、dropout0、监督 batch512、重建 batch256；数据次序与 seed 机制直接复用父函数。没有 gate、调参、早停或试探性模型。WLR 输入 float64，CB float64／原生类别；NN 实际 float32，logits 统一 float64 容器。

每个监督模型只在 July-cal 以父 `fit_monotone_platt` 拟合正斜率 Platt，保留 optimizer success、残差和边界状态。每家族三 seed 主结果是三个校准概率逐客户平均，不平均 logits、不另做集成校准。WLR 单模型校准概率为基准；其 raw 与 prior-offset 概率只作诊断。July-cal 校准后指标标为 calibrator 的原样本回读，不能称独立泛化。

## 固定评价与产物

新 harness 以实际十月分母计算：global10% `ceil(.1*21160)=2116`，5%=1058、20%=4232；久单 cluster1 独立固定79。并报告全体、group0/1/2、久单的 LL/Brier/AP/AUC，global 各群席位及命中；recall 分母分别为实际群正例（久单78、全体211）。客户 ID、快照作为同分时确定排序键，绝不进入 X。不调用父 `write_run`、旧硬编码 29368/230/2937。

保存模型、fit/cal/Oct logits、逐客概率、calibrator、拟合变换、行键与 split 到本分支 private/；公开候选仅汇总指标、容量、训练曲线、方案与源码。完成后用独立源文件重新加载变换／模型前向、复算概率／指标／排序；未过回读不写 complete。不生成新时期 bootstrap 或多窗口结果。

约束继续明确：七月历史 Jan1–4 下单／批准零记录原因未知；源完整性和静态属性／支付／预计日期等原入库及改写假设没有新日志证明。七月与十月共享 9,076 客户；七月整个目标日历事件池 12,261 笔，匹配七月 cohort 实际复购 129 笔／120人；这些已发生事件合法进入十月历史但不使两期独立。现行目标和历史均按批准时间窗口；此前核查的未来批准订单实际入史0。完整141复现不是生产asof认证。

先以 `--freeze` 仅检查字段、实际拆分与源哈希，不 fit 变换或模型。根任务明确 READY 后才允许 `--run`。`--run` 逐一核冻结源哈希且拒绝覆盖已存在的执行标记；结果失败原样保留，不自行重跑。无四月快照／标签／评分，无 Git／看板操作；原 time-audit 文件不改。
