# A/B 对外措辞独立定向审查

2026-11-14｜结论：**PASS，仅限本次措辞更新。** 未发现阻塞性事实失真或妨碍理解的断点；一处非阻塞笔误已修正并定向回读。

## 范围与方法

本审查者未参与候选撰写。顺读详细 README、简版入口、群消息、PRESENTATION-PLAN、IMAGE-COMPARISON 和 vote-packages，逐项阅读全部 19 个候选相对 before 的差异。对照基线标识为 `61eaafa86fee2f1859948c97b622074a473db08c`，本次未重新认证基线的模型结果。18 个 before 文件的实测 SHA-256 与清单一致，19 个候选的实测 SHA-256 与审查时清单一致。

旧 `review/` 报告及 `final-review` 属于先前版本的历史记录。本报告是新措辞的独立定向复核，不将旧报告冒称为新措辞审查，也不冒称重新验证历史模型、图像或所有来源。没有训练、产生预测、打开四月评价、操作 Git、元数据或看板；只在指定输出目录写本报告。

## 关键判断

1. 当前名称统一为 A“现有成果整理版”、B“在 A 基础上的深入分析版”。详细 README 第 9、43–51 行和简版第 5 行解释了 B 承接 A 的数据审计、逻辑回归基线、字段与分群画像、核验成果，再深化概率可靠性、受控对照、时间/消融反证、价值与容量。没有把 B 重新包装成另一本地独立项目。
2. 具体预测系统仍分别按已记录协议拟合。“在 A 基础上”没有被写成沿用 A 的全部拟合客户或保持同一模型不变。详细 README 第 55–67 行保留 A50/B49 训练与校准不一致的限制；B 内部 43/49 同时改变信息和模型，不能单归因于算法的解释完整保留。固定久单 79 均为 2、三期重叠、指标反例、价值取舍与未验证营销收益等限制未被删除。
3. `vote-packages.json` 去除 A/B 的 `label` 和新增 `presentation_relationship` 后，与 before 解析对象完全相同；原有数值、输入标识、训练/校准参数、容量、状态和流程字段均未改变。其新增 provenance 字段明确名称不代表全组运行了全部实验；PRESENTATION 末段仍要求按实际交付和执行记录列贡献。
4. 群消息用普通语言说明两版关系、B 的三个深化方向和选择条件；“我们补充分析”不构成声称每名成员均执行全部实验。第 23 行明确按实际贡献说明。第 21 行“总体改善”在详细 README/图释中有完整的管线比较及反例限定，不能据此推成纯算法提升或 A/B 胜负。
5. 群消息第一条完整 URL 是详细 README，第二条是图片入口，第三条是简版；末段要求辅助理解时先完整阅读详细说明和图释。顺序符合本次明确要求。
6. 当前材料反复明确仍待真实投票、共同确认配置和分工后才能冻结及制作正式 PPT；没有把建议 B 写成团队已采用。旧原话、实验 ID、目录名、既有独审未纳入本次改写；本次不改变 D14/D05/D09 的 pending 状态，也未复核或更新这些状态的底层记录。

## 非阻塞笔误与交付提醒

- `docs/team/current-status.md` 第 7 行原有“BB内部同协议49对LR43”，作者已改为“B内部同协议49对LR43”。审查者定向回读确认；更新后 19 个候选 SHA 与重建清单仍全部一致。本项关闭。
- 新 `WORDING-UPDATE.md` 的 `review/wording-review.md` 相对链接要求发布时将本报告放入同层 `review/`。主代理已明确将在发布时复制到该位置；本报告不提前确认远端发布。

## 审查时关键文件 SHA-256

以下路径相对候选根目录。结论绑定这些实测字节；后续实质改写须定向复核。纯重复字母修正可按上述方式承接。

|文件|SHA-256|
|---|---|
|`research/route-comparison-20261114/README.md`|`2e1a9991911606392e4d1cbbb88daba8698ac7ed696fa31165fa2c485a4d615f`|
|`docs/team/route-vote-comparison.md`|`f57aa0c8870e22b0f53672b525e4ee60d7703a0be1716cfdf2d48ca503ee4f99`|
|`research/route-comparison-20261114/group-vote.md`|`5b3c2eaf9ea1a98a38f68123b2fa9358fc4c8df44e0f7f94b08f361fa2b7caf6`|
|`research/route-comparison-20261114/PRESENTATION-PLAN.md`|`550f74a6818c26498e3e4715a8d5e118f46faf610107dae25ae62211e7093381`|
|`research/route-comparison-20261114/IMAGE-COMPARISON.md`|`80853a0d42dcb54fdcf317e3bb05f2fa2158f4c71c54cab3177b0e8f9f89025c`|
|`research/route-comparison-20261114/vote-packages.json`|`959cc2a70da02d2b22da240601e5635ad96cc9e728991761ffd005833a3897a4`|
|`research/route-comparison-20261114/WORDING-UPDATE.md`|`853c2477ab49b5c46c24f1766a2578353c5dcb8b5a75ef41320b70487dbb69f6`|
|`docs/team/current-status.md`（笔误修正后）|`01153421ccec478e5455a88eaa13c58f9a8304deb7b5c664ebdb83d7229bae7c`|

本结论不认证团队投票、模型重验、GitHub/看板同步、最终 PPT 或正式提交。
