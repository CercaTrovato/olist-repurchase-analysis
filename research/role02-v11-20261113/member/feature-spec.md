> 成员v1.1交付快照。数值修订已核；其中日期/接收方安排为附件陈述，不自动作为本人新决定。当前验收见根README。

# 2 号第三轮｜新增字段规格（feature-spec）

版本 `R3-role02-feature-v1.1`（候选池与筛选规则的**自报版本声明**时间 2026-11-12 21:35 +0800）。输入 `H02-v2-candidate-reviewed` + 1 号 `round3-role01-time-v1` + 群号 `H05-km3-v1`。

> **版本说明**：`R3-role02-feature-v1.1` 只修了效应区间标准误的分母，并补了 `delivery_days_log` 的下游变换警告；候选公式、筛选阈值、14 项取舍、两组推荐字段与全部点估计/AUC 与 v1 相同。`2026-11-12 21:35 +0800` 是 2 号**自报**的版本声明时间，**不是事前冻结的证明**；团队正式冻结、采用的版本与时间由 6 号按真实记录登记。

> **这一页只写实际跑出来的描述统计。** 本包没有训练模型、没有打分、没有产出名单命中，因此下面所有「差异」都是十月训练侧的描述差异，**不能写成加入模型后的增益**。3 号须在同一批一月客户、2,937 名额与固定久单 79 人下独立检验。

> **区间的性质**：`d_ci_lo/hi` 用 Cohen's d 的大样本近似标准误（分母取**非缺失**正负人数），是描述性近似，**没有多重比较校正**，不是因果作用、不是显著性检验、也不是筛选门槛的输入。

## 1. 口径与分母

| 项 | 值 |
|---|---|
| 训练（本包唯一用于筛选的标签） | 2017-10-01，历史 [2017-04-01,2017-10-01)，标签 [2017-10-01,2017-12-30) |
| 开发验证（只做事后方向核对） | 2018-01-01，历史 [2017-07-01,2018-01-01)，标签 [2018-01-01,2018-04-01)；团队已见 |
| 共同切片 | H05-km3-v1；十月群号来自 1 号 H05 包 `train_audit.local.csv`，一月来自 `validation_clusters.csv` |
| 十月客户 / 复购者 | 21160 / 211（0.9972%） |
| 十月群 C0 | N=11489，正例 114，负例 11375，复购率 0.9923% |
| 十月群 C1 | N=9121，正例 78，负例 9043，复购率 0.8552% |
| 十月群 C2 | N=550，正例 19，负例 531，复购率 3.4545% |
| 主键 | customer_unique_id + snapshot_date；特征、标签、逐人 as-of 表三向零重复零漏配 |
| 预测日截断 | 实际送达、评价答复严格早于快照零点；最终 order_status、快照日及之后的事件一律排除 |

输入核验：`tables/r3_input_checks.csv` 共 34 项，PASS 34 / FAIL 0；从 `orders` / `customers` / `order_items` / `order_reviews` 四张原表独立重算 1 号 7 项 as-of 字段（十月＋一月共 14 项比较），最大绝对差 `0`，NaN 模式差异 0。见 `tables/r3_asof_verification.csv`。

## 2. 候选池与筛选规则（版本声明）

候选池 14 项，全部可由 **1 号 `snapshot-asof-features.csv`（7 列）＋ H02 `F`** 直接算出，公式与来源见 `candidate-definitions.csv`；3 号可用 `scripts/r3_build_candidates.py` 原样重算。阈值在跑最终结果前写入 `scripts/r3_common.py`（带**自报**版本声明时间），未在一月标签上调整；该时间不构成事前冻结或盲测的证明。

