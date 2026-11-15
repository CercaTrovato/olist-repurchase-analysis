# IS6400 PPT 制作交接独立审查

审查日期：2026-11-15。审查对象是新会话使用的制作交接，**不是最终 PPT 验收、上传或提交成功认证**。

## 当前结论

**PASS，仅限制作交接。** 交接可直接支持零上下文的新制作会话启动 B 版制作。首次整篇顺读发现的两项具体缺口均已修正并定向回读：配置状态字段歧义已消除，2 号修正图 PNG/SVG 已补入索引。当前无交接阻塞；无需重开投票、模型实验或等待 Canvas 登录才能开始制作。

## 审查范围与已核事实

独立顺读 `README.md` 全文及 `team-adoption.json`、`requirements-check.json`、`asset-index.csv`、`preparation-checks.json`。实际查看教师指南两页渲染，核对已有抽文及原 PDF SHA-256；读取课程作业规范 §7。初审核实原素材索引 29 行，定向复核新增 2 行后的全部 31 行绝对路径和 SHA-256，无缺失、无不一致；本地参考模板通过 PPTX 包内 slide XML 计数确认是 5 页。

1. **决定与冻结分离。** 本人本轮直接确认团队选 B，足以承接路线采用，不编逐人票数。修正后正文及 JSON 明确 D14 为已选 B，D05 具体配置和 D09 主指标仍待独立采用记录；用既有提案先制作完整可审阅稿，不把路线投票追认成事前盲测或所有配置已经冻结。
2. **教师要求正确。** 指南第 2 页要求 8 分钟展示加 2 分钟问答、公司经理受众、全员展示并参加问答、覆盖问题/数据/分析/发现/结论、团队代表上传 Canvas。5 页/3 分钟属于早期 Briefing；20–25 页属于报告。8 页主讲、460 秒加缓冲、PPTX/PDF 是制作建议，未伪称教师硬性页数、模板或上传格式要求。
3. **截止证据有日期边界。** 23:59 香港时间明确来自 2026-11-14 已登录观察；今日 IAB 重开入口需登录，未声称今日成功读取详情。本审查未独立登录复查 Canvas，不将昨日观察升级为今日认证。交接要求新会话核新通知且不因此停止可独立制作，合理。
4. **提交与审阅顺序正确。** 正文直接引用课程规范 §7“用户审阅后再提交”，先出完整成品再供审阅，不索取空白批准；最终入口、代表账户、格式与回执分开核。没有编写已上传/已提交状态，没有扩大到报告提交。
5. **科学事实按已核版本承接。** 49 对 43 是字段和学习器同时变化的管线差；50 对 49 拟合/校准安排不同。久单固定 79 与全局名单久单 73 席分开；三期已见重叠、概率偏移、价值排序取舍、非营销因果收益等限制保留。价值图被正确标为六面板散点，CV 为 SD，信息控制划分不当独立时间实验。此次未重训或重新审全套科学证据。
6. **成品与资料边界清楚。** 早期 5 页模板标为参考，不能当最终成品或官方模板；最终 31 项素材均为现存文件，不冒称新增实验。教师 PDF、逐客数据和模型不在拟公开范围；成员信息、署名、AI 使用说明和提交件去管理信息均有交代。新会话输出目录、仓库、课程单写者接替及监督同步入口可定位。

## 具体问题与定向复核

- 已关闭：原 JSON 字段 `concrete_model_metric_freeze_separately_recorded=true` 可能被误读成配置/指标冻结已经完成。现改为 `concrete_model_metric_freeze_requires_separate_record=true`，并明确 D14/D05/D09 状态；正文第 1 节同步明确，已定向回读。
- 已关闭：正文 §7 称 2 号修正效应图“准确图路径见索引”，初版 29 行 CSV 未收录该图。作者现补入 `E:/app-data/codex/outputs/is6400-role02-v11-intake-20261113/private/extracted/Round3_role02/figures/02-candidate-effect-sizes.png` 及同目录 SVG 的两行精确路径、远端路径和 SHA，明确为 full 而非 smoke；检查记录同步改为 31 行。审查者核实两文件存在及哈希一致，不需重审模型。
- 后续两处定向回读：§7 已把参考模板改为完整本地绝对路径并附原 GitHub `slides/olist-repurchase-briefing.pptx` 链接，避免公开交接缺少本地副本时相对位置歧义；索引 SHA 明确只绑定 `local_path` 实际字节，已规范化行尾的 GitHub SVG 应按对应发布包 `public-evidence-manifest.json` 校验。本审查接受这一校验范围澄清，未重验全部远端 SVG；此前本地 31 项核验结论保持。PASS 继续适用，README 绑定更新如下。

## 关键源与交接 SHA-256

|来源/文件|SHA-256|
|---|---|
|教师 `IS6400 Project Guideline.pdf`（2 页）|`61be22d79c2f2c6415bae7fdd7a981bb5ac3679c8739314cf33afcd1d848afe3`|
|本地 5 页参考 `reference/olist-repurchase-briefing.pptx`|`8751de687219282ad1927bd97af6d9b19b1f6d1a691d1a9d516d0d34a3809672`|
|`README.md`（已补绝对模板路径、原 GitHub 链接及本地/发布 SHA 范围说明）|`0cbe5ea386e57c547f504b0bd5d6e3e7eb89cf8b8ca846828deb71d5e067217b`|
|`team-adoption.json`（澄清后）|`75dadeb4d0410011879015b5dbcdae54dd60a7ff59e6a11c9c250538c51b856a`|
|`requirements-check.json`|`22e2dd62c6e286ed99f9b8fb58fdfb2bc16e0555d94a8f257dafccd348828c10`|
|`asset-index.csv`（31 行）|`f22215237f69aee935be389cd0be8c17addff1464b65ceae7bff583cc1b7cf95`|
|`preparation-checks.json`（31 行）|`4f53e5c30a2a0a158514a8346e357b06909e410077aa2c821adf1f3f0cb98dd4`|

本审查只写此报告，未制作 PPT、训练模型、写 Git、修改课程源、登录/上传 Canvas 或操作看板。
