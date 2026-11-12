> 原成员交付快照：以下自报状态和历史数字以根目录验收说明为准；课程修正版另列，未覆盖原 ZIP。

# Round 3 role 03 prediction

## 当前状态

Round 3 已完成探索并冻结方案。完整历史尝试、结果和淘汰理由见 [ROUND3_ROLE03_EXPERIMENT_LOG.md](ROUND3_ROLE03_EXPERIMENT_LOG.md)；交接只看 [ROUND3_ROLE03_HANDOFF.md](ROUND3_ROLE03_HANDOFF.md)。

**主方案**：F0 原始 H02 特征 + `class_weight="balanced"` 逻辑回归 + 全局排序。

## 统一评价口径

- 训练快照：`2017-10-01`；
- 固定验证快照：`2018-01-01`；
- 5折分层交叉验证只在十月训练快照内部进行；
- 一月标签用于一次统一的开发验证和候选比较；各次运行前固定候选配置，不根据结果反复改参重跑；
- 排名按分数降序，同分按 `customer_unique_id` 升序；
- 报告 Top 5%、10%、20%；
- 数值字段沿用 `log1p`，缺失填补、标准化和类别编码在训练数据内拟合。

## 当前结果

一月 Top 10%：

- F0 全局加权逻辑回归：50 hits，主方案；
- B 全局模型加入 `cluster_id`：50 hits，AP/ROC-AUC略高，次要候选；
- C 群0/群1独立模型、群2全局兜底：49 hits，不采用。

配送字段、评价字段、R分箱、最近购买附加字段和群组配额均未超过主方案。旧模型、规则和最终测试结果的完整记录见实验总表。

## 输出索引

### 基础模型与验证

- `run_round3.py`：F0/F1/F2及加权/未加权逻辑回归；
- `cv-fold-results.csv`、`cv-summary.csv`：基础模型5折CV；
- `january-predictions.csv`、`january-comparison.csv`：一月逐客户分数和容量结果。

### 群组模型

- `run_group_models.py`：B/C群组方案；
- `group-cv-fold-results.csv`、`group-cv-summary.csv`：群组方案5折CV；
- `group-model-predictions.csv`、`group-model-comparison.csv`：群组方案逐客户分数、容量和逐群结果；
- `group-model-metadata.json`：群组方案配置。

### 群标记与复跑

- `build_training_clusters.py`：复算十月群标记；
- `training_clusters.csv`、`validation_clusters.csv`：两期逐客户群标记；
- `run-metadata.json`：基础实验配置；
- `ROUND3_ROLE03_EXPERIMENT_LOG.md`：全部探索记录；
- `ROUND3_ROLE03_HANDOFF.md`：简洁交接结论。

## 复跑

在项目环境中运行：

```powershell
python run_round3.py
python build_training_clusters.py
python run_group_models.py
```

脚本使用项目现有 H02 和时点特征输入；群组模型使用本目录保存的两期群标记。
