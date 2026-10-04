# 3分钟 Briefing 英文讲稿与中文翻译

对应 [最新版PPT](olist-repurchase-briefing.pptx)，共5页。英文约329词，按适度停顿、指图与换页安排约3分钟；实际时长需本人排练。只朗读英文，中文用于理解。不要读成已经完成全部研究的结果报告。

## 第1页：Business Problem（约30秒）

**English**

Our main question is who is likely to buy again within ninety days. Prediction alone does not explain what different customers are like. We therefore add customer segmentation and group-level exploration. Clustering has two roles: it may help improve predictive features, and it provides customer insights for differentiated business recommendations. We will evaluate both roles rather than assuming clustering must improve the model.

**中文翻译**

我们的核心问题是，哪些客户更可能在未来90天内再次购买。单独做预测，无法解释不同客户是什么样的人。因此，我们加入客户分群和组内探索。聚类有两个作用：它可能帮助改进预测特征，也能为差异化商业建议提供客户洞察。我们会分别评价这两种贡献，而不是预先假定聚类一定能改善模型。

## 第2页：Dataset Description（约30秒）

**English**

We use the orders, order items and customers tables. We aggregate item amounts to each order, then connect orders to unique buyers. This produces customer snapshots at defined dates. Product metadata can support category profiles. IDs are categorical, money is numeric, and timestamps define what information was available. The displayed counts describe raw tables, not the final modelling sample.

**中文翻译**

我们使用订单、商品明细和客户三张表。先将商品明细金额汇总到每笔订单，再将订单关联到唯一买家，形成指定日期的客户快照。商品资料可以辅助分析品类画像。编号属于类别信息，金额是数值，时间戳帮助界定当时可用的信息。页面显示的是原始表的行数，不是最终建模样本量。

## 第3页：Key Variables and Target（约35秒）

**English**

At each analysis date, we use six months of historical activity to predict an approved, positive-value order in the next ninety days. Candidate inputs include RFM, order size, recent activity and region. Earlier snapshots support development; a later period is reserved for final evaluation. Group-level findings suggest candidate features, but we only keep changes supported by validation. All inputs must be available at the prediction date.

**中文翻译**

在每个分析时点，我们使用此前六个月的历史活动，预测未来90天内是否再次出现已批准且商品金额为正的订单。候选输入包括RFM、订单规模、近期活动和地区。较早的快照用于开发，较晚时期保留作最终评价。组内发现可以启发候选特征，但只有获得验证支持的改动才会保留。所有输入必须在预测时点已经可知。

## 第4页：BDA Methods／流程图（约50秒）

**English**

The workflow starts with overall exploration and feature engineering. We then run two parallel paths. The main path compares classification models. The supporting path clusters the full eligible customer population and explores each group separately. Group findings suggest feature changes, which return to the prediction pipeline and are checked on validation data. They also produce business insights in their own right. After development is frozen, we evaluate predictions on a later held-out period and combine both outputs.

**中文翻译**

流程从整体探索和特征工程开始，然后分成两条并行路径。主线比较分类模型；辅助线对全部符合条件的客户分群，再分别探索各群体。组内发现会提出特征调整建议，反馈到预测流程，并通过验证数据检查。同时，这些发现本身也产生业务洞察。在开发方案固定后，我们使用较晚的留出时期评价预测，再综合两条路径的结果。

**指图提示**：先指上方整体EDA和特征工程，再指左侧分类主线；转到右侧聚类与组内EDA，指出右边返回特征工程的箭头；最后指两侧下方输出。强调“两个贡献”，不要把右边只讲成模型调参。

## 第5页：Potential Contribution（约35秒）

**English**

The final report will deliver more than a prediction tool. It will show how well repurchase can be predicted, describe the different customer groups, and connect both to business recommendations. Clustering may remain valuable even if it adds little predictive improvement, provided its profiles are stable and decision-relevant. Recommendations are hypotheses for future experiments: predicting a purchase does not show that marketing caused it.

**中文翻译**

最终报告将提供不止一个预测工具。它会说明复购能够被预测到什么程度，描述不同客户群体，并把两者结合成商业建议。即使聚类对预测改善不大，只要画像稳定且与决策相关，它仍可能有价值。建议属于未来实验的假设：预测到一次购买，并不代表营销促成了这次购买。

## 常见追问，简短回答

- **聚类是只做高复购客户吗？** 不是，覆盖全部符合历史资格的客户类型；模型拟合仍限制在开发数据，测试客户用冻结规则分配。
- **每个群分别训练分类器吗？** 当前主方案不是；组内EDA帮助提出特征改进，并独立提供画像。
- **能保证聚类提高预测吗？** 不能，要比较初版和修改版；没有提升也需要如实记录。
- **为什么不用准确率？** 复购极少，全猜不复购也有很高准确率；我们看AP、ROC-AUC及固定名单比例的精确率和召回率。
- **已经证明营销有效吗？** 没有，缺少干预实验。我们提出的是有证据的行动假设和后续验证建议。

学校模板与校徽权利保留，见 [许可说明](../LICENSES.md)。
