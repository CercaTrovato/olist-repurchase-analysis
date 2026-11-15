# 新会话按A制作PPT：直接接续，不再默认B

2026-11-15本人最新直接确认，当前PPT采用A“现有成果整理版”；本人会自行开启另一会话制作。此前B已选/B第一稿都保留为历史，不是当前正式主线。本文件是制作交接，**本会话没有生成A稿或提交任何文件**。

## 先读

1. 本目录`README.md`和`route-decision.json`，理解分歧及最新A确认，不重新发起路线投票。
2. `A-baseline.json`：本稿建议直接使用已核的团队R3 F0八字段加权LR资料，具体最终版本/主指标描述在成品核数时记录，不阻断先做完整稿。
3. 原制作交接`E:/app-data/codex/outputs/is6400-ppt-handoff-20261115/README.md`只沿用教师要求/文件安全/审阅提交流程；其中B模型与“B已选”属于历史，不能沿用为A主结果。

## A主线用大白话讲

用过去六个自然月的客户历史预测之后90天复购，给全体合资格客户评分；统一取前10%比较名单命中，再用客户分群检查漏判和提出特征假设。10%是可比容量，不是只预测10%的人，也不是已核真实运营只能联系这么多人。

一月同选2937人，加权LR命中50，未加权46，最近购买优先基线30；所测配送/评价/群号/群模型未超过该主容量的50。分群的价值是诊断和提出假设，不能说分群就自动提高预测。名单命中不等于联系后新增复购或利润；未来内容随机试验仍只是设计。

## 版本与数字：用这一套，不拼接

- A制作基线：`Round3_role03_prediction_v1`的F0八字段加权LR，H02-v2-candidate-reviewed，H05-km3-v1诊断；十月2017-10-01全21160人/211正例拟合，没有专用概率校准集。
- 八字段：`R,F,M,average_item_rows,freight_share,recent30_orders,recent30_spend,state`；数值log1p/填补/标准化，州编码，LR C1/balanced。主解释为排序分，不把加权分数直接说成自然复购概率。
- 一月2018-01-01为已见开发评价：29368人/230复购者，K2937，命中50；Precision1.7024%、Recall21.7391%，展示精度统一即可，源数值以CSV为准。
- 三群全局入选/命中：群0为2190/21，群1为73/2，群2为674/27，加总2937/50。久单群1共有12330人/90复购者；另固定群内79名额仍命中2，不能把73和79混写。
- 旧H04也有一月50，但与当前R3名单不完全相同。四月45/64/65来自H04 v0.4的独立已见回测记录，不能直接拼成R3 F0的“最终测试”；默认先用已核一月主结果，不新跑四月。
- B的16928fit/4232cal、43/44/49、141字段CB、概率和292.93及金额比较，不是A的成绩；若作为备查，明确其B协议身份。不能只换图上数字或把B三期结果算成A三次验证。

## 现成素材与代码入口

本地聚合与当前群卡：
`E:/app-data/codex/outputs/is6400-round3-team-intake-20261112/audit/january-recomputed.csv`
`E:/app-data/codex/outputs/is6400-round3-team-intake-20261112/audit/january-groups-recomputed.csv`
`E:/app-data/codex/outputs/is6400-round3-team-intake-20261112/figures/`

当前A模型代码：
https://github.com/CercaTrovato/olist-repurchase-analysis/blob/main/research/team-round3-20261112/members/role03/run_round3.py

A完整验收和版本边界：
https://github.com/CercaTrovato/olist-repurchase-analysis/blob/main/research/team-round3-20261112/README.md

A汇总表：
https://github.com/CercaTrovato/olist-repurchase-analysis/blob/main/research/route-comparison-20261114/data/team-capacity-results.csv

当前三群画像及结果图：
https://github.com/CercaTrovato/olist-repurchase-analysis/blob/main/docs/team/round3-team-figures.md

只用2号v1.1已修区间/描述图或课程已核派生图，不用撤回的旧SE图/5号错误区间图；2号新推荐组合不等于3号已测F1/F2，不能称其已被证明无效。1号时间审计、4号画像/未执行试验设计、5号有效核数等贡献保留，讲清分母和版本，不重做模型。

## 8分钟组织建议

可以按业务问题→数据/时间→整体EDA/字段→原版/加权与最近购买基线→已测改动/验证→分群漏判→业务试验设计→结论/限制组织，正文约8页、少量备查；这只是建议，不是老师硬性页数。

沿原1号数据、2号EDA/字段、3号监督预测、4号分群、5号核数反馈、6号业务统筹分配内容，并给每人对应页讲稿/问答；仅用编号，不放姓名/学号。实际认领、理解和真人排练要另核，不能假定选A就自动人人会讲。全员要展示并参加Q&A。

## 要求、目录与提交边界

教师指南`D:/上课资料/CityU/IS6400_Business_Data_Analytics/course_files_export/IS6400 Project Guideline.pdf`：最终8分钟＋2分钟Q&A，面向经理，涵盖问题/数据/分析/发现/结论。5页3分钟只属早期Briefing，报告20–25页不套到Slides。

制作会话今天已登录侧栏核339540的截止/关闭为11月15日23:59香港时间，file upload/20points，小组提交影响全组。最终提交前需依新授权核入口/账户/附件及真实成功回执；本次路线切换没有批准任何最终稿上传。当前仍不选文件、不上传、不提交。

本轮只制作A新稿、配英文讲稿/中文排练、双语Q&A及人类可读说明。可参考B初稿的视觉样式，但新建独立目录（例如`E:/app-data/codex/outputs/is6400-A-final-presentation-20261115/`），不覆盖B第一稿或原研究。复用已存数据重排图表，不新训或追加实验。

完成可编辑PPTX/PDF、逐页实际渲染/核数/独审后，先交本人和小组过目修改；只有本人之后明确批准最终版本，才进入Canvas操作。不把截止临近当授权，也不重复催当前稿提交批准。元数据和公共资料按已获授权的GitHub→本地→线上流程核真实版本；保留成员真实交付/学习字段，不公开原始群聊截图或私有逐客表。

## 复制给新会话

请完整读取：
`E:/app-data/codex/outputs/is6400-route-A-decision-20261115/README.md`
`E:/app-data/codex/outputs/is6400-route-A-decision-20261115/A-PPT-START-HERE.md`

最新决定已重新确认A“现有成果整理版”，请按A已核团队R3 F0全十月八字段加权LR结果制作新的最终展示草稿；B第一稿仅保留参考，不能把其43/44/49当A结果。按原1–6号职责安排可编辑PPT、讲稿/中文排练、问答和人类说明，目标8分钟＋2分钟Q&A。不要重训、新实验或新评价四月，也不覆盖B稿。先完成并核数/逐页渲染/独审，再交本人及小组过目修改；当前没有Canvas提交授权，不代提交。