| 门槛 | 规则 |
|---|---|
| S1 可用性 | 只保留预测日前已发生事件可算的字段；依赖「预计送达日当时已知且未回写」假设的字段不进推荐组 |
| S2 支持人数 | 每群非缺失 ≥ 80%（分母含全部客户），十月非缺失正例 ≥ 10 且 C0/C1 各 ≥ 3 |
| S3 群内变化 | 三群中至少 2 群 |Cohen's d| ≥ 0.08，且 C0/C1 标准差 > 0 |
| S4 方向＋折内重拟合 | 至少 2/3 群 d 符号与全体一致；5 折分层划分（seed 2026），每折只用另外 4 折拟合中位数填补与标准化后重算 d/AUC，通过率 ≥ 0.80 |
| S5 与原模型不冗余 | 与原八字段数值列的最大 |r| < 0.80 |
| S6 组内不冗余＋小组规模 | 按 |d| 从大到小贪心，组内 |r| ≥ 0.80 的舍弃；每组最多 2 个数值字段 |

**缺失一律显式建模**：有缺失的数值字段保留 NaN 并另加 0/1 缺失指示；填补中位数与标准化参数只在十月拟合（`tables/r3_transform_fit.json`），一月直接套用，不重新拟合。本组无缺失的字段不填、不加指示，具体按第 3 节每个字段的十月缺失人数执行。

**缺失指示不单独参与 S3/S4/S6 的数值字段挑选**：`C04`、`C09` 是随对应数值字段按构造附带的二元指示，用来让「没有观测送达 / 没有已答评价」这一状态不被中位数掩盖；它们不是通过门槛选出来的第三个数值字段，也不占每组最多 2 个数值字段的名额。其未通过的门槛结果与原因如实保留在 `candidate-screening.csv` 与第 4 节：`delivery_days_mean_missing`（S4 未过，折内通过率 40%）；`review_score_mean_missing`（S3 未过，折内通过率 80%）。请勿把这些指示写成「通过了全部筛选」。

## 3. 交付的字段组（最多两组）

### G1_fulfilment（2 个数值字段 + 1 个缺失指示）

| candidate_id | 字段 | 单位 | 公式 | 来源 | 预测日可用时点 | 缺失处理 | 十月支持人数 | 一月支持人数 |
|---|---|---|---|---|---|---|---|---|
| C02 | `delivery_pending_n` | orders | `F - delivered_known_n` | asof.delivered_known_n + H02.F | delivery timestamp strictly < snapshot | 无缺失（十月 21160/21160 非空），无需填补 | 21160 / 21160 (100.00%) | 29368 / 29368 (100.00%) |
| C03 | `delivery_days_log` | log(days) | `log1p(max(delivery_days_mean, 0))` | asof.delivery_days_mean | actual delivery strictly < snapshot; duration from approval | NaN + 0/1 缺失指示 + 十月中位数填补（十月缺失 2029） | 19131 / 21160 (90.41%) | 26355 / 29368 (89.74%) |
| C04 | `delivery_days_mean_missing` | binary | `1{delivery_days_mean is NaN}` | asof.delivery_days_mean | derived from prediction-day truncation only | 无缺失（显式 0/1） | 21160 / 21160 (100.00%) | 29368 / 29368 (100.00%) |

**选择规则（来自脚本，非事后挑最大）**：delivery_pending_n d=+0.170、AUC=0.526、折内通过率 100%、与原八字段最大 |r|=0.475；delivery_days_log d=-0.163、AUC=0.465、折内通过率 80%、与原八字段最大 |r|=0.161

**三群正负样本与分布（十月训练侧，全部人数在 `group-comparison.csv`）**：

- `delivery_pending_n`：C0: 114+/11375 d=+0.144 AUC=0.526 nonmiss=11489/11489; C1: 78+/9043  d=-0.105 AUC=0.491 nonmiss=9121/9121; C2: 19+/531   d=+0.472 AUC=0.621 nonmiss=550/550
- `delivery_days_log`：C0: 114+/11375 d=-0.315 AUC=0.420 nonmiss=9758/11489; C1: 78+/9043  d=-0.058 AUC=0.498 nonmiss=8839/9121; C2: 19+/531   d=+0.113 AUC=0.527 nonmiss=534/550

**预期作用（假设，不是已验证收益）**：「历史订单里已有观测送达 / 仍在途」的订单数与已观测履约时长，描述的是**履约进度**而不是购买规模；两项与原八字段数值列的最大 |r| 分别为 delivery_pending_n=0.475、delivery_days_log=0.161（均低于 S5 的 0.80）。群 1（久单）近 30 天订单全为 0，此点已由 `r3_inputs.py` 逐行核验；该群是否有可用变化须按上面的分群支持人数判断。

