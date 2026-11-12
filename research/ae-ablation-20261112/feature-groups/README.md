# 六信息块条件依赖验证

正式矩阵为六个 leave-one-view-zero 条件 × 五个 fit/cal split × 三个初始化，共 90 个独立 AE20+BCE50，已全部完成，失败 0。正式训练及保存/校准等主进程共 975.39 秒；另有 fit-only 计时小试，不纳正式 90 格。每格 1,340 次重建更新和 1,700 次监督更新，共 120,600 次重建更新、153,000 次监督更新、106,646,400 客户输入曝光。原始 CPU 耗时受同机并发与 I/O 影响，不据此宣称精确 FLOPs 匹配。

独立读回 90 个监督 state、90 个预训 state：fit/cal/Jan 全部 logit 逐元素完全一致，max abs diff = 0；校准概率、全部父指标与容量名单统计完全一致，校准参数可重现，最终 fit 重建 MSE 完全一致。30 组 split/view 的完整源矩阵及旧 full AE 15 个基线记录/分数哈希保持不变。证据为 `execution-verification.json`、`readback-verification.json`、`model-readback.csv`；训练图已实际查看，图例、轴及限制说明可见。

`run_feature_groups.py` 直接导入父 `eval_harness.py` 与 `neural/neural_models.py`。六块来自父 manifest 的 `view_order` 与各 split `dims`；`seller_context` 对外 family 写作 `AE-drop-seller-context`。每个条件从未改的完整 float32 矩阵复制，在 fit/cal/Jan 同段置零，保留全部列与六分支。`input-mask-audit.json` 逐段列出区间、维数、mask/hash、三期输入 hash 与 nnz，核其余列逐元素相同。预训重建目标也为遮蔽输入。

旧 full AE 15 格只读复用，encoder/head 初始化、20 轮重建及 50 轮监督的客户排列 hash 与对应 split/seed 原件相同。所有模型仅 fit 训练；父正斜率 Platt 只用 cal，Jan 为已见的一月评价。父 `write_run` 的 `root_plan_sha256` 是历史父计划；本轮现行 `followup_plan_sha256`、本分工计划及 candidate-freeze SHA 均另存于每格 metadata。

逐人分数、模型、预训 state 与逐格完整曲线位于 `private/`，不公开。`verify_feature_groups.py` 是独立的保存 state 前向、校准和父指标回算脚本；公共训练诊断图仅聚合 15 格曲线的均值及范围。MSE 在不同置零条件下对应不同难度，不能直接据此排名原始信息块。

解释范围：零分支仍能通过 bias 学到常量，其余块可能携带语义代理，移除目标段也使重建更容易。因此结果表示条件于其余五块的依赖、冗余与补偿，不能视作原始信息的纯因果 importance，六项影响不能相加。删除某块后改善只记录为线索，本轮不按 Jan 继续删字段或调参。研究候选未转为小组正式采用。
