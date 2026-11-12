> 原成员交付快照：以下自报状态和历史数字以根目录验收说明为准；课程修正版另列，未覆盖原 ZIP。

# [R3] 2 号 → 1、3、4、5、6 号｜第三轮交接单

| 项 | 内容 |
|---|---|
| 版本 | `R3-role02-feature-v1`（候选池与阈值冻结于 `2026-11-12 21:35 +0800`） |
| 状态 | **本地自检完成，待成员本人核验；尚未发送，无接收方回执** |
| 主送 | 3 号（直接重算字段、跑同口径对照）；5 号（核人数/分母/版本）；6 号（并列比较与采用决定） |
| 抄送 | 1 号（as-of 字段回执与时点假设）；4 号（群画像补充） |
| 输入版本 | `H02-v2-candidate-reviewed` + 1 号 `round3-role01-time-v1` + `H05-km3-v1` |
| 训练 / 开发验证 | 2017-10-01（唯一用于筛选）/ 2018-01-01（已见，仅事后方向核对） |
| 公开包 | `outputs/Round3_role02/`（聚合表 + 图 + 文档 + 脚本，无逐行客户数据） |
| 私有表 | `private_outputs/Round3_role02/candidate_features_train.csv`（21,160 行）、`candidate_features_validation.csv`（29,368 行），仅走组内私有空间 |
| 时间说明 | 本包生成于 **11/12 21:35，晚于 21:00 展示方法冻结时点**；若 6 号已锁版本，本包只作补充候选，不替换已锁方法，也不改写任何已登记结果 |

---

## 1. 交付文件与用途

| 文件 | 给谁 | 用途 |
|---|---|---|
| `feature-spec.md` / `feature-spec.json` / `candidate-definitions.csv` | 3 号 | 两组字段的公式、来源列、预测日可用时点、缺失处理、支持人数、选择规则、预期作用；`json` 可直接读 |
| `scripts/r3_build_candidates.py` | 3 号 | 按 `candidate-definitions.csv` 原样重算 14 项候选；输出按键对齐的私有逐人表 |
| `tables/r3_transform_fit.json` | 3 号 | 只在十月拟合的填补中位数、标准化均值/标准差；一月直接套用，**不要重新拟合** |
| `training-feature-evidence.csv` / `group-comparison.csv` | 3、4、5 号 | 三群正负样本人数、非缺失、Cohen's d / AUC / 95% CI、分布分箱 |
| `candidate-screening.csv` | 3、5、6 号 | 14 项候选逐项 S1–S6 门槛与舍弃原因（保留无效候选） |
| `field-correlation.csv` | 3、6 号 | 候选与原八字段、候选彼此的 Pearson r |
| `tables/r3_fold_selection.csv` | 5、6 号 | 5 折分层、每折内重拟合填补/标准化后的 d 与 AUC、通过率 |
| `tables/r3_january_direction.csv` | 5、6 号 | 一月事后方向；`used_for_selection=False` 全列 |
| `figures/` + `chart-data/` + `chart-index.csv` | 4、5、6 号 | 8 幅 PNG+SVG，每图含窗口、单位、N、分母、来源表行数、命令与哈希 |
| `tables/r3_input_checks.csv` / `r3_asof_verification.csv` | 1、5 号 | 34 项输入核验；从 4 张原表独立复算 1 号 7 项 as-of 字段 |
| `tables/r3_private_manifest.json` | 5 号 | 私有逐人表行数、列名、SHA-256（不公开逐行数据） |
| `ROLE01_RECEIPT.md` | 1 号 | 对 `round3-role01-time-v1` 的暂收回执与待核假设 |
| `GROUP_MESSAGE.md` | 2 号本人 | 「收到及预计交付时间」即时回复 + 提交后群内说明 |

## 2. 核过什么（脚本实跑，不是人工估计）

- **输入指纹**：12 个 SHA-256 全部匹配（H02 特征/标签/coverage、H04 v0.4、H05 包、三个 zip、4 张原表）；1 号包内 `CHECKSUMS.sha256` 以 CRLF 兼容方式逐项比对，0 处不符。
- **键与版本**：88,341 行；特征/标签/as-of 三向主键零重复、零漏配；`feature_version` 与 `data_version` 全部一致；标签域 `{0,1}`。
- **群号**：十月 21,160 人全覆盖、一月 29,368 人全覆盖；一月群计数 `{0:16335,1:12330,2:703}`；H05 `train_audit.local.csv` 的 R/F/M/y 与 H02 在 1e-10 内一致；十月群规模与 6 号公开 `october-feature-support.csv` 一致；久单群 `recent30_orders` 逐行确认为全 0。
- **预测日截断独立复算**：从 `orders` / `customers` / `order_items` / `order_reviews` 四张原表按 1 号 `field-time-audit.csv` 定义独立实现（未导入 1 号脚本），对十月＋一月共 **14 项比较，最大绝对差 0，NaN 模式差异 0**；实际送达、评价答复均严格早于快照。
- **筛选纪律**：阈值在跑最终结果前写入 `scripts/r3_common.py`；**只用十月标签**挑选，5 折每折内重新拟合中位数填补与标准化；一月只作事后描述，`used_for_selection=False`。
- **自检**：`SELF_CHECK.md` 由 `r3_verify.py` 生成，逐项核文件、版本、人数、两组上限、图哈希、私有表哈希、公开包无客户键；`CHECKSUMS.sha256` 为 LF 行尾，可 `sha256sum -c`。
- **小样例**：`python run_all.py --smoke` 先跑 5,000 行，输出留在 `smoke/`。

