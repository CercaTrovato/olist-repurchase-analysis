# P4C 多视图融合、预训练与深聚类结果

已完成 39 个固定预算模型：四个监督融合格、五个预训练格及四个聚类成员后端，各 seed2026/2027/2028。所有 January 客户均评分，所有原始结果保留，没有按一月选择模型/种子/epoch/K。January 已见，只是开发验证。

## 共同控制与证据

141 个结构原始列分六视图；仅 fit16928 拟合后编码 814 维，视图维度46/507/103/102/42/14。fit16928/169正例，cal4232/42正例；同一 stratified random_state=20261111 切分。所有监督50epoch、batch512、Adam.001、未加权BCE、dropout0，无early-stop。预训练20epoch batch256，随后全参数BCE微调；不是冻结编码器的纯无监督复现。

mean/global/view-attention/column-gate 参数13137/13143/13282/14765；预训练含decoder26975，监督阶段移除decoder。全局6个softmax权重不称样本attention；样本attention为共享16->8->1门；列门是对814个编码列逐列sigmoid(a*x+b)，并非原始141列一一权重。

Platt 只用同4232自然分布cal拟合，所有raw logit/cal概率/校准数据保存private。概率指标允许显示Platt对排序的改变，但容量始终按raw logit排序；如斜率为负，Platt会反转排序，不能把原始排名的捕获指标嫁接到校准后排序。只有42个cal正例，校准斜率本身可能不稳。

负 Platt 斜率格数：1，详见 verification.json 与 run-audit.json；全部保留，没有因表现删掉。

## 三种子读数

下表为三seed均值；seed-summary.csv保存std/min/max。图中横线仅三次初始化的min/max，不是置信区间，也不证明跨期稳定性。

| 候选 | raw Logloss | Platt Logloss | raw AP | Platt AP | raw AUC | K2937 raw-ranking mean | 久单79 raw-ranking mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| mean | 0.045318 | 0.045255 | 0.017354 | 0.017354 | 0.605202 | 51.33 | 2.33 |
| global | 0.045289 | 0.045299 | 0.017717 | 0.017717 | 0.607648 | 53.33 | 1.67 |
| view-attention | 0.055166 | 0.045956 | 0.015303 | 0.011647 | 0.579775 | 37.33 | 2.33 |
| column-gate | 0.045304 | 0.045332 | 0.018023 | 0.018023 | 0.607306 | 55.33 | 2.67 |
| AE | 0.045221 | 0.045301 | 0.018754 | 0.018754 | 0.608326 | 51.33 | 4.33 |
| AE-NCE | 0.045247 | 0.045316 | 0.020227 | 0.020227 | 0.606196 | 52.33 | 3.67 |
| AE-NCE-FN | 0.045266 | 0.045330 | 0.019817 | 0.019817 | 0.605215 | 52.00 | 4.00 |
| AE-NCE-FN-prototype | 0.045273 | 0.045332 | 0.019011 | 0.019011 | 0.605270 | 52.33 | 4.00 |
| AE-NCE-FN-prototype-centroid | 0.045246 | 0.045298 | 0.020446 | 0.020446 | 0.605079 | 53.67 | 2.33 |
| rfm-hard | 0.108405 | 0.045645 | 0.010425 | 0.010425 | 0.518061 | 37.33 | 2.00 |
| rfm-soft | 0.106324 | 0.045615 | 0.016674 | 0.016674 | 0.539122 | 36.67 | 0.67 |
| deep-hard | 0.119193 | 0.045727 | 0.010135 | 0.010135 | 0.541147 | 38.00 | 2.00 |
| deep-soft | 0.120910 | 0.045798 | 0.022199 | 0.022199 | 0.538135 | 47.33 | 1.00 |

adjacent-component-differences.csv逐seed保留相邻变化。AE->AE-NCE同时加入双mask增广和InfoNCE，不能把差异单独归因于InfoNCE。mean->AE还增加20epoch无监督预算；AE各格之间预训练预算完全一致。三seed负结果不证明所有注意力/表征方法都无效；不得用其中最优seed宣称稳定提升。

## 论文机制与简化

