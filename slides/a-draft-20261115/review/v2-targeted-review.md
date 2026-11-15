# A 初稿 v2 定向独立审查

时间：2026-11-15 16:00（UTC+08:00）。审查者未参与 v2 制作。本次只检查用户新增的七方法筛选、第 4→5 页版本转场、第 5 页主讲变更、第 8 页总结，以及配套材料同步；未重新审查其余教学内容、未重训、未新增实验、未访问旧课程会话或 Canvas。

**结论：本次改动无待修的实质问题，可以交用户及组员继续审阅修改。仍是草稿，不授予 Canvas 上传／提交权限。**

## 1. 绑定版本与检查范围

PPTX：`IS6400_SixSigma_A_Draft_v2.pptx`，直接计算 SHA-256 为 `67c776aa8013a397ff5073050bdc9a68d10de9ac4edd4c18cc73592a823144ed`。

本次读取 `source/ranking-comparison.csv`、`source/ranking-provenance.json`、`source/slide-content.json` 中第 4／5／8 页；读取 README、成员说明、英文讲稿与中文排练的对应段、16 条备问答及群说明的改动口径。实际查看原生 PDF 渲染的 `rendered/slide-04.png`、`slide-05.png` 两张完整单页图。直接读 PPTX 内相关 notes、chart1 及对应工作簿。没有读取主代理通过回执；`review/v1-independent-review.md` 只作为此前独审的历史入口，本次另写本报告。

## 2. 七方法 CSV 与来源身份

实际从持久原件 `E:/app-data/codex/outputs/is6400-h04-v02-intake-20261110/H04-role03-v02.zip` 读取 `H04_role03_prediction_v0.2/ranking-comparison.csv`，与 v2 的 `source/ranking-comparison.csv` 逐字节相等；直接计算 SHA-256 为 `0c441cba15087c84c24f77a540b040675ad9eab0bebc05083e1ab8b4d4f5bb9a`。没有把文件名相近或数字相同当作来源身份。

另读取 ZIP 中 `run-metadata.json` 与 README：训练快照为 2017-10-01，评价为 2018-01-01，使用原八字段 `R,F,M,average_item_rows,freight_share,recent30_orders,recent30_spend,state`，全体评价 N=29,368、正例 230，K=ceil(10%×N)=2,937。该 CatBoost 是 H04 八字段候选，参数与 B 的 141 字段校准系统不同。原包中关于未来四月的旧描述仅按当时历史口径理解，v2 没有据此恢复盲测身份。

| 方法 | CSV 命中 | v2 可见图／讲稿 |
|---|---:|---|
| Weighted LR | 50 | 一致，位于顶部并用洋红色强调 |
| LR | 46 | 一致 |
| CatBoost | 45 | 一致 |
| Random forest | 44 | 一致 |
| Weighted RF | 36 | 一致 |
| Weighted CB | 35 | 一致 |
| Recency | 30 | 一致 |

WLR 的 AP 为 0.029796574055586278，是七者最高；ROC-AUC 最高为 CatBoost 的 0.5864550847988732，WLR 为 0.5820409326533109。主讲、中文说明和 Q15 准确以固定容量命中为选择依据，没有声称所有指标都赢。Precision=50/2937=1.70%，Recall=50/230=21.74%，与图中文字一致。

## 3. 版本转场与结果边界

读取 `research/team-round3-20261112/audit/h04-v02-vs-round3-F0.csv` 的实际现存输出：加权旧／新均命中 50，但名单交集 2,920、各替换 17 人，久单全局席位旧 79／R3 为 73。未加权名单相同不证明整个加权执行版本相同。

第 4 页页脚明确标 `H04 v0.2 model screening`，讲稿说明下一页使用 later R3、保存分数／名单不同；第 5 页开头与页脚均再次明确切换到 R3。第 8 页总结分别写 seven-method screening 和 later R3。README、成员说明、Q16、群说明同步这一阶段区别，没有将 H04 的 AP／AUC 与 R3 的群切片拼成同一个保存版本。

后续 R3 的 50／48／46／50／49、CV 7.0／6.8、当前久单全局 73 及另固定群内 79 保持此前已核口径；本次没有将 H04 筛选的八字段 CatBoost 45 与 B 的 141 字段 CatBoost 49 合并排名，也没有迁用原错误区间或新称统计显著。未重新运行这些结果。

## 4. 两页实际图与原生图表

- 第 4 页实际图七条水平柱按 50→30 显示，方法标签、数值、同容量说明完整；WLR 单独强调，其余灰色。没有裁切、重叠、轴向误读或数值标签错配。
- 第 5 页实际图仍为 50／48／46／50／49，CV 摘要可读；新增 R3 转场页脚清楚，无新增溢出。
- 直接读取 `ppt/slides/charts/chart1.xml`：类别区域 `Data!$A$2:$A$8`、数值 `Data!$B$2:$B$8`；缓存顺序为 Recency／Weighted CB／Weighted RF／Random forest／CatBoost／LR／Weighted LR 与 30／35／36／44／45／46／50。横向图显示方向使 WLR 在顶，符合实际单页图。
- 读取 `ppt/embeddings/ChartData1.xlsx`：`Data` 共 8 行，B1=`Buyers`，与系列缓存及公式 `Data!$B$1` 一致。关系 `rIdData` 指向实际内嵌 `../../embeddings/ChartData1.xlsx`，数据未误接旧双柱工作簿。
- 第 4／5／8 页新脚本实际存在于对应 PPTX notes，公开 CSV 来源路径已加入第 4／8 页 notes。未实际点击 PowerPoint 的 Edit Data UI；本次证明包结构、缓存和工作簿数据一致。

## 5. 分工、时间与材料同步

README、成员说明、英文讲稿、Q6／Q10／Q16 和群说明均将第 4／5 页归 3 号连续主讲，共 150 秒；5 号负责第 6 页 55 秒。没有残留要求 5 号主讲第 5 页的本次有效安排。六人仍都有正文发言，总预算 460 秒，加 20 秒换页，Q&A 另计。

第 4／5／8 页脚本分别 137／156／73 词，对应 75／75／35 秒，约 109.6／124.8／125.1 words/min；全体正文当前 964 词，460 秒约 125.7 words/min。新增筛选和转场未把结尾重新推到先前的抢读速度；这仍是预算，成员真人试讲状态没有被提前记为完成。

16 问答中的新 Q15 正确回答“固定容量胜出但 AUC 非最高”；Q16 正确回答 H04 与 R3 保存版本不同、73／79 区分。群说明提出的分工和反馈范围与本稿相符，但本审查没有发送群消息，也没有以草稿文案代替实际 GitHub 发布回执。

**收束：本次定向检查全部完成，没有需返修的实质发现。未变部分承接此前 A v1 独审和定向关闭；不重新声称整个项目已获新一轮全篇验证。下一步仍为用户及成员审阅修改，禁止 Canvas 上传／提交。**