## 3. 实跑结论（描述统计，不是模型增益）

- 十月 N=21,160、正例 211（0.9972%）；C0 11,489/114（0.9923%）、C1 9,121/78（0.8552%）、C2 550/19（3.4545%）。
- 两组字段与十月支持人数：
  - `G1_fulfilment`：`delivery_pending_n` 21,160/21,160；`delivery_days_log` 19,131/21,160（90.41%）；`delivery_days_mean_missing` 21,160/21,160。
  - `G2_review`：`review_score_mean` 19,015/21,160（89.86%）；`known_review_ratio` 21,160/21,160；`review_score_mean_missing` 21,160/21,160。
  - 一月对应 29,368 分母下分别为 29,368 / 26,355 / 29,368 与 26,350 / 29,368 / 29,368。
- 缺失处理按字段实际缺失人数执行：`delivery_days_log`（十月缺 2,029）、`review_score_mean`（缺 2,145）留 NaN + 0/1 指示 + 十月中位数填补；另 4 个数值/指示字段十月零缺失，不填补。填补/标准化参数只在十月拟合。两个缺失指示按构造附带，不占每组 2 个数值字段名额，也未单独通过 S3/S4，其完整门槛结果保留在 `candidate-screening.csv`。
- `C07_late_delivery_share` 被 S1 排除（预计送达日「事前已知且未回写」假设未核）；`C01`、`C10` 因组内 |r| ≥ 0.80 冗余舍弃；其余舍弃原因逐项见 `candidate-screening.csv`。
- 一月方向：6 个保留字段中 4 个符号一致；`delivery_pending_n`（+0.170 → −0.004）与 `delivery_days_mean_missing`（+0.061 → −0.052）翻转。这提示**不要把十月描述差异当成稳定增益**。
- 本地已公开结果（`docs/team/round-3-results.md`，非本包产出）：全局 2,937 名额原版 50、加配送 46、加评价 45、两组都加 46；固定久单 79 命中 2/2/1/1。本包字段定义不同，这些数字**不能**当作本包预期效果。

## 4. 请各接收方做什么

- **3 号**：按 `candidate-definitions.csv` 或 `r3_build_candidates.py` 重算；用固定参数文件；两组分别加入原八字段加权逻辑回归，与三条既有对照同口径，报 5%/10%/20%（1,469 / 2,937 / 5,874）、全局 2,937 与固定久单 79；分数降序、同分按匿名客户键升序。**不要把本包 d / AUC 写成增益**。
- **4 号**：`group-comparison.csv`、`training-feature-evidence.csv` 可用于三群画像卡；本包没有提出品类或内容主题。
- **5 号**：核 21,160 / 29,368 / 三群人数、分母、版本、`tables/r3_private_manifest.json` 的哈希与 `candidate-screening.csv` 的门槛结果。
- **6 号**：把本包两组定义与本地两组并列；注意生成时点已过 21:00 冻结，采用与否请按真实登记决定。
- **1 号**：见 `ROLE01_RECEIPT.md`；预计送达承诺的历史版本、源系统完整性、评分/状态变更日志仍待核。

## 5. 回执

请接收方回复 **「已验收」** 或 **「还缺什么」**（写明缺哪一项、哪个文件、哪一行）。
收到回执前，本包状态保持「尚未发送，无接收方回执」；若 H02 或 1 号 as-of 定义变更，本包需整体复跑并升版本号。

---

### 可直接复制的群内索引

```
[R3] 2号 → 1、3、4、5、6号 | R3-role02-feature-v1 | 待验收
公开包 outputs/Round3_role02/；逐人候选表只走组内私有空间。
① 十月 21,160 人 / 211 正例；三群 11,489-114 / 9,121-78 / 550-19。
② 交 2 组字段：G1_fulfilment（delivery_pending_n、delivery_days_log + 缺失指示）；
   G2_review（review_score_mean、known_review_ratio + 缺失指示）。14 项候选全部留证据。
③ 输入检查 34/34 PASS；从 4 张原表独立复算 1号 7 项 as-of 字段，14 项比较 max diff 0。
④ 只用十月标签筛选，5 折每折内重拟合；一月只作事后方向核对，6 个保留字段中 2 个符号翻转。
⑤ 主动披露：C07 late_delivery_share 因预计送达日假设未核被排除；本包晚于 11/12 21:00 冻结时点；
   本地已公开的 50/46/45/46 不是本包结果；本包没有模型、分数或名单命中。
请 3号重算并跑同口径对照，4号取画像数据，5号核人数与哈希，6号决定采用。
回「已验收」或「还缺什么」。
```
