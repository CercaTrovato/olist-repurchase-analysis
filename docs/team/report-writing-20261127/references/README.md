# 可核的期刊候选文献池

10篇条目均通过Crossref精确DOI读取，类型为journal-article；另查出版者来源，记录题名、期刊、年份、页码、支持范围及注意事项。这里验证存在性与书目信息，没有逐篇全文认证。每位作者仍要读实际支持的段落并交位置；不要求10篇全引用。

- [CSV元数据与适用范围](verified-journals.csv)
- [JSON完整核验记录](verified-journals.json)
- [BibTeX条目](verified-journals.bib)

Cox1958原文的出版者页面提示1959勘误，DOI https://doi.org/10.1111/j.2517-6161.1959.tb00334.x ，引用细节前需读勘误。Wilson用1927原期刊年份。Van Calster2019是临床预测背景下的期刊Opinion/方法讨论，仅用于校准概念，不拿它证明电商收益。Friedman2001支持梯度提升家族，不冒称CatBoost原始期刊论文。McNemar原文是配对比例方法基础，当前exact binomial的实现另核实际脚本/软件。

软件/数据原始来源可使用下列官方入口，按实际版本/访问日期登记；它们不是期刊论文：

- Olist数据：https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
- scikit-learn校准：https://scikit-learn.org/stable/modules/calibration.html （文档当前版本不倒填为旧训练环境）
- CatBoost参数：https://catboost.ai/docs/en/concepts/parameter-tuning （当前建议不改写历史已跑的编码/参数）
- 本项目实际结果：[11/26修补包](../../../../report-prep/20261126/README.md)

期刊文献引用其DOI/publisher页，正式期刊文章即使在别处有预印本，也使用已发表版本的元数据和链接。不用arXiv入口替代正式发表来源。
