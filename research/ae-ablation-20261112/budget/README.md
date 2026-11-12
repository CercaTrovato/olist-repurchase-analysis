# AE 研究候选：训练预算与重建配对对照

本目录是固定候选之后的研究验证。它不代表团队正式采用，1 月也不是新盲测；新矩阵不按 1 月表现挑 seed 或 epoch。总体比较及条件 bootstrap 由上级 `ae-followup` 统一计算，此处保留 45 个正式拟合的独立执行与核验证据。

| 格 | 重建更新 | 监督更新 | 监督客户输入次数 | 总客户输入次数 |
|---|---:|---:|---:|---:|
| mean70 | 0 | 2380 | 1184960 | 1184960 |
| mean3040 | 0 | 3040 | 1513760 | 1513760 |
| AE-shuffled | 1340 | 1700 | 846400 | 1184960 |

每格是 5 个重叠 fit/cal 划分 ×3 个初始化。mean70 的 70 个完整监督 epoch 与旧 AE20+50 的总输入 epoch 相同；mean3040 的更新次数与旧 AE20+50 相同，但连续使用监督 Adam，89 个完整 epoch 后只再用 14 个批次。两者均不表示 FLOPs、标签曝光或实际耗时精确相同。30 个纯监督模型还记录第 50 个 epoch 的 encoder/head 状态 SHA，与只读旧 mean50 原件核对，以区分延长预算和改变初始化/训练前缀。

AE-shuffled 保留旧 AE 的 20 轮重建、50 轮监督、输入顺序、架构及优化设置，把同一批次目标换成另一客户；六视图使用同一无固定点随机置换，独立目标随机生成器不影响输入序列。在线曲线是打乱目标的训练损失；最终 aligned MSE 是对原客户重建的诊断，不能混作训练目标。更长监督或打乱目标是否也有收益，需要结合父目录的预定配对比较解释。

`source-freeze.json` 绑定新计划、候选、预算代码、旧模型/评价源码及五组输入矩阵与划分哈希；每个正式 run 的 metadata 明确绑定新 followup，而非把新实验伪装成旧 155-run 计划。`pilot-timing.json` 是冻结后丢弃的 fit-only 小试：额外 3 个两轮监督拟合、1 个两轮预训练拟合，无校准或 1 月评分；这些不计入 45 个正式模型。

公开聚合入口：`training-budget-summary.csv`、`run-support.csv`、`common-metrics.csv`、`common-capacities.csv`、`ensemble-metrics.csv`、`ensemble-capacities.csv`。单 run 和三 seed 的校准概率平均分别保留；不能把 seed 指标均值当成系统指标，也不能把五个重叠划分当五个独立时期。`budget-training-diagnostics.png/.svg` 展示监督曲线、打乱目标重建曲线和观测训练耗时；耗时受到同机其他任务影响。

核验入口：`readback-verification.json`、`model-replay.csv`、`metric-replay.csv`、`calibration-status.csv`、`failures.json`。独立回放从已保存 state_dict 用函数式线性层前向，重新核算 fit BCE 总损失及 cal/Jan 指标；不修改分数。NN 实际执行是 float32，保存 logits 为 float64 容器。校准优化器的 success 与实际 projected-gradient residual 分开报告。

所有逐客户 logits/概率、模型权重和各模型完整曲线都在 `private/`，不进入公开附件白名单。`deliverable-manifest.json` 记录交付文件哈希；原输入、旧模型、旧分数及 4 月数据均未改动。
