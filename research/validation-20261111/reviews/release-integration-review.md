# 最终发布整合定向检查

范围：候选发布工作树 `git-release` 的 `README.md → docs/team/current-status.md → docs/team/validation-execution.md` 顺读，以及 P2 两个已修生成源码的复制状态。本次不重训、不重新执行模型；不把审查者撰写的 P3/P4A/convergence 称为独立科学审查，涉及这些章节仅核入口状态、表述边界与链接整合。

**当前回读未发现新增的实质发布阻塞。** 先前入口 P4 状态滞后已在主代理更新后定向关闭；最终进度导出与群成员后端控制文件复制仍由主代理按已说明的收尾步骤完成，不把正在完成的动作记为遗漏。

## 已关闭的定向事项

1. 根 README 当前第 15 行和 current-status 第 66 行都已写为“P4 首批固定矩阵完成核验，并补数值优化控制”，与 validation-execution 的阶段表一致。最终模型、正式主指标及候选冻结后的 P5 系统消融仍待定，没有把局部矩阵完成写成最终系统采用。历史业务候选/旧名单数保留，主文有新的数值控制并列和原值边界。
2. 主文 P2 已明确更多字段与模型类型的混合归因，旧 LR8 与 P2 LR8 的 rare OHE/固定缺失指示差异也单列解释；没有继续称纯浮点噪声。
3. **F2 发布副本正式关闭**：发布树 `features/run_features.py` 与 `finalize_features.py` 已与输出源按规范化换行后的文本逐字一致；两者都有 `LONG_CLUSTER=1`，运行构造含 12,330/90 断言，旧“久单79也未超过基线”模板句不再出现。发布文件 SHA256 分别为 `49cb902949a55d1fdd25bfefa61b02c6fdfae3e2c773d4b3cc64ec44805b8a88` / `33e52c6db262430f0998b7da946e6729152457618cd72f808b442667292d9be0`。这关闭此前 cross-review-foundation 中“源已修、发布副本待复制”的收尾项。

## 方法与当前/历史状态衔接

- 原 P1 数字、历史四月回放与当前新模型结果没有混为同一训练预算。P4 明确 fit16,928/cal4,232；主文交代原全 Oct 的 50 命中不能当同预算基线。
- 同 fit/X 的 44 与 47 归因于停止精度控制，主文已明确其不是群模块收益；原 P1 的条件 bootstrap 区间没有移植到新优化 score，也没有把不同矩阵最高值排成统一因果榜。
- P4C 主表标为 raw Log loss/AP 和 raw 名单；正文明确一个负 Platt 斜率会翻转排名，因此校准后 AP 不能嫁接原始容量读数。P4B 的保序结论只限其自身已记录的正斜率，不被主文推广成“所有校准都保序”。
- 预训练额外预算、AE→NCE 同时增加 mask、单个 seed/三个 seed 与真正未见时间验证的区别均保留；最终候选和 P5 待定与完成首批实验不冲突。成员待回传也没有被本地模型完成替代。

本段是文档整合检查，不重新认证各作者计算或审查者自己的模型结论。

## 链接定向核验

三个入口合计检查 63 个本地链接。工作树缺文件的 5 项中：

- `progress/timeline.json`、`progress/daily-plan.json`、`slides/briefing-script-bilingual.md`、`slides/olist-repurchase-briefing.pptx` 均由 `git ls-tree -r --name-only HEAD -- <paths>` 确认在既有 HEAD 跟踪。Slides 两项 `git ls-files -t` 为 `S`，是 sparse checkout 省略，**不认定为缺链**。主代理已说明 progress 两文件将由 timeline.py 同源导出；本检查不声称该最新导出已完成。
- `cluster-head-control/README.md` 是主代理明确正在最后复制的已完成新结果，本次按指令保留为收尾待回读，不列为实质缺失。未重审其计算或因当时尚未复制而判失败。
- 其余 58 个目标在当前工作树可访问；使用的“倒排计划”锚点与实际标题匹配。新 P4/P1/P2 导航没有发现错误路径。

本次只执行只读的 Git 路径存在性/skip-worktree 查询，没有提交、推送、切换或修改索引；没有操作看板。发布前仍由主代理核实际最新 progress 导出、群成员控制复制和最终 evidence manifest，整合检查不代替三端同步回执。
