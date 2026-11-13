> 成员v1.1交付快照。数值修订已核；其中日期/接收方安排为附件陈述，不自动作为本人新决定。当前验收见根README。

# 第三轮 2 号｜运行日志（v1.1，真实标准输出）

> 记录时间 2026-11-13 21:41 +0800。环境：Windows / Python 3.13.12 / pandas 3.1.1 + numpy + matplotlib
> （无 scipy、无 sklearn；AUC 用秩次实现）。工作目录 `outputs/Round3_role02/scripts`。
> v1 的完整运行日志（含首次自检顺序缺陷与两次修复）保留在
> `Round3-role02-feature-v1_2026-11-12.zip` 内，不被本文件覆盖。

## v1.1 改了什么、没改什么

- **改**：`r3_evidence.py` 的 `d_se` 分母由全组 `n1/n0` 改为**非缺失**正负人数
  （影响 `C03/C07/C08/C10/C12` × 4 scope = 20 行区间）；`r3_common.py` 的 C03 备注与
  `r3_spec.py` 生成的规格补「已 log1p、禁止下游重复 log」；补「区间无多重比较校正」、
  「3 号 F1/F2 不能外推到本包两组」；「冻结」措辞改为自报版本声明；`SPEC_VERSION` 升 `v1.1`。
- **没改**：14 项候选公式、S1–S6 阈值、筛选结果、两组推荐字段、全部点估计/AUC、
  一月方向、支持人数、私有逐人表的字段数值。没有训练模型、没有分数、没有名单命中。
- **独立对照 v1**：20 行区间全部变化，点估计与 AUC 变化 0，"是否跨零"分类变化 0；
  两张私有表除 `spec_version` 列外逐格相同。例 C03 全体 se 0.06919 → 0.07349，
  CI `[-0.2986,-0.0273]` → `[-0.3070,-0.0189]`。
- 环境备注：11/13 19:47 装 `pyarrow 26.0.1` 时曾缺 `__init__.py` 导致 `import pandas` 失败，
  20:53 已补齐；本次复跑使用恢复后的环境。

## 最终复跑（采信）

```
### command: python run_all.py --smoke
=== Round3 role-02 pipeline: SMOKE (4 stages) ===

$ MEMBER_HOME/.workbuddy-ai\binaries\python\versions\3.13.12\python.exe MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\scripts\r3_inputs.py --smoke
[r3_inputs] smoke=True checks=27 PASS=27 FAIL=0

$ MEMBER_HOME/.workbuddy-ai\binaries\python\versions\3.13.12\python.exe MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\scripts\r3_build_candidates.py --smoke
[r3_build_candidates] smoke=True private_tables=1 candidates=14 -> MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\private_outputs\Round3_role02\smoke

$ MEMBER_HOME/.workbuddy-ai\binaries\python\versions\3.13.12\python.exe MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\scripts\r3_evidence.py --smoke
[r3_evidence] smoke=True rows=5000 candidates=14 retained=5 groups=['G1_fulfilment', 'G2_review']
candidate_id                      field         group                   decision
         C02         delivery_pending_n G1_fulfilment                   retained
         C04 delivery_days_mean_missing G1_fulfilment attached_missing_indicator
         C08          review_score_mean     G2_review                   retained
         C09  review_score_mean_missing     G2_review attached_missing_indicator
         C12        review_per_delivery     G2_review                   retained

$ MEMBER_HOME/.workbuddy-ai\binaries\python\versions\3.13.12\python.exe MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\scripts\r3_plots.py --smoke
[r3_plots] smoke=True figures=8 -> MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\smoke\chart-index.csv

=== pipeline finished: SMOKE ===

### command: python run_all.py
=== Round3 role-02 pipeline: FULL (6 stages) ===

$ MEMBER_HOME/.workbuddy-ai\binaries\python\versions\3.13.12\python.exe MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\scripts\r3_inputs.py
[r3_inputs] smoke=False checks=34 PASS=34 FAIL=0

$ MEMBER_HOME/.workbuddy-ai\binaries\python\versions\3.13.12\python.exe MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\scripts\r3_build_candidates.py
[r3_build_candidates] smoke=False private_tables=2 candidates=14 -> MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\private_outputs\Round3_role02

$ MEMBER_HOME/.workbuddy-ai\binaries\python\versions\3.13.12\python.exe MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\scripts\r3_evidence.py
[r3_evidence] smoke=False rows=21160 candidates=14 retained=6 groups=['G1_fulfilment', 'G2_review']
candidate_id                      field         group                   decision
         C02         delivery_pending_n G1_fulfilment                   retained
         C03          delivery_days_log G1_fulfilment                   retained
         C04 delivery_days_mean_missing G1_fulfilment attached_missing_indicator
         C08          review_score_mean     G2_review                   retained
         C09  review_score_mean_missing     G2_review attached_missing_indicator
         C11         known_review_ratio     G2_review                   retained

$ MEMBER_HOME/.workbuddy-ai\binaries\python\versions\3.13.12\python.exe MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\scripts\r3_plots.py
[r3_plots] smoke=False figures=8 -> MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\chart-index.csv

$ MEMBER_HOME/.workbuddy-ai\binaries\python\versions\3.13.12\python.exe MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\scripts\r3_spec.py
[r3_spec] wrote feature-spec.md / feature-spec.json / candidate-definitions.csv (2 groups, 4 numeric fields)

$ MEMBER_HOME/.workbuddy-ai\binaries\python\versions\3.13.12\python.exe MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\scripts\r3_verify.py
[r3_verify] 49 checks, 0 FAIL; wrote SELF_CHECK.md and CHECKSUMS.sha256 (96 files, 96/96 re-verified)

=== pipeline finished: FULL ===
```

> 本日志写定后再单独执行一次 `r3_verify.py`，刷新 `SELF_CHECK.md` 与 `CHECKSUMS.sha256`，
> 使清单中 `RUN_LOG.md` 的哈希对应最终字节（与 H03 / v1 相同做法）。
