> 原成员交付快照：以下自报状态和历史数字以根目录验收说明为准；课程修正版另列，未覆盖原 ZIP。

# 第三轮 2 号交付包｜新增字段规格与十月群内证据

版本 `R3-role02-feature-v1`；候选池与筛选阈值冻结于 `2026-11-12 21:35 +0800`。
状态：**本地自检完成，待成员本人核验；尚未发送，无接收方回执。**

输入版本：`H02-v2-candidate-reviewed` + 1 号 `round3-role01-time-v1` + 群号 `H05-km3-v1`。

---

## 1. 第三轮 2 号应该交什么

按 `docs/team/round-3/role-02.md` 和 `docs/team/round-3/README.md`：用**十月**数据，在 H05 三个群里找能区分复购者与未复购者、且**预测日已经可算**的信息；三群都给正负样本人数、缺失和分布；最多两个小字段组，每组写字段名、公式、来源、可用时点、缺失处理、支持人数、选择规则和预期作用；筛选用标签时只用训练侧，交叉验证每折内重新拟合；把描述差异与加入模型后的增益分开；交 `feature-spec.md`、`training-feature-evidence.csv`、两期按键对齐的私有候选表、分布对照图及脚本，供 3 号直接重算、4/5 号复核人数与版本。

## 2. 本包实际交付

| 交付项 | 文件 |
|---|---|
| 字段规格（两组、公式、来源、时点、缺失、支持人数、选择规则、预期作用、限制） | `feature-spec.md`、`feature-spec.json`、`candidate-definitions.csv` |
| 14 项候选的完整门槛结果（含被舍弃者与原因） | `candidate-screening.csv`、`tables/r3_retained_fields.csv` |
| 三群正负样本人数、缺失、分布与效应量 | `group-comparison.csv`、`training-feature-evidence.csv`、`tables/r3_distribution_bins.csv` |
| 支持人数、相关性、折内重拟合、一月事后方向 | `tables/r3_candidate_support.csv`、`field-correlation.csv`、`tables/r3_fold_selection.csv`、`tables/r3_january_direction.csv` |
| 输入核验与 1 号 as-of 字段独立复算 | `tables/r3_input_checks.csv`、`tables/r3_asof_verification.csv`、`tables/r3_environment.json` |
| 8 幅统计图（PNG + 可编辑 SVG + 每图聚合数据 + 逐图哈希/窗口/单位/N/分母/命令） | `figures/`、`chart-data/`、`chart-index.csv` |
| 训练侧填补/标准化固定参数 | `tables/r3_transform_fit.json` |
| 两期按键对齐的**私有**逐人候选表（不在公开包内） | `private_outputs/Round3_role02/candidate_features_{train,validation}.csv`；公开侧只给 `tables/r3_private_manifest.json`（行数、列名、SHA-256） |
| 可复跑脚本、小样例、运行日志、自检、哈希 | `scripts/`、`smoke/`、`RUN_LOG.md`、`SELF_CHECK.md`、`CHECKSUMS.sha256` |
| 交接与群内消息 | `HANDOFF.md`、`ROLE01_RECEIPT.md`、`GROUP_MESSAGE.md`、`tables/HANDOFF_SUMMARY.md` |

**结论摘要**（全部来自本次实跑，详见 `tables/HANDOFF_SUMMARY.md`）：

- 十月 N=21,160、正例 211；三群 C0 11,489/114、C1 9,121/78、C2 550/19。
- 输入检查 34/34 PASS；从 4 张原表独立重算 1 号 7 项 as-of 字段（十月＋一月共 14 项比较），最大绝对差 **0**，NaN 模式差异 0。
- 14 项候选，交付 **2 组 / 4 个数值字段 + 2 个缺失指示**：
  - `G1_fulfilment`：`delivery_pending_n`、`delivery_days_log` + `delivery_days_mean_missing`
  - `G2_review`：`review_score_mean`、`known_review_ratio` + `review_score_mean_missing`
- `C07_late_delivery_share` 因依赖「预计送达日当时已知且未回写」的未核假设，被 S1 排除，只保留证据。
- 一月方向核对：6 个保留字段中 4 个符号一致，`delivery_pending_n` 与 `delivery_days_mean_missing` **符号翻转**；一月是已见开发验证，只作事后描述，不参与选择。

## 3. 目录结构

```
Round3_role02/
├── README.md  HANDOFF.md  ROLE01_RECEIPT.md  GROUP_MESSAGE.md
├── feature-spec.md  feature-spec.json  candidate-definitions.csv
├── candidate-screening.csv  training-feature-evidence.csv
├── group-comparison.csv  field-correlation.csv  chart-index.csv
├── RUN_LOG.md  SELF_CHECK.md  CHECKSUMS.sha256
├── figures/       8 PNG + 8 SVG
├── chart-data/    每图对应的聚合数据 CSV
├── tables/        输入核验、支持人数、折内、方向、参数、私有清单、交接数字块
├── scripts/       r3_common.py + 6 个阶段脚本 + run_all.py
└── smoke/         5,000 行小样例的等量输出（表 + 图 + chart-index）
```

## 4. 隐私边界

公开包只含**聚合表、图、文档、脚本**，不含任何 `customer_unique_id`。逐人候选表写在
`private_outputs/Round3_role02/`（仓库之外的私有目录），只在组内私有空间传递；
公开侧 `tables/r3_private_manifest.json` 只放行数、列名与 SHA-256，供 5 号核对。

## 5. 复跑

```bash
cd outputs/Round3_role02/scripts
python run_all.py --smoke     # 5,000 行小样例：inputs -> candidates -> evidence -> plots
python run_all.py             # 全量：inputs -> candidates -> evidence -> plots -> spec -> verify
```

每个阶段在独立子进程中运行，任一阶段非零退出即中止。输入路径可用
`R3_H02_DIR` / `R3_ROLE01_DIR` / `R3_H05_DIR` / `R3_RAW_DIR` / `R3_PRIVATE_IN` /
`R3_PRIVATE_OUT` 覆盖；预期 SHA-256 写在 `scripts/r3_common.py`。

环境只用 `pandas` / `numpy` / `matplotlib` 与标准库；本机无 `scipy`、无 `sklearn`，
AUC 用秩次实现（`r3_common.auc`），**本包不训练模型、不打分、不产名单命中**。

## 6. 明确未做 / 不能写成结论的东西

1. 没有模型、没有分数、没有 5%/10%/20% 命中数；`feature-spec.md` 里的 d / AUC 是**十月训练侧描述差异**，不是加入模型后的增益。
2. 一月标签只用于事后方向核对；H01／最终评价日期、最终标签仍未由 1、3、6 号核定，三期都已见过，本包不声称盲测。
3. 没有重新聚类；十月群号复用 1 号 H05 包 `train_audit.local.csv`，其 R/F/M/y 与 H02 在 1e-10 内一致。
4. 没有 Slides、英文讲稿、报告要点、内容主题或品类建议；这些属 4/5/6 号与合稿阶段。
5. 本包生成于 11/12 21:35，**晚于 21:00 展示方法冻结时点**；若 6 号已锁版本，本包只作补充候选，不替换已锁方法。详见 `HANDOFF.md`。
6. 1 号 `field-time-audit.csv` 中预计送达承诺的历史版本、源系统完整性、评分与状态变更日志仍列待核，因此所有 late 相关字段只留证据、不进推荐组。