### G2_review（2 个数值字段 + 1 个缺失指示）

| candidate_id | 字段 | 单位 | 公式 | 来源 | 预测日可用时点 | 缺失处理 | 十月支持人数 | 一月支持人数 |
|---|---|---|---|---|---|---|---|---|
| C08 | `review_score_mean` | stars 1-5 | `asof.review_score_mean as delivered` | asof.review_score_mean | review answer strictly < snapshot; per-order latest valid answer | NaN + 0/1 缺失指示 + 十月中位数填补（十月缺失 2145） | 19015 / 21160 (89.86%) | 26350 / 29368 (89.72%) |
| C11 | `known_review_ratio` | fraction | `review_known_n / F` | asof.review_known_n + H02.F | review answer strictly < snapshot | 无缺失（十月 21160/21160 非空），无需填补 | 21160 / 21160 (100.00%) | 29368 / 29368 (100.00%) |
| C09 | `review_score_mean_missing` | binary | `1{review_score_mean is NaN}` | asof.review_score_mean | derived from prediction-day truncation only | 无缺失（显式 0/1） | 21160 / 21160 (100.00%) | 29368 / 29368 (100.00%) |

**选择规则（来自脚本，非事后挑最大）**：review_score_mean d=+0.186、AUC=0.545、折内通过率 100%、与原八字段最大 |r|=0.085；known_review_ratio d=-0.129、AUC=0.475、折内通过率 80%、与原八字段最大 |r|=0.582

**三群正负样本与分布（十月训练侧，全部人数在 `group-comparison.csv`）**：

- `review_score_mean`：C0: 114+/11375 d=+0.141 AUC=0.545 nonmiss=9486/11489; C1: 78+/9043  d=+0.219 AUC=0.545 nonmiss=9009/9121; C2: 19+/531   d=+0.278 AUC=0.567 nonmiss=520/550
- `known_review_ratio`：C0: 114+/11375 d=-0.120 AUC=0.477 nonmiss=11489/11489; C1: 78+/9043  d=-0.005 AUC=0.500 nonmiss=9121/9121; C2: 19+/531   d=-0.412 AUC=0.390 nonmiss=550/550

**预期作用（假设，不是已验证收益）**：用已答复评分的均值与按 `F` 归一化的应答覆盖描述历史反馈行为。三群 d 符号与全体一致的候选共 4 项（C07, C08, C10, C11），本组 C08, C11 在其中；两项与原八字段数值列的最大 |r| 分别为 review_score_mean=0.085、known_review_ratio=0.582。`C10_low_review_share` 与 `C08` 的 |r|=0.860，按 S6 组内冗余舍弃，只保留证据。

## 4. 全部候选的处置（保留无效候选）

