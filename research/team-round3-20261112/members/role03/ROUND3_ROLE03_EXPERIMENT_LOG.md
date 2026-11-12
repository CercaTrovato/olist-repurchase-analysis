> 原成员交付快照：以下自报状态和历史数字以根目录验收说明为准；课程修正版另列，未覆盖原 ZIP。

# 3号方案实验总表

截至 2026-11-12，本文件汇总3号从 H04 开发到 Round 3 的全部模型、特征、名单规则和分群尝试。除特别注明外，开发比较使用 `2017-10-01` 训练快照和 `2018-01-01` 固定验证快照，Top 10%使用 `K=ceil(0.10*N)`，同分按 `customer_unique_id` 升序。

## 1. H04 初始模型比较

输入为 H02 的8个字段：`R`、`F`、`M`、`average_item_rows`、`freight_share`、`recent30_orders`、`recent30_spend` 和 `state`。数值字段使用 `log1p` 后标准化，类别字段 one-hot。

比较了以下模型及未加权/`balanced`版本：

- 逻辑回归；
- Random Forest；
- CatBoost；
- 最近购买优先和多单优先规则基线。

本节在本文件中保留字段、变换和比较结果摘要；本轮没有重新生成这些旧模型文件。

结论：原始字段 + 加权逻辑回归是当时的主模型；其他学习器没有超过它。

## 2. H04 特征变换尝试

### 2.1 R 分箱

将 `R` 分为 `0–30`、`31–90`、`91–180`、`>180`，分别测试：

- 仅 R 分箱；
- 原始 `R` + R 分箱。

Top 10%结果：逻辑回归分别为44和46 hits，未超过原始连续 `R`。因此不采用 R 分箱。

### 2.2 `is_recent_buyer`

定义为 `R <= 30`，测试加入原始字段的未加权/加权模型。Top 10%结果为42/46 hits，低于原始字段的46/50 hits。因此不加入默认模型。

本文件保留该尝试的字段定义、结果和淘汰理由。

## 3. H04 名单容量和分群分配规则

### 3.1 Top-K容量

对加权逻辑回归比较 Top 5%、10%、15%、20%：

- 5%：31 hits；
- 10%：50 hits；
- 15%：63 hits；
- 20%：74 hits。

结论：容量改变会改变总命中和召回，不属于模型特征改进。

### 3.2 H05 分群后的名单分配

使用 H05 一月客户群标记，只改变预测后的名单分配，不重新训练模型，比较：

- 全局 Top 10%；
- 按群组人数比例分配；
- 群1最低10%、20%、30%名额。

加权逻辑回归全局 Top 10%命中50；按比例分配命中28；群1最低10%、20%、30%分别命中49、44、43。比例配额不采用；群1最低配额只保留为业务侧备选。

本文件保留该尝试的名单规则、结果和淘汰理由；本轮新增群组模型结果见本目录的 `group-model-comparison.csv`。

## 4. H04 最终测试评分

在冻结模型配置下对 `2018-04-01` 最终测试快照评分，没有重新选模或调参：

- 最近购买优先：45 hits；
- 原始逻辑回归：64 hits；
- 加权逻辑回归：65 hits。

本文件保留最终测试的模型、容量和命中结果摘要；本轮不复制该历史逐客户文件。

## 5. Round 3 特征和交叉验证

Round 3 在十月训练快照内部使用5折分层交叉验证；一月作为统一开发验证集比较预先固定的候选方案，不是最终盲测集，也没有根据结果反复改参重跑。

### 5.1 F0 原始字段

- F0：H02 原始字段；
- 未加权逻辑回归；
- `class_weight="balanced"` 加权逻辑回归。

一月 Top 10%分别为46和50 hits。

### 5.2 F1 配送字段

在 F0 上加入：

- `delivered_known_n`；
- `delivery_days_mean`；
- `late_delivery_share`。

一月 Top 10%未加权/加权分别为48/48 hits；没有超过 F0 加权模型。

### 5.3 F2 评价字段

在 F0 上加入：

- `review_known_n`；
- `review_score_mean`；
- `low_review_share`。

一月 Top 10%未加权/加权分别为43/46 hits；没有超过 F0 加权模型。

逐折CV见 [cv-fold-results.csv](cv-fold-results.csv)，汇总见 [cv-summary.csv](cv-summary.csv)，一月容量比较见 [january-comparison.csv](january-comparison.csv)，实现见 [run_round3.py](run_round3.py)。

## 6. Round 3 群标记复算和群组模型

### 6.1 十月群标记

本轮同时保存十月和一月逐客户群标记。3号按 H05-km3-v1 原配置复算十月群标记：

- K-means，`k=3`；
- 仅十月数据拟合 StandardScaler 和聚类；
- `n_init=20`、`max_iter=300`、`tol=1e-4`、`random_state=42`；
- 使用 `R`、`log1p(F)`、`log1p(M)`；
- 输出 `training_clusters.csv`（原交付本地证据，未公开该项）。

复算脚本见 [build_training_clusters.py](build_training_clusters.py)；一月群标记见本目录的 `validation_clusters.csv`。

### 6.2 B：全局模型加入 `cluster_id`

在全局加权逻辑回归中加入 `cluster_id` 类别字段，不拆分训练数据。

- 一月 Top 10%：50 hits；
- AP：0.03063；
- ROC-AUC：0.58579。

与 F0 的50 hits持平，排序指标略高，因此保留为次要候选，不替换 F0。

### 6.3 C：分群模型

- 群0：独立加权逻辑回归；
- 群1：独立加权逻辑回归；
- 群2：使用全局加权逻辑回归兜底；
- 预测后合并分数，再统一全局排序。

一月 Top 10%为49 hits，低于 F0，因此不作为主方案。

群组5折CV和一月结果见 [group-cv-summary.csv](group-cv-summary.csv) 与 [group-model-comparison.csv](group-model-comparison.csv)，实现见 [run_group_models.py](run_group_models.py)。

## 7. 当前保留方案

- **主方案**：F0 原始字段 + 加权逻辑回归 + 全局排序；
- **次要候选**：F0 + `cluster_id` 的全局加权逻辑回归；
- **不采用**：R 分箱、`is_recent_buyer`、配送字段、评价字段、按群组比例配额、群1最低配额作为默认规则、C 分群模型；
- **仍保留为对照**：未加权逻辑回归、Random Forest、CatBoost、最近购买优先、多单优先。

所有 Round 3 逐客户分数和配置见 [README](README.md) 与 [ROUND3_ROLE03_HANDOFF](ROUND3_ROLE03_HANDOFF.md)。
