# 已绑定producer与内部规范化接口

2026-11-12根已给真实schema，producer_adapter.py精确映射并记录来源；缺失／冲突时报错，不猜列。此次只绑定共享数据，不读取未齐模型记录或分数。

每个监督模型的身份：`split_id`（五个指定整数）、`information`（base8/full141）、`family`、`seed`（确定性WLR为null）、`model_id`。nativeCB标独立`family`且只full141。需源文件路径／SHA和fit/cal/Jan键清单或共同矩阵manifest。

每模型Jan评分规范化表：`customer_unique_id,snapshot_date,cluster_id,y,raw_logit,calibrated_probability`。可选`raw_probability,prior_probability`只供指定概率诊断，不作默认ensemble。所有行必须与共同Jan权威键、标签、群逐项一致；同模型内双键唯一，N29368/y230，long12330/90。

汇总指标规范化表每行：模型身份＋`scope`（all/cluster_0/cluster_1_long/cluster_2）、`probability_variant`＋`logloss,brier,AP,AUC`；策略附`policy,k,hits,precision,recall,global_long_selected,global_long_hits`。若根harness只提供全体／久单，以逐人score重算补齐，不伪造源表。

训练／校准manifest：每split原8列索引、完整视图维数、base/full矩阵哈希、effective_columns；每模型参数数／训练预算／停止信息；Platt的a/b、下界、active-bound和实际梯度／KKT；全部错误。各split共同fit/cal键哈希必须一模一样，保证同split的受控配对。

canonical统计主规则已在根计划改为mean(calibrated probability)，adapter核对完成后才能执行。根还在结果前补充unweightedLR10拟合，155监督模型；两种LR各1run，不伪造seed。当前没有读模型新结果，没有bootstrap／模型采用结论。

真实producer文件为classical/{run_id}-record.json、neural/{run_id}-record.json。tags为run_id/family/information/split_id/seed；LR seed=null。family精确为weightedLR/unweightedLR/encodedCatBoost/mean/column-gate/AE/nativeCatBoost，information为base8/full141。native只full141，单列编码及缺失处理包桥接，包含missing flags、median、log/scale，不能仅归类别编码因果。

record含score_file（相对批次根）、score_sha256、metrics/capacities/calibration/metadata及shared_manifest_sha256/root_plan_sha256/eval_harness_sha256。NPZ含fit/cal/jan各时段的_logit、_raw、_calibrated，weightedLR另有_prior。一维数组行序严格对应eval_harness.load_frames(split_id)的fit/cal/jan，均带KEY/y/cluster_id/F。

metric条目variant=raw/calibrated/可选prior，period=cal/jan，scope=all/group0/group1/group2/F1，分别规范到all/cluster_0/cluster_1_long/cluster_2/single_order_F1。capacity政策global2937/global5/global20/long79，含各群名额／命中。主单run同主ensemble统一calibrated probability，raw sigmoid/prior和mean-logit均单列诊断；protocol-clarification.md补充SHA纳入binding，不覆盖旧计划或记录。

adapter的freeze_binding只读共享输入，不枚举classical/neural。load_complete_matrix首先检查statistics/RUN_STATS.authorization.json（仅根明确允许完整155模型RUN_STATS后记录），再核155个预定身份齐全唯一，之后才打开score NPZ。绑定所有根源码、补充协议、数据manifest和统计源码SHA；拒绝缺失、重复、越根路径、哈希或数组shape不符。主矩阵140+native15=155，AE预训练30另计。
