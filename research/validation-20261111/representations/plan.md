# P4C 固定预算表征、融合与深聚类验证

执行前冻结。CPU 线程 2；不安装、不解析 April、不改源数据/Git/看板。输入为 P2 141 个结构列，六视图，不含文本。上轮 paper-transfer.md 已读；本研究为明确定义的 MVSIB-inspired 改造，不称复现。HN hinge、gate、pull、MMD 口径歧义保持，本文不执行未经澄清 HN 分支。

## 切分与监督阶段

Oct 按原表顺序用 stratified train_test_split(test_size=.2,random_state=20261111)，fit16928，cal4232，自然标签比例。全部预处理仅 fit16928；cal 只用于 Platt。Jan 全29368只transform/评分，不调字段/epoch/K/超参。H05 权威 cluster_id=1 久单12330/90，top79。seed2026/2027/2028，所有种子完整保留。

数值训练median、非负log1p（负数与坐标原值）、StandardScaler、每列固定缺失指示；类别缺失标记与OHE min_frequency20 train-only。每视图 Linear(d_v,16)+ReLU，共识16维，Linear(16,1) BCE头。50epoch batch512 Adam(lr=.001)，未加权BCE，dropout0，不early-stop。全部真实监督阶段同预算；预训练系列先无监督20epoch，再全参数BCE微调50epoch，明确为监督适配，不混称冻结表征后端。

固定监督四格：mean（等权均值）、global（6个全局softmax参数，不称attention）、view-attention（共享 Linear16->8、tanh、Linear8->1，逐样本softmax六视图）、column-gate（每个编码后列g=sigmoid(a*x+b)，a=b=0起始，再同mean架构）。参数差异逐项报告，不调宽度。

## 论文启发预训练五格

同mean主体，六个Linear(16,d_v) decoder仅预训练使用。固定20epoch batch256 Adam.001，所有格/seed相同预算。每步两份独立feature-drop=.1，重建为各视图MSE平均。下列累计加入，所有系数预先固定，未按Jan选择：

1. AE：原输入重建MSE。
2. AE-NCE：mask双增广重建MSE + .005*标准双向InfoNCE，temperature=.2。
3. AE-NCE-FN：同上，InfoNCE分母中“同训练伪簇而非本人的负对”乘.1；正对不降权，不删客户。伪簇由预处理fit-X的KMeans(K3,n_init10,seed各实验seed)固定获得，无y/cal/Jan。此为明确简化FN候选，非论文不确定性路由/FN真值。
4. AE-NCE-FN-prototype：额外.005*潜原型一致性。按fit伪簇人数<fitN/3识别少数簇；batch该簇>=2时潜向量均值+高斯噪声生成P=2潜原型，方差=(P/n_batch)*diag(cov)+1e-4。约束该簇当前归一化均值与归一化伪原型MSE。仅pretrain unsupervised，不赋复购y、不入BCE；不足2跳过并记录。简化为对角协方差，无MMD/排斥/安全边界复现。
5. AE-NCE-FN-prototype-centroid：再加.005*各视图伪簇中心与共识同簇中心的MSE平均（batch>=2）。使用固定伪簇，非论文完整簇对比。

训练loss分项、伪簇规模、原型生成/跳过批次、全局权重/样本注意力分布保存。pseudo少数簇不等于真实复购少数类。

## 深聚类小格

只在最后一格的无监督预训练latent（BCE微调前）拟合KMeans K2..8；固定fit子样本至多2000、silhouette最大选K，平手小K，绝不用cal/Jan/y选K。各seed分别选K。报告K与簇数，深latent hard一热 / soft softmax(-平方距离/fit距离median)仅成员输入，同线性BCE头50epoch。共同对照为fit RFM(log1p+StandardScaler) K3的hard/soft成员，同后端/预算。完整四格x3seed；不是另起无限搜索。

## 评价与冻结边界

所有候选raw logits排名，raw sigmoid与仅Oct-cal Platt(LogisticRegression C1e6)概率并报。Logloss/Brier/AP/AUC、0.5指标，全局K2937及5/10/20%容量，久单79。Platt若斜率为负须明示；raw-score容量固定保持，不用cal/Jan选阈值。科学质量与商业捕获并列，不自动选最终模型。

正式矩阵为9主体格x3seed=27监督结果，其中5x3=15预训练；深聚类4x3=12头结果，共39原始模型结果、各raw/Platt两种概率。先两epoch小试计时，报告实际维度/参数和外推预算，再整跑。private保存预处理、矩阵、split键、模型、latent和逐人分数；公开聚合CSV/PNG/SVG及源码/config/manifest，不外发。最终系统消融仍待候选冻结后。
