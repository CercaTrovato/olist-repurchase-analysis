> 原成员交付快照：以下自报状态和历史数字以根目录验收说明为准；课程修正版另列，未覆盖原 ZIP。

# 第三轮 2 号交付前自检

由 `scripts/r3_verify.py` 生成。49 项检查，PASS 49，FAIL 0。

| 检查 | 结果 | 说明 |
|---|---|---|
| present: README.md | PASS | MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\README.md |
| present: HANDOFF.md | PASS | MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\HANDOFF.md |
| present: ROLE01_RECEIPT.md | PASS | MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\ROLE01_RECEIPT.md |
| present: GROUP_MESSAGE.md | PASS | MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\GROUP_MESSAGE.md |
| present: feature-spec.md | PASS | MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\feature-spec.md |
| present: feature-spec.json | PASS | MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\feature-spec.json |
| present: candidate-definitions.csv | PASS | MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\candidate-definitions.csv |
| present: candidate-screening.csv | PASS | MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\candidate-screening.csv |
| present: training-feature-evidence.csv | PASS | MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\training-feature-evidence.csv |
| present: group-comparison.csv | PASS | MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\group-comparison.csv |
| present: field-correlation.csv | PASS | MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\field-correlation.csv |
| present: chart-index.csv | PASS | MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\chart-index.csv |
| present: SELF_CHECK.md | PASS | MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\SELF_CHECK.md |
| present: RUN_LOG.md | PASS | MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\RUN_LOG.md |
| present: tables/HANDOFF_SUMMARY.md | PASS | MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\tables\HANDOFF_SUMMARY.md |
| present: tables/r3_input_checks.csv | PASS | MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\tables\r3_input_checks.csv |
| present: tables/r3_asof_verification.csv | PASS | MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\tables\r3_asof_verification.csv |
| present: tables/r3_candidate_support.csv | PASS | MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\tables\r3_candidate_support.csv |
| present: tables/r3_fold_selection.csv | PASS | MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\tables\r3_fold_selection.csv |
| present: tables/r3_january_direction.csv | PASS | MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\tables\r3_january_direction.csv |
| present: tables/r3_distribution_bins.csv | PASS | MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\tables\r3_distribution_bins.csv |
| present: tables/r3_retained_fields.csv | PASS | MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\tables\r3_retained_fields.csv |
| present: tables/r3_transform_fit.json | PASS | MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\tables\r3_transform_fit.json |
| present: tables/r3_private_manifest.json | PASS | MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\tables\r3_private_manifest.json |
| present: tables/r3_environment.json | PASS | MEMBER_HOME/WorkBuddy AI\2026-11-08-15-56-13\olist-repurchase-analysis\outputs\Round3_role02\tables\r3_environment.json |
| input checks all PASS | PASS | 34/34 PASS |
| independent as-of recomputation all PASS | PASS | 14/14 PASS, max_abs_diff=0.0 |
| October cohort N and positives | PASS | N=21160 pos=211 |
| three clusters reported | PASS | [0, 1, 2] |
| at most two field groups | PASS | ['G1_fulfilment', 'G2_review'] |
| each group has <=2 numeric fields | PASS | {'G1_fulfilment': 2, 'G2_review': 2} |
| all 14 candidates retained as evidence | PASS | 14 |
| no late/promise-dependent field retained | PASS | [] |
| rejected candidates have reasons | PASS | {'rejected_S4': 3, 'rejected_redundant': 2, 'rejected_S1': 1, 'rejected_S3': 1, 'rejected_S3+S4': 1} |
| evidence table has all candidates x 4 scopes | PASS | 56 |
| January direction not used for selection | PASS | 6 rows, used_for_selection={False} |
| no row-level customer key in public CSVs | PASS | [] |
| private tables are outside the public bundle | PASS |  |
| private candidate table hashes match manifest | PASS | {'candidate_features_train.csv': {'exists': True, 'rows': 21160, 'hash_ok': True}, 'candidate_features_validation.csv': {'exists': True, 'rows': 29368, 'hash_ok': True}} |
| all figure hashes match chart-index | PASS | 8 figures, 16 hash checks OK, bad=[] |
| chart-data files present and non-empty | PASS | 8 files |
| feature-spec mentions H02-v2-candidate-reviewed | PASS |  |
| feature-spec mentions round3-role01-time-v1 | PASS |  |
| feature-spec mentions H05-km3-v1 | PASS |  |
| feature-spec mentions R3-role02-feature-v1 | PASS |  |
| feature-spec mentions 不 | PASS |  |
| feature-spec mentions 2,937 | PASS |  |
| feature-spec mentions 79 | PASS |  |
| handoff summary has real numbers | PASS |  |

哈希清单 `CHECKSUMS.sha256` 含 96 个文件（LF 行尾，可 `sha256sum -c`）。
本自检只核文件、版本、人数、哈希与隐私边界；**不核模型增益**，本包未运行模型。
