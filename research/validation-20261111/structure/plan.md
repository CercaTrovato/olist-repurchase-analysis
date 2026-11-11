# P3 冻结配置

冻结于 2026-11-11，主计划 `../task_plan.md` 已解除开测门禁。仅使用既有 `read_dev()` 读取 H02 开头 50,528 行，Oct 21,160 / 211 阳性，Jan 29,368 / 230 阳性；不解析四月。

1. 空间 `rfm`：R 原值、log1p(F)、log1p(M)，StandardScaler 仅 Oct fit；空间 `original8`：原预测模型 7 个数值字段 log1p 后标准化，state 训练侧 OHE（ignore unknown）。原“8 字段”含 state，不是 8 个数值。
2. KMeans K=2..8，seed=42，n_init=20，max_iter=300，tol=1e-4，Lloyd。固定 seed=2026 抽 Oct 2,000 人计算 silhouette；DB/CH 和最小群规模用全 Oct。每空间 silhouette 最大者当选；差距 <=1e-3 按较小 K。仅 winner 和 K=3 各做 3 次 80% 无放回训练抽样（seeds 2026/2027/2028），固定原 Oct 变换并预测同一全 Oct 参考集，ARI 对全样本拟合模型。
3. GMM diagonal K=2..8，seed=42，max_iter=300，n_init=1，reg_covar=1e-6；训练 BIC 最小者当选。BIC、几何 silhouette 与未来预测效果分别解释。保留 winner 与 K3 模型/labels/后验权重。
4. sklearn HDBSCAN，min_cluster_size=200/500，min_samples=20，其余库默认，Oct fit；记录 noise、簇规模、训练侧 silhouette（排除 noise）以及相同三次 80% 抽样交集 ARI（包含/排除 noise 各报）。当前第三方 hdbscan 未安装；sklearn HDBSCAN 没有 out-of-sample predict，不给 Jan 假标签。
5. LOF novelty=True，n_neighbors=10/30/60，contamination=auto；IsolationForest n_estimators=200，contamination=auto，seed=2026。只在 Oct fit、Jan score_samples，异常度为负 score_samples，越大越异常。两个表示均报，主空间 original8。LOF 训练 negative_outlier_factor 不与 Jan novelty 分数混用。
6. 不用 Jan y 选择空间、K、阈值或异常超参。固定异常排名 top 5/10/20%（ceil），同 K=2937 报 precision/recall/lift、AP，ROC AUC 辅助；固定久单为 H05-km3-v1 cluster_id=1（Jan 12,330 人 / 90 正例），在这个群内独立排名选 79 人，另报指标和随机期望。共同 H05 只作诊断，新聚类不替换这个切片。基准随机期望、recency 与已有 weighted LR 一并报告。异常值不是概率，不计算未校准 log loss/Brier。
7. 固定 CPU threadpool_limits(2)。模型、变换、键、逐人 labels/distances/soft weights/scores 放 private；外层仅聚合 CSV、PNG/SVG、报告、代码及哈希。无安装、外发、Git、看板和原件写入。
8. 预定停止：若主空间三组 LOF 与 IF 在 K2937 的 hits 均不超过既有 weighted LR 50，且 AP 不超过 weighted LR，则记为本组方法无明显增益，不自动叠后端；若某项超过只作为已见 Jan 线索，交主代理决定，不能称稳健胜出。一月已见，目标日历重叠/重复客户仍为限制。
