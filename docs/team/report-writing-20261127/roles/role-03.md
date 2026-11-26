# 3号 · SUN Bo · 预测方法、参数和初始模型比较

按既有六岗能力和贡献拟定本轮写作安排；待本人发群、成员回报承接与时间。没有将未回报的认领、写稿或检查标成完成。

先读[统一规则](../WRITING-RULES.md)、[六章结构](../STRUCTURE.md)和[交件模板](../DELIVERY-TEMPLATE.md)。英文草稿用Word/Markdown即可，无需LaTeX；图表、公式和引用需可编辑及可追源。

## 写哪些子节

- IV-A Common pipeline and predictive models
- V-A Baseline and group-feature model comparisons

初稿文字预算：约850–1100英文词。预算用于控制整体23页，不为凑字重复内容。

## 具体交付

1. 写共同输入、训练内拟合的填补/编码/缩放、类别权重、分数排序与并列规则。
2. 写7个初筛配置：最近购买规则＋LR/RF/CatBoost各普通/加权版本；之后R3与分群配置按registry身份区分。
3. 解释实际参数、开发选择和对照，列全必要比较，不把不同80/20扩展混进主模型表。F0/G1/G2新字段结果由2号主写，配合核配置定义。

## 图表候选

- F02 初始筛选图（候选）
- T-R3-01 主要模型与实际参数表
- T-R3-02 同容量初筛/分群输入比较

候选F01–F10是现有素材ID，不是最终Figure编号，正式采用与编号由合稿统一。

## 直接证据入口

- [data/experiment-registry.csv](../../../../report-prep/20261126/data/experiment-registry.csv)
- [data/model-parameters.csv](../../../../report-prep/20261126/data/model-parameters.csv)
- [data/h04-screening.csv](../../../../report-prep/20261126/data/h04-screening.csv)
- [data/r3-group-methods.csv](../../../../report-prep/20261126/data/r3-group-methods.csv)
- [cv-and-uncertainty.md](../../../../report-prep/20261126/cv-and-uncertainty.md)

## 引用与交叉核对

- cox1958（引用前核勘误）
- breiman2001
- friedman2001（仅提升家族）
- hegarcia2009
- CatBoost与scikit-learn官方文档（软件来源）

与5号核训练/开发/后期分工，和4号核固定群映射条件；保留历史实际one-hot与扩展native输入的差别。

内部首稿建议11/30 22:00 HKT，待组内确认；先交给6号完整素材包和未决问题。以本轮规则/当前修补包执行，旧岗位卡的11月实验交件节点保留历史。
