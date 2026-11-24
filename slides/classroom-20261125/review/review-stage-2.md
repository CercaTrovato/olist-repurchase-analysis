# 课堂新版 PPT：第二阶段定向独立复核

- 日期：2026-11-25；审查者 `/root/classroom_deck_review`，未参与候选撰写。
- 承接 `review-stage-1.md`，不覆盖初读报告。本阶段只核 A1、B1、显示差异及相关来源，不做第二轮全篇审查。
- 已读规则：`D:/上课资料/CityU/_meta/笔记制作与融合验收流程.md` §3。规则由主代理第二阶段提供；第一阶段没有读取作者验收结论或来源答案。
- 只写本报告；没有修改候选、课程文件或 Git，没有重训。

## 1. 最终候选绑定

根目录：`E:/app-data/codex/outputs/is6400-classroom-ppt-20261125/`。

| 文件 | 最终 SHA-256 |
|---|---|
| IS6400_SixSigma_Classroom_20261125.pptx | 763F3EB54639798135C987BB5476E4F5CE2804F268EAB6A2F0A15B24F3348F11 |
| IS6400_SixSigma_Classroom_20261125.pdf | 96B06E3830A369A7E420A70E280FAB63DE81BDAACD1612B7FA1C5B0B40880066 |
| Speaker-Guide-20261125.md | 512D2046B63583401052B732974BB91D2BB38C19E837F1D349F66ACE37656386 |
| QA-20261125.md | 132AF8168005834C3EB583C41678BEC829C5578A5B24D60AA06C29E90CFF780F |

本阶段开头和结尾重新计算，四文件哈希一致。与阶段 1 不同是作者已修订后的新候选，不把阶段 1 哈希误当最终版。

## 2. A1：模型与指标白话桥接已补足本次样本

实际读了 QA 最前面的“先把模型和指标名翻成人话”、QA 2–5、Speaker Guide 第 5 页中文提示，并从 PPTX 的 `notesSlide5.xml` 回读同页备注。

现在仅据候选可以回答：LR 从历史线索学客户评分；复购案例约占 1%，加权使少数复购案例的拟合错误占更大分量，不改变样本人数，也不保证各指标改善。recency 按 R 从小到大排。Precision 看入选名单中的复购比例，Recall 看真实复购者被找到多少；AP 汇总不同阈值下的精确率/召回率表现，ROC-AUC 描述正负样本的整体成对排序，并列记半。

关键变式判断：若 CatBoost 的 ROC-AUC 更高，但固定 10% 名额时少找买家，仍可按本次固定容量目标选择 weighted LR；若五月普通 LR 命中更多，则应报告，不能靠测试结果重选获胜者。这个判断无需用候选未教的专业知识补齐。

来源抽核：

- `E:/app-data/codex/scratchpad/is6400-technical-qa-20261125/h04/train_role03.py` 第 149–189 行：普通/加权 LR 均为 C=1、max_iter=2000、seed=2026，加权使用 `class_weight="balanced"`；RF 为 300 棵、depth=8、min_samples_leaf=20；CatBoost 为 300 次、depth=6、learning_rate=.05、l2_leaf_reg=5，带加权候选。
- `.../sources/research/team-round3-20261112/members/role03/build_training_clusters.py` 第 37–44 行：k=3、k-means++、n_init=20、max_iter=300、tol=1e-4、seed=42，与候选参数表口径一致。
- 冻结测试 `verification.json` 中的分类器配置补证 L2/lbfgs/tol=1e-4；本次只核已记录配置，不声称实际运行完成了上限轮数或存在全局最优搜索。
- 既有 `baselines/README.md` 明确 recency 为 R 越小越优先，支持新增中文提示。

处置：A1 在本次抽样学习任务上关闭；不要求新增完整算法课或再加同型例子。

## 3. B1：79 人协议与证据边界已说清

实际读了修订后的 QA 9、Speaker Guide 第 7 页中文提示，并从 PPTX 的 `notesSlide7.xml` 核到同版说明。实际视觉查看原提交稿 PDF 第 7 页，该页已区分“当前全局 73”和“另固定 79”；原 PPTX 第 5、7 页文字也已只读定位。

相关来源：

1. `E:/app-data/codex/outputs/is6400-round3-20261111/baselines/README.md`：共同口径明确“久单另做固定 79 人排名诊断”，与全局名单分配席位不能混用。
2. 同目录 `run_baselines.py` 第 32 行 `LONG_K = 79`；第 179–180 行对久单子集做 `long_fixed79`，每种方法使用同一容量。该常量的全部引用未见按命中数搜索容量的实现。
3. `E:/app-data/codex/scratchpad/is6400-closeout-20261123/source-cache/research/team-round3-20261112/audit/h04-v02-vs-round3-F0.csv` 加权行：旧 H04 久单席位 79、新 R3 席位 73，均命中 2；两份全局名单共同 2,920、各换 17。

