> 原成员交付快照：以下自报状态和历史数字以根目录验收说明为准；课程修正版另列，未覆盖原 ZIP。

# 交接数字块（由 r3_spec.py 生成，勿手改）

- 十月 N=21160，正例 211；三群 114+11375/11489 / 78+9043/9121 / 19+531/550
- 输入检查 34/34 PASS，1 号 as-of 独立复算 14 项，max abs diff 0，NaN 模式差异 0
- 候选池 14 项，通过并交付 4 个数值字段 + 2 个缺失指示，分 2 组：G1_fulfilment = delivery_pending_n, delivery_days_log; G2_review = review_score_mean, known_review_ratio
- 图 8 幅（PNG+SVG），逐图数据与哈希见 chart-index.csv
- 私有逐人表：candidate_features_train.csv 21160行 sha256=251ea2bc3c3a2f2f…; candidate_features_validation.csv 29368行 sha256=4fa0f74bbb7b5076…
