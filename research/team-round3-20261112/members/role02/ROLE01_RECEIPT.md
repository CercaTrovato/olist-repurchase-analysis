> 原成员交付快照：以下自报状态和历史数字以根目录验收说明为准；课程修正版另列，未覆盖原 ZIP。

# 2 号 → 1 号｜`round3-role01-time-v1` 暂收回执

| 项 | 内容 |
|---|---|
| 收件 | 1 号；抄送 3、5、6 号 |
| 收到包 | `Round3_role01_time_v1(1).zip`（本工作区解包至 `private_inputs/Round3_role01_time_v1/`） |
| 基线 | `H02-v2-candidate-reviewed`；本包版本 `round3-role01-time-v1` |
| 主文件 | `snapshot-asof-features.csv`（88,341 行 × 11 列，私有逐人表） |
| 状态 | **暂收，可用**：结构、键、版本、预测日截断均通过独立复算；下列假设仍待 1 号确认，未获答复前不写成「已验收」 |

---

## 1. 已核过的内容（实跑）

- 包内 `CHECKSUMS.sha256` 用 CRLF 兼容方式逐项比对，**0 处不符**；`snapshot-asof-features.csv` SHA-256 与 `input-versions.csv` 登记值 `549f0502…0628` 一致。
- 88,341 行；`customer_unique_id + snapshot_date` 零重复，与 H02 `snapshot_features.csv`、`snapshot_labels.csv` **三向 1:1 零漏配**；三期快照齐全。
- `feature_version` 全为 `round3-role01-time-v1`，`data_version` 全为 `H02-v2-candidate-reviewed`；`data-version.json` 记载 `label_differences = 0`。
- **独立复算**：不导入 1 号 `build_audit.py`，另按 `field-time-audit.csv` 定义从 `orders` / `customers` / `order_items` / `order_reviews` 四张原表重算 7 项 as-of 字段；十月 21,160 人、一月 29,368 人各 7 项，共 **14 项比较，最大绝对差 0，NaN 模式差异 0**（`tables/r3_asof_verification.csv`）。
  - 复算中已严格断言：计入的实际送达时间 `< 快照`；计入的评价答复时间 `< 快照`；按订单取最新有效答复的答复时间也 `< 快照`。
  - 商品金额先按 `order_id` 汇总、再按 `customer_id` 接客户、最后按 `customer_unique_id` 聚合，未用 item 行直接连表。
- 缺失规模与 1 号 `field-missingness.csv` 一致：十月 `delivery_days_mean` 缺 2,029 / 21,160、`review_score_mean` 缺 2,145 / 21,160；一月分别缺 3,013 / 29,368 与 3,018 / 29,368。本包按「已知事件缺失」处理，**不删客户**，全部留在分母并加 0/1 指示。

## 2. 本包据此采用的口径

- 只使用**可用 / 预测日已发生**的 6 列（`delivered_known_n`、`delivery_days_mean`、`review_known_n`、`review_score_mean`、`low_review_share`，以及派生的覆盖比），配合 H02 `F`。
- `delivery_promise_known_n` 与 `late_delivery_share` 只作候选证据（本包 `C07`），**不进推荐字段组**。
- 最终 `order_status`、快照日及之后的送达/答复、评价创建时间/文本一律排除。
- 两期填补中位数与标准化参数只在十月拟合（`tables/r3_transform_fit.json`），一月直接套用。

## 3. 待 1 号确认 / 暂不验收的点

1. **预计送达承诺的历史版本**：`field-time-audit.csv` 已注明「预计日期假设在批准时已知且未被事后回写」「预计字段可知性无版本日志证明」「假设待核」。在拿到版本日志或明确结论前，所有 late 相关字段只留证据。
2. **源系统完整性与变更日志**：评分、状态、评价文本的变更记录未提供；`review_creation_date` 不足以证明答复已发生。本包只用 `review_answer_timestamp` 截断，未使用创建时间或文本。
3. **`order_delivered_carrier_date` 未发布**、尾部月份覆盖稀疏（1 号 `source-tail-monthly.csv` / `time-window-audit.csv`）：本包不据此提出任何新快照或盲测主张。
4. 二期/三期都已见过，H01／最终评价日期与最终标签仍未由 1、3、6 号核定；本包不声称盲测。

## 4. 给 1 号的回执行（可直接粘进 `receipt-log.csv`）

```
round3-role01-time-v1,2号,暂收可用,88,341行×11列,三向键1:1零漏配,7项as-of字段独立复算14项比较maxdiff=0,待核预计送达承诺版本与源系统变更日志
```

请回复 **「已验收」** 或 **「还缺什么」**。若 1 号修订 `snapshot-asof-features.csv` 或 as-of 定义，本包会整体复跑 `run_all.py` 并升版本号，旧版结果作废。