因此可以说“沿用既有固定 79 协议以维持方法间同容量，数值与旧 H04 该群全局席位一致”；不能据此证明 79 的最初唯一成因或业务最优性。修订后的 QA 明确保留这个限制，没有把数值匹配写成已证因果。

处置：B1 关闭。原始取值动机没有完整证据这一来源限制仍真实存在，但当前候选没有越界声称，已不阻塞本次解释与比较。

## 4. 相关数值定向回源

读取 `E:/app-data/codex/outputs/is6400-frozen-test-20261125/metrics.csv` 的全部文本后，聚焦 9 条 Top 10% 行与候选第 14 页对应：

| 月份 | 客户/复购者 | 席位 | recency | 普通 LR | 加权 LR |
|---|---:|---:|---:|---:|---:|
| April | 37,813/299 | 3,782 | 45 | 64 | 65 |
| May | 40,025/284 | 4,003 | 57 | 67 | 65 |
| June | 39,804/271 | 3,981 | 48 | 53 | 59 |

四月加权 precision=.0171866737、recall=.2173913043、AP=.0203653001、ROC_AUC=.6069158930；候选的 1.72%、21.74%、0.020365、0.606916 四舍五入一致。CSV SHA-256 为 `7708ccc53970530a8607c7a2a2d6adec5065440d89d9f3242cdadd40263b4917`，与 `verification.json.metrics_sha256` 相同。

`verification.json` 记录 no_fit_or_tuning_calls、原来源未变和一月 50/46 身份核对。这是主代理执行证据，不把读过记录冒称本独审者重新运行了整条评估管线；本阶段未加载模型、未训练、未重新构造快照。

## 5. 显示差异：保留初读，但撤回文件溢出的推断

阶段 1 的真实观察保留：工具直接展示原 9600×5400 预览时，我把第 8 页两项样本数、第 14 页长小数判读为相接；同阶段直接渲染 PDF 的两页却清晰分列，所以当时未将它确认为 PPT/PDF 本身缺陷。

本阶段实际看图：

- `native-previews/slide-08.png`（原生 PowerPoint Export，9600×5400），四项样本数分列清楚。
- scratch 的 `native-14-1600.png` 和 `pdf-qa-14.png`：AP、ROC-AUC 分列清楚，内容与数值一致。
- 我另外把保留的 `initial-previews/slide-08.png` 和新的 `native-previews/slide-08.png` 直接读取像素、在内存缩为 1600×900 后分别实际查看；两者的 21,308 与 6,380 都有明确空白间隔。没有改变原文件。
- 原提交 PDF 第 7 页直接以 Poppler 输出 1600px 实际查看，73/79 的视觉分区清楚。

显示证据 SHA-256（前缀 `scratch/` 指本任务 scratch，`output/` 指候选输出根）：

| 证据 | SHA-256 |
|---|---|
| scratch/initial-previews/slide-08.png | 4b3d522dc31cf4abb94d4d864ac54539f3742a46430eae1de479e040c4940aa5 |
| scratch/initial-previews/slide-14.png | 886c75e2269f8160192e261a36a088df729547ba1d728b8c5292bf699f50f0b8 |
| output/native-previews/slide-08.png | 66d847ecbb37bb6bb081fd68cdac232b6de5b7e38cf288bf09ff58190d3b2fad |
| output/native-previews/slide-14.png | 1fe675fd4b4b704010c4dff6d6de0dd4c7d117c783bdfec63b74c01594d20d3e |
| scratch/native-14-1600.png | 7aa0450c4c603b330a143d79eaf1d716a1026122ebc17c93462fb55e9455019b |
| scratch/pdf-qa-14.png | 43f71760d1f0dd531d756525c75c2b120971cd915ae038aca17d3a2c2c311daa |

据此更正：阶段 1 的“相撞”不能作为真实文件几何溢出的证据；原图缩图也正常，进一步指向大图展示/判读层的差异。未知根因没有被确诊，不写成某个具体渲染器或导出器故障。最终样本的原生图片与 PDF 显示均无此项阻塞，不需要继续为这个误报改数值或重排整页。

另只读核到第 12 页标题为 `Capacity and validation trade-offs`；第 14 页两个长小数的 OOXML 字号均 `sz="2400"`（24 pt），文字仍为 0.020365/0.606916。没有因该字号改动发现科学数值变化。

## 6. 最终范围结论

本次独立抽检的 A1、B1 均已在候选中落实修复；显示争议经原图缩图、原生预览与 PDF 对照，不再作为文件缺陷。相关四月/五月/六月 Top 10% 数值与提供 CSV 一致。**本次定向样本未留未关闭的教学或显示阻塞**，不是全篇独立通过证明。

未抽范围承接阶段 1：未逐页重新视觉审 15 页；未核全部原始订单、完整标签重建、全部模型/群结果、模型文件哈希与首次见到测试数据的历史；未重新推导试验样本量、未核完整 Guideline、未做真人计时/现场投影/用户作答。来源记录中的作者通过状态不替代独审实核范围。不能据本报告升级本人掌握、排练、正式展示或 Canvas 提交状态。
