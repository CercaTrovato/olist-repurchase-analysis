# 155格统一比较的完整统计

本批统计及独立读回已经完成。模型没有重训，四月没有新读快照/标签或评分。此前README中的“等待RUN_STATS”是结果前骨架状态，原字节保存在private/README-before-completion.md；不把旧状态继续显示为当前。

[主结论与候选建议](../README.md) · [冻结统计方案](statistics-plan.md) · [来源与共享矩阵审查](shared-source-review.md)

## 主规则与完成量

先核155个身份/score SHA再读分数。单run主规则为校准概率；canonical split20261111的随机模型取三个校准概率的平均值，确定性LR一份。概率误差、AP/AUC和名单同一score。raw/prior是独立诊断；cal校准后读数在同cal标签上拟合，不当无偏泛化。

全部3200概率行、1280容量行已独立复算，与producer差0。13个canonical概率均值逐人核对误差0。52,000行bootstrap复制结果来自all和long各2000个共同计数，区间不含重训/选模/时间漂移。

- [全部模型概率指标](all-run-metrics.csv) · [全部模型策略](all-run-capacities.csv) · [训练元数据](all-run-training-metadata.json)
- [模型×字段：每split先平均seed指标](main-model-information-by-split.csv) · [五split摘要](main-model-information-five-split.csv)
- [逐seed配对差](controlled-paired-differences-by-seed.csv) · [逐split配对差](controlled-paired-differences-by-split.csv) · [重叠split方向](five-overlapping-split-directions.csv)
- [canonical概率指标](canonical-ensemble-metrics.csv) · [canonical名单/群覆盖](canonical-ensemble-capacities.csv) · [主条件区间](canonical-paired-bootstrap-intervals.csv)
- [完整复制结果gzip](canonical-bootstrap-replicates.csv.gz) · [原始均值logit诊断](canonical-raw-mean-logit-diagnostic.csv)
- [名单稳定性](selection-stability-pairs.csv) · [校准实际优化](calibration-optimization-audit.csv) · [有限精度排名对应](finite-ranking-correspondence.csv)

## 候选读法

canonical基线43/久单2；完整字段mean52/3、gate52/3、AE51/4、encodedCB46/1、nativeCB49/2。前三者相对基线全局+9/+9/+8的95%固定score条件区间为[-4,22]/[-3,21]/[-4,20]，久单+1/+1/+2均为[-3,6]，不能声称稳定命中优势。

CB两种表示的全体/久单Logloss差条件区间均小于0；AP与名单差区间仍包含0。概率质量与容量名单不是同一指标。原生CB桥接改变编码/数值变换/缺失处理整包，不能单独归类别编码。

[结果后探索性同字段完整配对](exploratory-complete-same-information-canonical-CI.csv) 单独保留36对；从既存同rep_id复制结果相减，没有新bootstrap或训练，不伪称原冻结的单项确认性检验。gate/AE相对full mean全体Logloss更大，名单差区间仍含0；它不是正式系统机制消融。

## 两种“跨split稳定”不可混淆

原主表先平均每seed的指标，回答单次模型波动。实际融合系统是先平均概率再计算名单，两个顺序不等价。

[根补充：五split真实融合指标](../ensemble-five-split-results.csv) · [同规则方向](../ensemble-five-split-directions.csv) · [融合名单稳定性](../ensemble-five-split-selection-stability.csv) · [补充说明](../ensemble-stability-supplement.md)

该结果后补充对全部13个既有系统评分，canonical26行复现；AE融合全局4胜1平、久单5胜。原seed-mean表与原区间均不覆盖；高度重叠的划分与复用一月不当作5个独立测试月份。

## 可视化与独立读回

本目录10幅PNG/SVG：模型×字段/五split范围、信息配对差、canonical损失/名单条件区间、Brier/AP差、名单Jaccard，以及五种主候选概率的校准/支持图。calibration bin边界来自Octcal概率分位数；每箱Jan人数/事件/Wilson带全部保存，并核100箱范围与计数守恒。主代理已逐批实际查看；全部图清单 [figure-manifest.json](figure-manifest.json)。

[readback-verification.json](readback-verification.json) 给PASS：1040行原定及探索性区间端点重算；从保存种子重建各scope第1/2/10/50/100/250/500/1000/1500/2000号样本，显式展开260组复制客户并与sklearn比较，最大误差1.11e-16。390个根seed均值检查一致；[root-ensemble-supplement-review.json](root-ensemble-supplement-review.json) 再独立核130融合行/260名单配对/130方向行，误差0。

statistics-verification.json是主统计计算时的历史快照，标PLOTS_READBACK_PENDING；后续真实读回由前述PASS及completion-receipt.json承接，不篡改原冻结分析。完整运行输入/代码/输出哈希将由当前最终清单绑定。

没有安装、外发、Git/看板操作；真正未见时间评估、正式模型采用和系统消融均未在本目录宣称完成。
