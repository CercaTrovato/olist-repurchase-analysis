# 第三轮验收说明独立顺读回执

审查者：未参与候选撰写的独立子代理，`gpt-6.1-sol / high`。日期：2026-11-12。

本回执接续 `role03-source-review.md`、`role02-ci-targeted-review.md`，只做一次完整顺读和必要定向核对；未训练、未运行附件代码、未新评分四月、未重复 bootstrap。候选审查范围是根 `README.md` 全篇 114 行与 `group-update.md` 全篇；导航文件、全部原始数据回算、13 组图逐张视觉及外部同步由主代理负责，不冒称由本独审重新全部完成。

## 当前结论

**本次验收说明独立审查通过，无未关闭的实质阻塞。** 首轮唯一待改是 README 第 112 行提前写“已发布”，另建议第 88 行明确样本量为两组合计；作者已修复，已定向核实。该通过不升级成员源包的待补状态，不代表6号正式采用、5号已交或外部同步完成。

|检查点|独立顺读与定向证据结论|
|---|---|
|成员自报冻结与正式采用|README:7,69,101–104 明确分开成员自报、真实采用版本与6号记录；未倒填21:00，也未据自报推断动机。群回复仍称主方案“参照”、正式采用待记录。|
|2号组合未接入|README:48–55 区分2号推荐与3号实际字段，未将未测试组合写成无效；不自动启动新训练，最小补件保持记录性。|
|基础CV与群模型CV|README:65–66 与源码审查一致：基础分类Pipeline各折fit；B/C的全十月无标签群映射包含验证折协变量，不称整个流程完全隔离；不把随机5折说成5个未来月份。|
|四月解析与拟合/评分|README:67–69 区分整表读取、训练、评价和按结果选择；没有宣称零解析，未把单纯读入认定为目标泄漏；历史四月继续为已见回测。|
|2号CI修正影响|README:59–61 与独审代码流及聚合回算一致：20/56行误用全组n，点估计/AUC不变、筛选不读CI、跨0状态0行改变，不因此全包否定。保留作者确认和重交状态。|
|旧新50命中版本|README:38–44 与 `audit/h04-v02-vs-round3-F0.csv` 一致：旧新名单交集2920、各换17、标记34行不同，久单79→73，均2命中；未加权名单一致。明确本次未重新验v0.4包。|
|已有配置复跑|README:42–44 与 `audit/base-replay.json` 一致：2次existing_configuration_replay_fits、0新候选、0四月预测；当前R3名单全重现，分数最大差5.27524e-5，不宣称位级重现、不唯一归因。旧wrapper不同分数/名单也据实限定。|
|关键模型表|README:24–34 与 `audit/january-recomputed.csv` 的5个加权/群方法Top10%一致：50/48/46/50/49及固定久单79命中2/2/1/2/1；本地当前画像表支持R3 F0的2190/73/674席位和21/2/27命中，总2937/50。|
|4号画像、试验及样本量|README:76–88 与旧/新画像聚合及 `audit/role04-readback.json` 一致；明确新卡是课程核验衍生、试验未做、可触达资格未知。3个样本量均为两组合计76784/21308/6380；MDE规划非已有效。|
|验收与独立限制|README:20,103,114 区分160附件hash通过、实际回算、5号尚未交、候选/采用/提交；不把机械汇总核验变成重跑全部模型/新未来检验。|

## 定向修改

1. **README:112，发布状态提前写成完成。** 候选写“已实际检查并发布13组”，但当时主代理仍补白名单/导航，未提供本批GitHub/看板/线上最终回执。建议改“已实际查看，本批发布白名单纳入13组……累计85；实际发布状态见操作回执”。这不影响图的实质评价，但需避免版本状态混淆。
2. **README:88，明确总样本量。** 建议“所需总样本量（两组合计）”后接76784/21308/6380，避免读者误当每组人数。原数字正确，不需要重算。

## 绑定证据

初审候选及关键证据的 SHA-256（小写）：

|文件（相对本任务输出根）|SHA-256|
|---|---|
|README.md（本次全篇顺读版）|ceea1964bf9d51e40c372fe02479d0660e139be1dd791a3e31a28d6a8846310a|
|group-update.md|2ced3b3317e5a11c89137f9ed6c6e547b90728f921dbf56e9331911518e8d2f3|
|audit/base-replay.json|9377d78d7eef24fcc9e2a7788258d6b25c9bfd9ebb499a4340e14e5cdf30f0dd|
|audit/january-recomputed.csv|ce57e03677fbd35912080e67527e2b0a7b5bc77a73c82b265c3d00b2fa309f01|
|audit/january-groups-recomputed.csv|218883989cd068af9130f5a00055c3a71e56d9131b767a99898ade4591554dfa|
|audit/role02-evidence-recomputed-corrected.csv|6b8bedf3837008e3ca00f9caf5836e2b30d7128d80d8a7124c7629d228f570e9|
|private/extracted/role03/Round3_role03_prediction_v1/run_round3.py|cb52be785c6863ee66df1b1f7c02d2163998cfc4904109348d2d54f4444dd943|
|private/extracted/role03/Round3_role03_prediction_v1/run_group_models.py|027122f1fc5c018869af50985f93b812d0f8894bd3fbd62b11426d7ccba690bd|
|private/extracted/role03/Round3_role03_prediction_v1/build_training_clusters.py|de473e8710c1bc1631541c9a37218c0ff5eb667dd3cdd145f8ef5c2f58d29f21|
|private/extracted/role03/Round3_role03_prediction_v1/training_clusters.csv|ccafa2e968ef7f43a32ae825c771f51647a39ddf6d5a625b1be74e5db39775bf|
|private/extracted/role03/Round3_role03_prediction_v1/validation_clusters.csv|509e6df79c758be73c693ea63a5e1ff9a33db97bcbc168d218b47dfe02d55f85|

原件哈希与根intake-manifest一致。关键推断已回源当前交付，历史记忆只作口径定位，不替代本次实证。

## 定向复核与封板

- README:112 已改为“已实际查看……本批发布白名单纳入……实际发布状态见操作回执”，关闭提前宣称发布的问题。
- README:88 已明确“所需总样本量（两组合计）”，数字不变，关闭读者可能误解。
- README:29–30 的 F1/F2 久单席位及命中由“见完整表”替换为148/3、189/2。已与 `audit/january-groups-recomputed.csv` 中Top10%、cluster1对应两行定向对齐；固定久单79的2/1仍与原汇总一致。
- 未重开全篇审查；承接初审未改范围的证据。最终 README SHA-256：`7731a2917ebf0b86cec60b8a4e14391427551d63662c33dd631400726a15e219`。群回复草稿哈希未变。
- 新补绑定：`audit/h04-v02-vs-round3-F0.csv`=`aa53636a3d3886492cdaf1510bfdb094c181b7ab77e76850f9bdd7c14b1a6b98`；`audit/current-profile-summary.csv`=`943745d0c1f66759c52435a2f850289f47356784d957c08451f115dd35648c06`；2号 `scripts/r3_evidence.py`=`5941ccb449ceaf49dc5087c409894fe31c53a25a0c87c5a345848def7d744d7f`，`scripts/r3_common.py`=`1254d5404d095c625d668012eeb31f7ac9a677d23f620476f08aff9ae31395d9`。
- 机器可读绑定及报告本身哈希见 `independent-review.json`。若正文/关键证据后续有实质变化，本回执不能自动外推到新字节。