已读上轮 paper-transfer.md。本文是MVSIB-inspired适配：同伪簇负对只在InfoNCE分母乘.1，不改正对、不删客户、不用真y判FN；伪簇仅fit-X K3。少数簇按人数<fitN/3，绝不等同复购正类；每个有效batch采P2个对角协方差潜向量，仅无监督潜原型一致性，不赋复购y、不送BCE。最后加入视图/共识同簇均值MSE。

没有实现原论文不确定性路由、HN hinge/gate、完整MMD、伪样本排斥或安全边界；原论文符号/门控/中心参照歧义未在本实验擅自声称消解。当前FN、prototype、centroid是明确定义的新简化，不称MVSIB精确复现或理论保证。伪原型生成/跳过次数与簇规模记录run-audit，预训练四分项loss在private。

深聚类使用最后一格BCE之前的无监督fit latent，K2..8按fit-only sample2000 silhouette选K，不用cal/Jan/y；各seed K选择与全部候选silhouette见deep-k-selection.csv。hard一热与soft负平方距离温度成员送同线性BCE头50epoch，对照fit-RFM K3 hard/soft。此处变换与KMeans均不与Jan共同拟合。

## 文件、复核与执行依赖

公开聚合：january-metrics.csv（含自然概率、0.5混淆/precision/recall/F1），january-capacity.csv（raw排名K2937、5/10/20%、共同久单cluster1固定79），seed-summary.csv、adjacent-component-differences.csv、deep-k-selection.csv、fusion-weight-distribution.csv、PNG/SVG。private保留变换参数、OHE、同split键、fit/cal/Jan矩阵、模型、cal数据、全Jan raw logits/两种概率、无监督latent、cluster成员和列门分布。

保存模型逐行重评分、全部指标与名单捕获从private回算、输入与split SHA核验均记录verification.json。共同久单权威H05-km3-v1 cluster_id=1、12330/90，非重新KMeans标签。

源码是本机执行记录，依赖同目录../features/private两张P2对齐表、feature-views.json及历史H05 validation_clusters.csv；不是独立一键复现包。完整依赖与SHA在input-audit.json，代码按run_representations.py、finalize_representations.py运行；需本机已装PyTorch/sklearn，无安装行为。P2静态属性/支付回写缺日志假设继续适用。P2原五候选使用全部21160训练，本轮仅16928拟合，跨两阶段数值不能解释为单模块效果。

April快照/标签解析0；无源数据/Git/看板写入、无外发、无依赖安装。最终系统正式消融仍待候选冻结后；本实验相邻差异只是预定模块验证。

## 结果可支持的结论与有限预算限制

四个监督融合格中，global和列门的平均AP/全局捕获小幅上升，但逐seed并非所有概率指标都改善；样本view-attention三seed raw Logloss均比mean差，不能因“使用注意力”就宣称更优。AE相对mean三seed raw Logloss和AP均改善，但它新增20epoch无监督预算；NCE、FN、prototype、centroid逐项变化不是单调改善，不能声称模块越齐效果越好。

深latent三seed均按fit silhouette选K2，较小簇528/528/513人；高silhouette只证明该几何划分分离，不代表划分能预测复购。仅簇成员线性头的50epoch最终fit BCE仍高于常数基率基线（详见optimization-audit.csv），固定Adam预算存在明显优化限制，raw Logloss差不能单独归因于表征本身；Platt改善概率刻度也不等于补回模型信息。未因此临时改变学习率、初始化或epoch。

本轮策略明确固定raw-logit排名；主表单列Platt AP，不能把校准后AP与raw名单当成同一套决策规则。view-attention seed2026的Platt负斜率来自仅42正例cal支持，方向反转是需要保留的不稳定事实，不推广为“校准都保序”。

RFMlog 参考的具体口径：本矩阵对 R、F、M 三列全部 log1p，再仅fit训练部分 StandardScaler/KMeans K3；P3/P4A及H05采用R原值、仅logF/logM，因此这里的rfm-hard/rfm-soft不称H05复现，跨矩阵deep对H05的差异不能直接归因于深表征。共同久单诊断仍逐键使用权威H05 cluster_id=1，不由本矩阵RFM重新编号。
