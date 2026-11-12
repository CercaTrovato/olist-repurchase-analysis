# AE 固定候选验证：统一统计

本次处理完整 135 个新模型与候选冻结清单的 65 个既有模型，共 200 个分数原件、14 个系统、70 个系统×划分组合。没有新增拟合或修改源分数。主系统按同一客户平均三 seed 的校准概率，再用这一个概率评价损失、排序与名单；WLR 每个划分只有一个确定性模型。单 seed 的指标均值及波动另存，不能替代主系统。

当前结果不支持把“多训练一些监督轮数”当成 AE 命中收益的完整解释，也不支持宣布 AE 全指标获胜。配对重建相对打乱目标保留了一些排序线索，但打乱目标在概率损失上可以更好；移除 behavior 的全局命中改善是条件冗余或噪声线索，尚不能证明可以稳定删去该信息块。这里没有正式替团队采用新方案。

| canonical 20261111 三 seed 概率融合 | 全局 Logloss | 全局 AP | global2937 命中 | long79 命中 |
|---|---:|---:|---:|---:|
| AE-full | 0.045582 | 0.022033 | 51 | 4 |
| mean50 | 0.045302 | 0.021852 | 52 | 3 |
| mean70 | 0.045785 | 0.021084 | 50 | 2 |
| mean3040 | 0.046021 | 0.024491 | 41 | 0 |
| AE-shuffled | 0.045261 | 0.020527 | 50 | 3 |
| AE-drop-behavior | 0.045445 | 0.024011 | 58 | 4 |
| WLR-base8 | 0.045788 | 0.026114 | 43 | 2 |

完整 14 系统及全部容量政策见 `ensemble-primary-by-split.csv` 和 `ensemble-capacities-by-split.csv`，不据这张节选表选优。

- mean70/mean3040 对 AE-full 的全局与久单命中都在五个重叠划分中下降。canonical 全局命中差分别为 -1（条件 95% 区间 [-9, 6]）与 -10（[-21, 1]）；单次命中区间仍宽。mean3040 全局 Logloss 差为 +0.000439（[+0.000245, +0.000646]）。30 个预算模型的第 50 epoch 状态与旧 mean50 精确相同，预算控制证据见相邻 budget 目录。
- AE-shuffled 对 AE-full 的 AP 在 all 与 long 两个范围的五划分中均下降；全局命中 1 胜 4 负，久单 0 胜 1 平 4 负。canonical 全局 Logloss 则改善 -0.000321（[-0.000509, -0.000132]），AP 差 -0.001507（[-0.005857, +0.000287]），命中差 -1（[-7, 5]）。配对重建的排序线索与概率损失须分开解释。
- AE-drop-behavior 全局命中在五划分都增加 +3 至 +7；canonical 差 +7（[-1, 16]）。久单差为 0（[-2, 4]），五划分 1 胜 2 平 2 负。全局 Logloss 虽 canonical 改善，但五划分仅 2 胜 3 负；不能只挑这一个 canonical 值。零分支常量、其余块代理信息及更易重建的目标共同限制解释，六块影响不能相加。
- AE-full 对 WLR-base8 canonical 全局命中差 +8（[-4, 20]），久单 +2（[-3, 6]）；全局 AP 差 -0.004081（[-0.017909, +0.006372]）。结果仍有目标权衡及较大不确定性。

`canonical-paired-bootstrap-intervals.csv` 保存全部 25 个预定对照×2 范围×7 指标＝350 条区间。每个范围对完整 14 系统使用相同的 2000 次客户复制计数，在复制观测池中重新排序并保留 K2937/K79；重复客户没有被去重。区间以冻结 score 为条件，不含重训、候选选择或时间漂移。1 月已经用于开发，存在多重探索；这些区间不是新的盲测认证。

`five-overlapping-split-directions.csv` 是描述性方向与范围，`selection-stability.csv` 保留跨 seed、跨划分及新格对 AE-full 的名单 Jaccard。五个划分共享同一 1 月客户，不是五个独立时期。July→October 的单独诊断不在本矩阵中，也没有用它改变对照或候选。

图示入口共三族，均有 PNG/SVG：`budget-canonical-conditional-intervals`、`blocks-canonical-conditional-intervals`、`five-split-directions-and-list-stability`。原冻结 renderer 保留；`render_public.py` 是只调整标签长度和刻度数的呈现补充，`presentation-supplement.json` 记录数据未变及输出哈希。

执行与回读：`source-freeze.json` 绑定计划和统计源码，`input-binding.json` 绑定全部 200 份 record/score SHA；200 份源指标差异为 0。`readback-verification.json` 记录独立重算 70 格概率融合（最大差 0）、140 个主点及 350 个区间分位数。200/200 校准优化器 success，实际最大 projected-gradient residual 为 6.251879e-6，不能把 success 直接说成精确最优。此处是统计实施验证，不冒充作者预算实验的独立审查。

逐人数据、名单及全部 56,000 行 bootstrap 明细只在 `private/`；公开仅源码、计划、聚合表与图。`deliverable-manifest.json` 提供文件哈希。
