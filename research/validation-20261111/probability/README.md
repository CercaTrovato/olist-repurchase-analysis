# P1：概率、分类与名单策略的验证结果

本轮验证完成：既有 17 方法完整保留，另加 4 个显式概率对照，总计 21 方法；其中 15 个有可解释的概率输出。Oct 21,160 人／211 个正例训练，Jan 29,368 人／230 个正例全量评分。April 快照／标签解析 0 行。结果是已见一月上的开发验证，不是新增盲测，未自动改变最终采用方法。

## 最有用的发现

加权 LR 的原分数有排序能力，但不能直接解释成自然复购概率。其 Jan 平均输出 47.17%，真实复购率只有 0.7832%。解析先验修正或 Oct OOF Platt 能纠正主要的概率尺度错误；这不增加信息，也不会改变 weightedLR 的排序和 TopK 命中。未加权 LR 的概率质量仍更好，Platt 不是自动胜出。

| 方法 | 全体 Logloss ↓ | 全体 Brier ↓ | AP ↑ | AUC ↑ | Top10% 命中 |
|---|---:|---:|---:|---:|---:|
| Oct 常数基率 | 0.046032 | 0.00777490 | 0.007832 | 0.5000 | 仅固定键打破同分，不解读为模型能力 |
| 未加权 LR3 | 0.044976 | 0.00770666 | 0.032458 | 0.5608 | 51 |
| 未加权 LR8 | 0.045072 | 0.00771366 | 0.028239 | 0.5778 | 46 |
| weightedLR 原分数 | 0.660372 | 0.23446377 | 0.029797 | 0.5820 | 50 |
| weightedLR 解析先验修正 | 0.045410 | 0.00771376 | 0.029797 | 0.5820 | 50 |
| weightedLR OOF Platt | 0.045711 | 0.00776620 | 0.029797 | 0.5820 | 50 |
| CB14-unweighted | 0.045135 | 0.00772248 | 0.025959 | 0.5875 | 50 |

Logloss 衡量是否把实际发生／未发生事件的概率押对，过度自信押错会受重罚；Brier 是概率与真实 0／1 的平方误差。AP／AUC 衡量排序，TopK 衡量给定联系容量下的名单效果，三者不能相互替代。完整 balanced LR、context、CatBoost 负结果均保留在 `january-metrics-all-scopes.csv`。

全体 LR3 和 LR8 相对 Oct 常数的 Logloss 差分别为 -0.001056（95% 条件 bootstrap 区间 [-0.001734, -0.000435]）和 -0.000960（[-0.001694, -0.000298]）。LR3 相对 LR8 的差为 -0.000096，区间跨 0，不能据此认定 LR3 稳定优于 LR8。Platt 相对 LR8 的 Logloss 差为 +0.000640，区间 [0.000159, 0.001158]；本轮 Platt 明确没有胜过未加权 LR8。

## 单单／久单的信息质疑

Jan 的 F=1 客户 28,665 人／202 个正例，久单群 12,330 人／90 个正例。只拿全局 Oct 常数比较，会把群间基率差也算成模型收益。因此额外用 Oct 同切片基率作为更公平的无信息参照，Jan 基率常数仅列理论诊断下限，不能当可部署预测器。

久单 Oct 同切片基率为 78/9121=0.8552%。相对它，LR3 的 Logloss 差为 -0.000128（95% CI [-0.000327, 0.000079]），LR8 为 +0.000002（[-0.000383, 0.000409]），CB14-unweighted 为 -0.000144（[-0.000379, 0.000136]），均不足以确认可靠增量收益。全部单单 F=1 上，LR3／LR8／CB14-unweighted 的同类区间也跨 0；Platt 比同切片常数更差，差 +0.000186（[0.000021, 0.000354]）。

可支持的结论是：当前特征和这些候选在单单／久单中尚未证明可靠的增量概率价值。不能把这个有限负结果扩展成“单单绝无信息”或“任何模型都不可能学到”；部分候选 AUC 略高于 0.5，但这不是 stable proper loss 收益的充分证据。久单固定 79 人策略仍保留 LR3=2、LR8=1、weightedLR=2、CB14-unweighted=3 命中，名单事件稀少也限制判断。

## 为什么 99.2% Accuracy 仍可能没有识别能力

对全体人都预测“不复购”，Accuracy 就是 99.2168%，但 F1=0、MCC=0。未加权 LR3／LR8 和已校准模型在 0.5 阈值下恰好也是全负类；因此 Accuracy 单独不能比较本题模型。

