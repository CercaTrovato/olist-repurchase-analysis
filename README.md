# Olist 复购预测与客户价值

IS6400 小组项目｜Six Sigma

业务主线已经补齐：**给全部合资格老客户预测未来 90 天复购概率，再按历史价值或预计商品金额打分，由经理按实际能力选择关注人数。** 全量输入和预测覆盖所有客户，10%只是可比名单容量；现在并列1/2/5/10/20/50/100%，不是只预测10%。

2026-11-12最终固定研究已收尾：7快照、3滚动评价期、30概率位置（25新+5旧复用）、6条件金额模型、18全量经理私表及20项质疑结案。主原式p×F×M和预计金额各15/18组合比概率排序覆盖更多商品额，但大多数条件区间含0，目标间有取舍，没有统一稳定赢家。经理私表及未来答案保持私有。

[最终白话说明与完整研究](docs/team/final-research-closeout.md) · [价值与经理使用](docs/team/final-value-guide.md) · [本批6图](docs/team/final-validation-figures.md) · [累计72图](docs/team/visual-assets.md) · [Q01–Q20结案](docs/team/research-questions.md)

[当前团队事项](docs/team/current-status.md) · [时间线](TIMELINE.md) · [个人助手入口](ASSISTANT-README.md)

计算完成不替小组正式选模型、改目标或提交。仍按真实回件记录H04措辞修正、正式采用版本与H07收稿；不再把已完成消融或滚动验证列为下一轮待跑。真正未见未来、利润与触达增量缺少相应数据，不能从本回测证明。

## 真实团队记录与此前结果

以下保留团队交接和旧回测历史；最新本地研究以上述最终入口为准。

**一月加权模型和按群复核已对齐。** 同样取 2,937 人，最近购买优先命中 30 人，原逻辑回归 46 人，加权逻辑回归 50 人。加权后久单群入选从 17 到 79，命中从 0 到 2。当前主方案候选是原八字段加权逻辑回归、全局前 10%。四月三份名单已复现，45／64／65按已见窗口回测记录。交接说明和正式采用版本仍待收尾。

[小组最新进度](docs/team/current-status.md) · [本地探索与对照](docs/team/local-exploration.md) · [汇总表与图](docs/team/evidence/README.md) · [各岗入口](docs/team/README.md)

**第三轮已发群。** 6 号已确认业务取舍和展示采用截止。本地六基线、新增信息、时间审计与内容试验设计已完成，当时两批共18幅图；当前全部主素材72幅，见最新图表索引。组员按同目标独立设计策略，本人已确认发群，成员新回件待核。

[第三轮成员任务](docs/team/round-3/README.md) · [本地结果](docs/team/round-3-results.md) · [后续11候选](docs/team/round-3-extension.md) · [PPT／报告图表素材](docs/team/visual-assets.md)

## 顺着读就能接上

1. [项目在解决什么问题](docs/01-project-explained.md)。用同一个运营场景理解候选名单、分群和特征反馈。
2. [订单怎样变成一行客户数据](docs/02-data-guide.md)。认清订单、商品明细和跨单买家编号，再看如何汇总。
3. [训练、验证和按群核数怎么做](docs/03-methodology.md)。包括每期日期、排序口径和已经看过的四月窗口。
4. [回到自己的岗位](docs/team/README.md)。按 [交接协议](docs/team/protocol.md) 核版本、文件和验收条件。遇到术语可以查 [速查表](docs/04-glossary.md)。

**组内拟定节点**为 11 月 12 日 21:00 冻结方法、13 日 21:00 收各岗 Slides 和英文讲稿、14 日合稿与排练。Canvas 的正式截止为 **11 月 15 日 23:59（Slides）**、**12 月 6 日 23:59（报告）**，均为香港时间。Six Sigma 的课堂场次待核，尚未核到 Canvas 提交回执。[完整倒排](docs/07-team-guide.md#倒排计划)

## 复现与历史资料

- [运行指南](docs/06-run-guide.md) 提供数据解压、入门 Notebook 和仓库原有探索脚本的入口。首轮团队脚本、客户快照、逐人预测和群标签通过组内渠道交接。当前 GitHub 同步的是汇总结果和项目图。
- [旧探索结果](docs/05-results.md) 和 [旧发布验证记录](docs/08-verification.md) 保留原来的证据。四月早期探索的 73 对 45 使用旧模型设置。本轮四月回测用的是十月拟合的八字段模型，三种方法分别命中 45／64／65。
- [历史 Briefing Slides](slides/olist-repurchase-briefing.pptx) · [英中讲稿](slides/briefing-script-bilingual.md)

数据为 Olist 发布的 2016–2018 年历史记录。名单命中衡量排序能找到多少已观察到的复购者。触达后能增加多少订单，需要另外做对照实验。[数据来源与许可](LICENSES.md)
