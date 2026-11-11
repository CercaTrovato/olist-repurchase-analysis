# 七个既有 LR 的数值停止精度控制

冻结于 2026-11-11，先于本批任何新 Jan 结果。新增原因是同 fit/X 的 P4 发现默认 tol1e-4 可能过早停止；这是必要的数值稳健性控制，**不是模型机制增益或根据 Jan 调参**。

唯一矩阵：原 full-Oct LR3 / LR8 / weightedLR；P2 lr8 / lr8-geo / full-structure / structure-text，共7个模型，各1次确定性重拟合，无seed重复。仅将既有 sklearn LogisticRegression 的 tol 统一改为1e-10、max_iter5000；其余solver=lbfgs、C、class_weight、penalty、初始规则和全部字段保持原值。不再调tol/C/特征/校准，不据Jan选择候选。

只读既有read_dev前50528行（Oct21160/211，Jan29368/230）；前三项直接使用保存的已fit原预处理转换，不重新fit预处理；P2四项直接用保存Oct/Jan sparse矩阵，原样本与列顺序。先核旧模型评分重现存档，随后clone原estimator只改tol/max_iter拟合。旧基线不覆盖。四月快照/标签解析0。

训练目标统一报告 sum weighted BCE + ||β||²/(2C)，bias不罚；balanced权重=n/(2n_class)，未加权全1。记录旧/新niter、停止参数、警告、同目标值、sum梯度∞及除样本权重和后的梯度尺度。sklearn没有公开完整optimizer状态，不把无警告自动说成满足梯度阈值；若5000触顶或警告，保留失败/不确定状态，不追加搜索。

Jan全客户对比raw Logloss/Brier/AP/AUC，global2937、H05-km3-v1 cluster_id1 n12330/90内独立79；固定按分数降序、customer_unique_id/snapshot_date升序破平。报告最大/平均概率差、名单对称差和替换人数、命中变化，不把它解释为额外信息或模块效果。不用Jan扫阈值，不加calibration以免混入不同变化。

CPU threadpool_limits2，工程估计约30–120秒但真实时长运行后记录，max_iter提供有界预算。新模型和逐人score仅convergence/private；外层plan/代码/聚合CSV/PNG/SVG/回执。最终独立读回模型与所有指标。不写Git/看板、不安装、不外发、不改原件或原产物。只有当前目录与任务scratch为本次写入范围。