Oct OOF 选择 maxF1 阈值后固定用于 Jan，LR3 Accuracy=97.9433%、F1=0.07077、MCC=0.06413；LR8 为 97.5722%、0.06307、0.05752。weightedLR 原分数及其单调校准后的固定阈值对应相同分类结果，F1=0.05895。阈值是 Oct 内部开发选择，Jan 没有参与选阈值；这不是最优一月阈值承诺。

## 校准实现与证据边界

Oct 3 折 StratifiedKFold(shuffle=True, random_state=20261111)，每折预处理只在本折训练数据拟合。保留原模型配置，Jan 使用原全 Oct 拟合的存档模型，重载评分逐人复现。先验修正使用训练负／正数比，full-Oct offset=4.597988；它依赖“权重主要改变先验”的近似，不保证模型误设或正则化下自动校准。

Platt 用自然比例 Oct OOF logit 拟合单变量无类别权重 LR，C=1e6，系数 0.263739、截距 -4.554349。它是经验校准；`october-oof-development-metrics.csv` 中 Platt 的校准器也使用这些 OOF 标签，所以这一列是开发读数，不能当嵌套无偏 CV。Jan 完全未用于 fit 校准器。

校准图边界由 Oct 决定：新 LR 系列用 Oct OOF，既有其他模型只用全 Oct 模型的训练分数定边界，不将训练拟合度当评估。每个方法／群域 10 bins，共 600 bins；重复边界导致的空 bin 保留，外端延伸到无穷以接住所有 Jan 客户。`calibration-all-bins.csv` 展示全部 bin 的 N／events、预测均值、实际事件率与 Wilson 区间；计数和事件已逐组守恒核验。`figures/calibration-support-*.png/.svg` 直接展示 LR8、weightedLR raw／prior／Platt 的所有 bin 分母和事件数。完整坐标图与局部放大图分开保存。

所有 bootstrap 为每群域 2,000 次配对客户重采样，模型／分数固定，不重新训练。它度量当前已见一月及固定模型的条件不确定性，不能涵盖重训、时间漂移、团队探索及候选选择的不确定性。区间未做多重比较校正，不据此宣称最终采用。

## 文件与接续 schema

- `private/january-all-scores.csv`：29,368 行，键 `customer_unique_id,snapshot_date`，附 `cluster_id,y` 与 21 个 `score_<method>`。
- `private/october-oof-scores.csv`：21,160 行，键与标签／群，`fold=0/1/2`，6 个 LR／校准／常数系列 `score_<method>`。常数列为共同 Oct 基率基准，不解释为独立 CV 学习成绩。
- `private/lr-probability-predictors.joblib`：3 个原全 Oct pipeline、Platt、先验 offset、常数、Oct OOF 固定阈值和特征名。`predict_lr_suite.py` 可重评分，不调用 fit。六分数重放 Jan 最大绝对差均为 0；每折模型也独立保存。
- `method-schema.csv`：完整 17 个既有方法与 4 个新增对照及分数类型。原 `recency/simpleMulti`、3 个 rank blends 不算概率；`group-shrink100` 原值为 logit，另列显式 sigmoid 变换，避免把 logit／百分位偷当概率。
- `january-metrics-all-scopes.csv`：84 行，全体／三个群的 21 方法 AP/AUC，15 个概率方法另有 proper metrics。
- `january-threshold-classification.csv`、`thresholds-october.csv`：固定 0.5 和可用 Oct OOF maxF1 阈值／Accuracy/F1/MCC／混淆矩阵。
- `strategy-top10-long79.csv`：原名单策略单独呈现；`no-information-and-single-order.csv` 和 `information-support.csv`：无信息／F=1 参照。
- `bootstrap-loss-differences.csv`：关键候选相对常数／LR8／W(raw) 的 loss 差；`bootstrap-vs-scoped-no-information.csv`：同群／单单常数更严格的补充对照。
- `all-pr-roc-curves.csv`：所有阈值、所有方法、四个域，约 189 MB；`all-pr-roc-curves.csv.gz` 是已验证相同 SHA256 解压内容的紧凑副本，交接或提交优先用 gzip，避免将两份都纳入仓库。
- `verification.json` 是核心运行回执，`supplement-verification.json` 是单单补充和预测器回放，`final-verification.json` 汇总最终文件哈希、25 个输入未变和 600 bins 守恒。主／补充计划哈希分别记录，保留实际冻结时点。

复现依次运行 `run_probability.py` → `no_information_diagnostics.py` → `finalize_probability.py`，使用 `D:\anaconda3\python.exe -B -X utf8`。核心执行实测约 20.7 秒；本目录没有 Git／看板／外部写入，未安装软件、未修改原件。Q01／Q03／Q12 的既有事实继续承接：全量客户输入、容量仅是输出策略；加权／阈值／校准为不同动作；一月已见而 April 本轮不读。其他质疑由主任务统一归档，不越权宣布全部关闭。