| id | 字段 | 组 | d(全体) | 折内通过率 | max |r| vs 原八字段 | 结论 | 原因 |
|---|---|---|---:|---:|---:|---|---|
| C01 | `known_delivery_ratio` | G1_fulfilment | -0.110 | 80% | 0.466 | rejected_redundant | \|r\|=0.990 with C02 already retained |
| C02 | `delivery_pending_n` | G1_fulfilment | +0.170 | 100% | 0.475 | retained | retained as numeric field #1 in G1_fulfilment |
| C03 | `delivery_days_log` | G1_fulfilment | -0.163 | 80% | 0.161 | retained | retained as numeric field #2 in G1_fulfilment |
| C04 | `delivery_days_mean_missing` | G1_fulfilment | +0.061 | 40% | 0.459 | attached_missing_indicator | sign match 1/3, fold pass 0.40; attached to C03 |
| C05 | `delivered_known_log` | G1_fulfilment | +0.043 | 20% | 0.434 | rejected_S4 | sign match 2/3, fold pass 0.20 |
| C06 | `delivery_known_any` | G1_fulfilment | -0.061 | 40% | 0.459 | rejected_S4 | sign match 1/3, fold pass 0.40 |
| C07 | `late_delivery_share` | G1_fulfilment | -0.111 | 100% | 0.078 | rejected_S1 | assumption-dependent: conditional: estimated delivery date assumed known at approval and never rewritten |
| C08 | `review_score_mean` | G2_review | +0.186 | 100% | 0.085 | retained | retained as numeric field #1 in G2_review |
| C09 | `review_score_mean_missing` | G2_review | +0.089 | 80% | 0.573 | attached_missing_indicator | clusters \|d\|>=0.08: 1/3, sd(c0,c1)=[0.3794, 0.1101]; attached to C08 |
| C10 | `low_review_share` | G2_review | -0.146 | 100% | 0.093 | rejected_redundant | \|r\|=0.860 with C08 already retained |
| C11 | `known_review_ratio` | G2_review | -0.129 | 80% | 0.582 | retained | retained as numeric field #2 in G2_review |
| C12 | `review_per_delivery` | G2_review | +0.056 | 20% | 0.261 | rejected_S4 | sign match 2/3, fold pass 0.20 |
| C13 | `review_known_any` | G2_review | -0.089 | 80% | 0.573 | rejected_S3 | clusters \|d\|>=0.08: 1/3, sd(c0,c1)=[0.3794, 0.1101] |
| C14 | `review_known_log` | G2_review | +0.016 | 0% | 0.541 | rejected_S3+S4 | clusters \|d\|>=0.08: 1/3, sd(c0,c1)=[0.263, 0.0763]; sign match 0/3, fold pass 0.00 |

## 5. 与本地方案的差别（供 6 号并列比较）

本地字段规格见仓库 `research/round3/data/features/field-dictionary.csv`（公开，本页生成时读到 10 条定义）。本包候选池与筛选阈值在跑筛选前已写入版本声明；`r3_spec.py` **只在生成本页时**读取该文件作对照，没有用它的定义或结果反推候选。下列本地字段均确实存在于该文件：`latest_known_review_score`✓、`known_late_rate`✓、`last_order_late`✓、`known_delivery_days_mean`✓、`latest_known_review_score_missing`✓。

- 本地评价组用「最新一条已答评分」`latest_known_review_score`；本包用**按订单去重后的客户均值** `C08_review_score_mean`，并加按 `F` 归一化的应答覆盖 `C11_known_review_ratio`。
- 本地配送组含 `known_late_rate` / `last_order_late`，两者依赖预计送达日的事前可知且不回写；1 号 `field-time-audit.csv` 把该假设列为待核，本包**把 `C07_late_delivery_share` 明确排除推荐组**，只保留证据。改用不依赖承诺版本的实际送达时长与在途订单数。
- 本地字段用 `known_*_missing` 缺失指示；本包同样显式加指示，但把填补中位数、标准化均值/标准差写成固定参数文件，3 号可在一月直接套用。
- 本包额外要求**每群支持人数、群内标准差、折内重拟合方向一致性**三道门槛，并保留全部 14 项的通过/失败原因。

**本地已公开结果（来自 `docs/team/round-3-results.md`，不是本包跑出来的）**：八字段加权逻辑回归在全局 2,937 名额下，原版命中 50，加配送组 46、加评价组 45、两组都加 46；固定久单 79 人命中分别为 2 / 2 / 1 / 1。即本地那两组**没有改善主容量命中**。本包字段定义与本地不同（见上），所以这些数字**不能**直接当作本包两组的预期效果；本包也没有模型、没有命中数。请 3 号按同一口径重新跑，6 号再并列比较。

## 6. 一月方向核对（事后，不参与选择）

| 字段 | 十月 d | 一月 d | 一月 AUC | 符号一致 | 一月非缺失 |
|---|---:|---:|---:|---|---:|
| `delivery_pending_n` | +0.170 | -0.004 | 0.500 | 否 | 29368 / 29368 |
| `delivery_days_log` | -0.163 | -0.111 | 0.472 | 是 | 26355 / 29368 |
| `delivery_days_mean_missing` | +0.061 | -0.052 | 0.492 | 否 | 29368 / 29368 |
| `review_score_mean` | +0.186 | +0.123 | 0.528 | 是 | 26350 / 29368 |
| `review_score_mean_missing` | +0.089 | +0.063 | 0.510 | 是 | 29368 / 29368 |
| `known_review_ratio` | -0.129 | -0.073 | 0.487 | 是 | 29368 / 29368 |

