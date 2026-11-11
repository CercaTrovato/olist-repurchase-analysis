# 执行记录

首轮实现把 BCE 每epoch客户均分为17份（995/996人），虽然更新步数和最大batch符合预算，但没有精确执行预定batch1024。发现后保留首轮完整代码／参数／模型／分数／结果于 `private/initial-equal-batches-run.zip`，不删负结果、不以指标选择保留版本。

正式矩阵将 BCE 改为16个1024 + 1个544，ranking仍将8450pairs均分17份（497/498对），均2550steps；按同一预定配置完整重跑。没有扩大参数搜索或据Jan修改损失／超参。以下主目录结果均为改正batch实现后的正式版本；首轮仅历史实现偏差，不混入3seed汇总。

独立读回脚本首调遇原H02已有 `split` 与本地fit/cal `split` 合并重名，出现 `AttributeError: 'DataFrame' object has no attribute 'split'`；仅将核验脚本本地合并列改名 `partition` 后继续，训练、预测、数据分割均未改变。正式读回400项指标／200项策略通过。
