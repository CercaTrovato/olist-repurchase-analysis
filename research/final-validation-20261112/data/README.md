# 冻结滚动数据

发布副本说明：文中冻结 SHA 指本地原始字节；公开文本经 LF 规范及链接重定位，其当前字节 SHA 以顶层 [public-evidence-manifest.json](../public-evidence-manifest.json) 为准，不代表数据重算。

`data-manifest.json` 已冻结为 `READY`。冻结计划 SHA-256 为 `c6d0ff58feed195bc4db1a803813faaedebb4fd7902874168d4139faeb24c1f4`；manifest SHA-256 为 `0f7f16aed6f01b0b3d2ed83bf14f2eaf739cea88c393418449419b23b6bf37f6`。

私有行表在 `private/snapshots/{日期}.csv` 和 `private/cells/{评价日}__{single|pooled}/{fit,cal,eval}.csv`。列为双键、冻结 141 字段及 `y/future_gmv/future_orders/label_end/cluster`。读取双键与 8 个类别字段须指定 pandas `dtype='string'`，以保留邮编前导零。所有 ID、日期、未来标签和群均不进入模型输入。

未来金额只加总历史 cohort 客户在 `[预测日,预测日+90天)` 内批准的正商品额订单，不含运费；未来次数计不同订单。7 日期均逐键满足 `y == (future_gmv > 0) == (future_orders > 0)`。独立使用原始订单、客户、商品明细三表重算，各日期金额最大绝对误差均为 0；次数和标签全部一致。Jan 目标区间在 `2018-04-01` 之前结束，不构造四月快照、标签或评分。

| 快照 | 客户 | 正例客户 | 匹配未来订单 | 未来商品额 |
|---|---:|---:|---:|---:|
| 2017-07-01 | 14,012 | 120 | 129 | 19,109.81 |
| 2017-08-01 | 17,105 | 141 | 158 | 21,121.37 |
| 2017-09-01 | 19,609 | 186 | 207 | 25,497.98 |
| 2017-10-01 | 21,160 | 211 | 230 | 27,727.82 |
| 2017-11-01 | 23,260 | 232 | 250 | 30,116.25 |
| 2017-12-01 | 26,848 | 239 | 261 | 33,109.11 |
| 2018-01-01 | 29,368 | 230 | 248 | 30,478.29 |

July 是从固定 2017-01-01 观察起点取得六自然月历史的最早允许日期，没有按成绩挑窗口。Nov/Dec/Jan 训练快照分别限 Jul–Aug、Jul–Sep、Jul–Oct。最新成熟快照按双键排序，以 `seed=20261111` 分层拆 80% fit / 20% cal；pooled 在所有旧快照也剔除 T-cal 的每一位客户。6 cell 的 fit/cal 客户交集均为 0，全部训练及校准标签在评价日前成熟。Jan single 的 fit/cal 客户哈希分别为 `037940a31f4faca2a82b84c59e72a890ff021cfbde14a9bd443973121ff028b9` 和 `30dab0b367932e7b3bf346c69565dc57320ee9b8023a824b6c1840adc9375681`，与旧 shared split20261111 逐键复现。

旧 H05 的数值中心与原 Oct 缩放尺度在 `private/frozen-group-model.json`。使用相同变换、固定语义中心和尺度计算最近中心，未重新拟合 KMeans、未选择 K 或按评价标签改映射。Oct 21,160 键与 Jan 29,368 键均与旧标签全部一致；Nov/Dec 只做同一冻结模型的外推诊断。群不入 X。

`cell-support.csv` 区分行、唯一客户、正例行、唯一正例客户和重复目标订单。例如 Jan pooled 是 59,954 个预测机会、21,864 位客户，547 个正例行、329 位正例客户；600 个目标订单机会仅对应 365 个唯一订单，235 次为跨快照重复。每行等权不等于新增独立样本。窗口本身已用于开发；不称独立盲测。

核验入口：`historical-feature-reproduction.csv`（July/Oct/Jan 对旧源 141 字段与 y 全部零不匹配）、`all-field-roundtrip.csv`（全部写后回读）、`independent-readback.json`（独立原始三表标签及六 cell 检查）、`date-construction-audit.json`（日期化原函数审计）、`sourcehash.json`（源码与原始文件来源）、`outputhash.json`（输出哈希）。日/月覆盖和跨快照客户、订单、日历重叠均已量化；有每日事件不证明摄取完整，静态属性与付款等字段的历史可得性仍依赖既有无变更日志假设。

原 P2 `load()` 返回的原始来源审计含其旧代码硬编码的 `snapshot_rows_read=50528`；这是承接函数的旧标记，不是本批实际读取计数。本批未读取 H02 CSV 成员，仅读 notebook JSON。实际行数以 manifest 顶层 `snapshots/cells` 为准，澄清见 `metadata-addendum.json`；冻结 manifest 和数据未因此更改。

复现顺序是 `run_data.py` → `verify_data.py` → `finalize_data.py`。仅选择并执行已审 H02/P2/context/service 的函数，原脚本 main 和四月评分分支均不执行。没有训练预测模型。所有 `private/` 数据、未来标签及模型数值参数保持私有；公开仅采用经主代理核准的支持数、日期、覆盖、哈希和源码白名单。
