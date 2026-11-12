# Olist 复购预测与客户分群

## 进度与每日事项入口

- [项目时间线：已完成、当前与未来](TIMELINE.md)
- [个人助手读取说明](ASSISTANT-README.md) · [结构化时间线](progress/timeline.json) · [总监督每日事项候选](progress/daily-plan.json)

时间线按可核事实维护，建议日期需确认，等待回件与已验收分开。线上只读看板：https://cityu-board-online.vercel.app/


IS6400 小组项目｜Six Sigma

我们用过去 6 个自然月的订单给已有客户排序，比较同等名额下能找到多少未来 90 天的复购者。主比较把名单容量设为 10%，并与最近购买优先等简单策略对照。分群用于定位漏判，也给内容试验提供线索。

**2026-11-12：四候选统一比较已完成。** 两档字段、共享矩阵、五个重叠训练/校准划分及三个随机种子，共155个监督模型。完整字段AE概率融合值得优先研究，CatBoost在概率质量上较好；名单增益条件区间仍含0，尚未替小组冻结正式采用版本，消融后置。

[最新统一比较与候选建议](docs/team/common-candidate-comparison.md) · [本轮17幅图](docs/team/common-comparison-figures.md) · [全部57幅图](docs/team/visual-assets.md)

[上一批Q01–Q18验证](docs/team/validation-execution.md) · [建模质疑台账](docs/team/research-questions.md) · [验证设计历史](docs/team/research-protocol-draft.md) · [MVSIB迁移核读](docs/team/mvsib-transfer-notes.md)

## 真实团队已核进度与历史结果

**一月加权模型和按群复核已对齐。** 同样取 2,937 人，最近购买优先命中 30 人，原逻辑回归 46 人，加权逻辑回归 50 人。加权后久单群入选从 17 到 79，命中从 0 到 2。当前主方案候选是原八字段加权逻辑回归、全局前 10%。四月三份名单已复现，45／64／65按已见窗口回测记录。交接说明和正式采用版本仍待收尾。

[小组最新进度](docs/team/current-status.md) · [本地探索与对照](docs/team/local-exploration.md) · [汇总表与图](docs/team/evidence/README.md) · [各岗入口](docs/team/README.md)

**第三轮已发群。** 6 号已确认业务取舍和展示采用截止。本地六基线、新增信息、时间审计与内容试验设计已完成，当时两批共18幅图；当前全部主素材57幅，见最新图表索引。组员按同目标独立设计策略，本人已确认发群，成员新回件待核。

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
