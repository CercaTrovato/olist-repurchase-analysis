# P2 预先冻结的全字段与地区对照

冻结于运行本批一月模型结果前。训练 2017-10-01；已见开发验证 2018-01-01；仅通过既有 read_dev 读取 H02 前 50528 行，禁止解析 April 快照。

候选全部保留，不按 January 挑字段或参数：

1. lr8：原 8 字段，未加权 LR。
2. lr8-geo：原 8 字段 + 买卖家州、城市、邮编的末单类别及历史地区/公里距离摘要。
3. full-structure：H02 全部 11 个非标识原字段 + 所有合法历史结构摘要，包括商品、篮子、支付、服务、卖家上下文和地区。
4. structure-text：上述结构 + 截止日前已答评价 title/message 文本；TFIDF max_features=2000，min_df=5，训练侧拟合词表。
5. structure-catboost：与 full-structure 相同的原始结构字段；depth=3, iterations=300, learning_rate=.03, l2_leaf_reg=10, random_seed=2026，无类别权重。

LR 固定 C=1, max_iter=2000, solver=lbfgs，无类别权重。数值训练侧 median 填补、每列固定缺失指示、非负数 log1p、StandardScaler；负值/坐标按原值缩放。类别训练侧 OHE(handle_unknown=infrequent_if_exist,min_frequency=20)。五候选同 y、同键同时间窗口；原 8 基线也用相同预处理。实际历史旧分数因本次明确统一预处理可能不逐位相同。

原始 9 表 52 字段逐个记录位置、处理状态及派生去向；key 仅连接，最终订单状态 unknown_at_t，英文分类翻译 redundant。商品/卖家 ID 不直接独热，转截止日前历史 frequency；customer/order ID 只连接。product/seller/customer 地区维度缺更改日志，payments/预计日期/发货截止缺回写日志，单列 assumption；不声称严格可恢复生产时点。实际承运/送达日期及评价答复必须发生在 t 前。评价文本仅已答且创建<=答复、答复>=审批的合法历史记录。

Geo 先 exact 去重，再按邮编聚合 median lat/lng，Haversine 地球半径 6371.0088 km；报告缺失与无法连接，不将邮编当数值距离。客户保留所有 H02 键，6 个月审批>=start 且<t 且金额>0 的历史；F/M 独立重算核对。

评价自然分布 Log loss / Brier / AP / AUC、0.5 混淆和 precision/recall/F1、全局 K=2937、5%/20% 容量（ceil），共同久单 H05-km3-v1 cluster_id=1（Jan 12330 人 / 90 正例）的固定 79 仅诊断。排序分数降序再 customer_unique_id 升序稳定打破并列。一月已见，不称未见最终测试。

共同切片纠正记录：最初本文误写 cluster=2（703/28），执行也沿用了错误切片。主代理提供权威共同定义后，按原 H05 validation_clusters.csv 逐键核对并修正为 cluster_id=1；仅更正已固定容量诊断，不重训、不据模型分数选切片，错误切片记录保留 private/long-slice-mismatch。

下游复用 private 对齐的完整原始特征表和 feature-views.json；y、cluster、score、split、data_version 不列入 X。训练拟合变换另存。全部结果及失败保留，不自动采用模型。
