> 原成员交付快照：以下自报状态和历史数字以根目录验收说明为准；课程修正版另列，未覆盖原 ZIP。

# 第三轮 2 号｜运行日志（真实标准输出）

> 本文件记录最终复跑的真实 stdout / stderr，数字与结论均来自实跑，未手工改写。
> 环境：Windows / Python 3.13.12 / pandas + numpy + matplotlib（无 scipy、无 sklearn）；
> 工作目录 `outputs/Round3_role02/scripts`；记录时间 2026-11-12 22:37 +0800。

## 运行历史与采信说明

1. **第一次全量复跑**：`r3_verify.py` 在干净环境首次运行时，对自身产物 `SELF_CHECK.md`
   报了 1 项**假 FAIL** —— 脚本先做「必需文件是否存在」检查，后才创建占位文件。
   这是脚本顺序缺陷，不是数据或结论问题。原始输出完整保留在第 1 节。
2. **修复 1**：`r3_verify.py` 改为在「present」检查之前先创建 `SELF_CHECK.md` 占位；
   最终定稿仍按 H03 的做法「先写定 SELF_CHECK.md 最终字节，再哈希整包」。
3. **修复 2（图表可读性）**：逐张目视检查 8 幅图，发现 `05-support-and-missing` 与
   `07-october-january-direction` 的图注与旋转后的 x 轴刻字相撞；调整 `r3_plots.py` 的
   `bottom` 边距与刻字角度后整包重跑。图表内容、数据、窗口、分母与结论均未改动。
4. **修复 3（规格文案）**：`r3_spec.py` 原先对全部数值字段写同一句「NaN + 指示 + 填补」，
   但 `delivery_pending_n` / `known_review_ratio` 十月零缺失；改为按实际缺失人数生成，
   并补充说明两个缺失指示是按构造附带、不单独过 S3/S4、不占每组 2 个数值字段名额。
5. **最终全量复跑（第 2 节，采信）**：smoke 输入检查 27/27 PASS、full 输入检查 34/34 PASS、
   1 号 as-of 独立复算 14 项全 PASS、自检 **49 项 0 FAIL**、96 个文件哈希 96/96 回验通过。
6. 本日志写定后，会再单独执行一次 `r3_verify.py`，刷新 `SELF_CHECK.md` 与
   `CHECKSUMS.sha256`，使清单里 `RUN_LOG.md` 的哈希对应最终字节。

---

## 1. 第一次全量复跑（含失败，原始输出，不采信结论）

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
[r3_verify] 49 checks, 1 FAIL; wrote SELF_CHECK.md and CHECKSUMS.sha256 (96 files, 96/96 re-verified)
                 check status                                                                                                         detail
present: SELF_CHECK.md   FAIL MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\SELF_CHECK.md
Traceback (most recent call last):
  File "MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\scripts\run_all.py", line 57, in <module>
    main()
    ~~~~^^
  File "MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\scripts\run_all.py", line 52, in main
    run(stage, smoke)
    ~~~^^^^^^^^^^^^^^
  File "MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\scripts\run_all.py", line 41, in run
    subprocess.run(cmd, cwd=HERE, check=True)
    ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "MEMBER_HOME/.workbuddy-ai\binaries\python\versions\3.13.12\Lib\subprocess.py", line 577, in run
    raise CalledProcessError(retcode, process.args,
                             output=stdout, stderr=stderr)
subprocess.CalledProcessError: Command '['MEMBER_HOME/.workbuddy-ai\\binaries\\python\\versions\\3.13.12\\python.exe', 'MEMBER_HOME/WorkBuddy AI\\2026-11-08-15-56-13\\olist-repurchase-analysis\\outputs\\Round3_role02\\scripts\\r3_verify.py']' returned non-zero exit status 1.
```

---

## 2. 最终全量复跑（采信）

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