一月是**已见的开发验证**，标签此前已被查看；这里只报描述方向，既不用于挑选字段，也不构成新时期验证或模型增益。

## 7. 下游怎么用

- **3 号**：按 `candidate-definitions.csv` 的公式或 `scripts/r3_build_candidates.py` 重算；私有逐人表 `candidate_features_train.csv` / `candidate_features_validation.csv` 按 customer_unique_id + snapshot_date 与 H02、H05 群号一一对齐。把两组分别加入原八字段加权逻辑回归，与三条既有对照同口径比较，报 5%/10%/20% 容量、全局 2,937 与固定久单 79；**不要**把本页的 d 当作增益。
- **4 号**：`group-comparison.csv`、`training-feature-evidence.csv` 给三群的正负样本人数、缺失和分布，可用于画像卡；本包没有提出任何品类或内容主题。
- **5 号**：`tables/r3_private_manifest.json` 有逐人表的行数、列名与 SHA-256；`candidate-screening.csv` 有全部候选的门槛结果；可核人数、分母与版本。

> **接入前的硬性警告（v1.1 新增）**：`delivery_days_log` 的定义**已经**是 `log1p(max(delivery_days_mean, 0))`。若下游管道对所有数值列统一再套一次 `log1p`（例如 3 号 `run_round3.py:66` 的 `FunctionTransformer(np.log1p)`），该字段会静默变成 `log1p(log1p(days))`，**定义被偷换、结果不可比**。接入时必须把该列从通用 log 步骤里排除，只对它做填补与标准化。同理 `review_score_mean` 本就是 1–5 星原值，不要当计数取 log。

## 8. 已知缺口与限制

1. H01／最终评价日期、最终标签仍未由 1、3、6 号核定；三期都已见过，本包不声称任何盲测。
2. 预计送达承诺的历史版本、源系统完整性、评分与状态变更日志 1 号仍列待核；因此所有 late 相关字段只留证据不推荐。
3. 十月正例仅 211 人（群 2 只有 19 人），群 2 的 d 与 AUC 波动大，按 S3/S4 只用「至少两群」判定，不对群 2 单独下结论。
4. 十月群号复用 1 号 H05 包内训练侧 `train_audit.local.csv`，本包**没有重新聚类**；其 R/F/M/y 与 H02 在 1e-10 内一致。6 号公开 `october-feature-support.csv` 按 `delivery_known_any` 汇总的群规模为 {0: 11489, 1: 9121, 2: 550}，与本包 {0: 11489, 1: 9121, 2: 550} 一致（已由 `r3_inputs.py` 核对）。
5. 本包没有模型、没有分数、没有名单命中；它只交字段证据与统计图，Slides 片段、英文讲稿与报告要点由 2 号另件交 6 号合稿。描述差异与模型增益必须分开报告。
6. 公开包不含任何逐行客户数据；逐人候选表只在组内私有空间传递。
7. 3 号本轮 F1/F2 用的是 `delivered_known_n` / `delivery_days_mean` / `late_delivery_share` 与 `review_known_n` / `review_score_mean` / `low_review_share`，与本包两组只有 `review_score_mean` 重合，且包含本包按假设未核与组内冗余明确排除的两项；他也没有测过本包的 `delivery_pending_n`、`known_review_ratio` 与缺失指示组合。因此「3 号配送/评价版未改善」**不能**写成本包两组已证实无效。该结论也应限定在 Top 10% 主指标：5% 与 20% 容量下 3 号部分候选高于 F0。

## 9. 复跑

```bash
cd outputs/Round3_role02/scripts
python run_all.py --smoke     # 5,000 行小样例
python run_all.py             # 全量：inputs -> candidates -> evidence -> plots -> spec -> verify
```

输入路径可用 `R3_H02_DIR` / `R3_ROLE01_DIR` / `R3_H05_DIR` / `R3_RAW_DIR` 覆盖。全部图的来源表、行数、窗口、单位、分母、命令与哈希见 `chart-index.csv`（8 幅）。
