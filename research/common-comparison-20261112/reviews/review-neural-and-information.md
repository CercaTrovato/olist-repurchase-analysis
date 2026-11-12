# 神经矩阵与信息/融合解释的独立交叉审查

审查对象为本批未参与撰写、训练的 neural 矩阵及根级单调校准/ensemble规则；不将本人负责的经典模型或旧批P4C冒称本次独立对象。本审查只读，不调用fit/backward、不重训、不改权重/共同分数/经典manifest，不运行bootstrap。

结论：指定30模型/90数组的独立前向与落盘logits逐元素完全相同，未发现阻塞这份冻结矩阵归档的输入、模型前向或fit/cal隔离错误。下列预算、初始缩放、常量分支与数值精度限制应随研究结论保留；本报告不放行正式采用、纯机制因果解释、跨期泛化或最终系统消融。

## 独立范围与承接证据

| 检查 | 实际范围 | 结果/边界 |
|---|---|---|
| 本人显式前向 | 五split×base8/full141×mean/gate/AE，固定seed2026；30模型×fit/cal/Jan=90数组 | 自写保存权重F.linear/ReLU/逐列sigmoid/1⁄6融合，逐元素完全一致，最大误差0 |
| 作者工程重放 | 作者90模型/270数组读回回执 | SHA承接，不改称本人独立前向了全部90模型 |
| 本人全量哈希 | 作者deliverable-manifest全部598项，含90监督state、30预训练state、90共同scoreNPZ、90原logitsNPZ | 全部与manifest相符；不能把哈希相符当新增90模型语义审查 |
| 本人源/共享分片哈希 | 45个源、raw表、五split分片/掩码/变换文件 | 全匹配；141字段清单无y/客户键/日期/群号/score等元数据 |
| 初始化与batch配对 | 15个split/seed组合，每组两info×三家族6格；90条 | 独立重建构造时enc/head参数哈希及50轮监督顺序哈希，全部一致 |
| AE预训练head检查 | 全30预训练state | head权重/bias均与构造时初值逐元素相同；decoder12个张量存在；支持源码的纯重建路径，不冒称重训AE |
| 校准公式检查 | 90run×fit/cal/Jan三组概率 | 独立公式重算a*z+b的sigmoid、Octcal目标/梯度/投影梯度全部吻合；无重新拟合校准器 |
| canonical主ensemble | neural两info×三家族6格，每格三seed | 独立mean(calibrated p)与根helper一致，并打乱一份seed行顺序核对按客户键对齐 |

固定seed2026在读回前已选定，未根据一月指标挑模型。上述“90数组”是本人前向范围；校准公式的全量检查与作者270前向回执是不同证据，不合并冒称更大独立样本。统计代理的155逐run指标/名单和最终bootstrap由其另行核验，本次未重复。

## 模型、fit/cal隔离与AE路线

1. [run_neural.py:28](../neural/run_neural.py)只调用根load_split，传dense=True、dtype=float32，未自行split、重编码或本地再mask。根[eval_harness.py:43](../eval_harness.py)读取冻结CSR、在base8按同一mask置零再转换dtype。五split输入维度808/813/817/813/812，每档仍六个分支；所有fit/cal客户键互不交叉，fit16928/169正例、cal4232/42正例，Jan29368/230全评分。
2. [neural_models.py:73](../neural/neural_models.py)重建只读encode输出与q；[neural_models.py:85](../neural/neural_models.py)的pretrain_AE只接受model/x/epochs/seed，没有y参数。驱动[run_neural.py:88](../neural/run_neural.py)只传tensors[fit]，20轮、batch256、Adam.001。六视图各自MSE再等权平均，无NCE/FN/伪正例等未授权模块。30个预训练head不变为此提供额外状态支持。
3. [run_neural.py:92](../neural/run_neural.py)先model.dec=None，再[run_neural.py:93](../neural/run_neural.py)创建新的监督Adam进行50轮、batch512、未加权BCE、lr.001。已抽查的30监督state均不含dec键，保存标记decoder=False；无冻结encoder，因此AE是预训练后全参数监督适配，不是冻结表征+单一后端的复现。
4. [neural_models.py:51](../neural/neural_models.py)只有fit X/fit y进入监督loss；cal/Jan只在固定50轮完成后infer，cal标签只交根校准器。没有cal/Jan选epoch、earlystop或阈值扫描。4500监督epoch、153000updates与600预训epoch、40200updates的固定预算可核。
5. 配对初始哈希是在模型构造后、AE预训练之前记录。独立重建15组enc/head哈希与90条记录一致；监督generator(seed)与预训generator(seed+901)分离，顺序哈希重算一致。AE监督开始时encoder已经改变，不能把“构造初值配对”写成“AE与mean监督阶段起点完全相同”。

## 信息与融合的解释边界

- base8只暴露原8字段的34个编码列，新增输入每个值严格为0，且只有behavior分支有34个原8列；其余五分支均全0。本次逐split/三时段检查了实际零值。它保持六分支形状，**没有删除五个分支**。[neural_models.py:20](../neural/neural_models.py)的Linear仍有bias，所以零分支产生ReLU(bias)常量，并可在监督中学习；这些常量不提供逐客户新信息，但能改变网络截距/潜空间。名义参数数相同不代表所有权重有非零输入梯度。
- [neural_models.py:23](../neural/neural_models.py)gate_a=gate_b=0，[neural_models.py:27](../neural/neural_models.py)因此初始是x×0.5。即使enc/head初值逐元素相同，gate与mean的初始前向、激活边界及有效优化尺度也不同；另新增2D参数。因此本轮比较是预定列门控方案整体对照，不是已隔离“学习门”的纯机制效应。后续固定0.5缩放参照/参数控制仍属消融，不为当前结果临时补跑。
- AE比mean/gate多20轮无监督训练；base8大量重建目标为0，且每视图MSE等权，较full141更容易得到低MSE。不能把base/full重建值直接解释成哪档“业务结构更好”，也不能把AE的差异全部归因于抽象表征机制，忽略额外预算/目标变化。
- 六视图内部融合是固定1/6均值，[neural_models.py:30](../neural/neural_models.py)没有学习视图softmax或样本级attention。列sigmoid门也不是Q/K/V自注意力。它与最终“三个seed概率平均”的ensemble是两个不同层次，发布解释应分开。
- 根存储矩阵是float64，neural源代码明确转float32并以float32训练/推理；随后float64容器保存这些实际推理值。不能称全部模型双精度训练，也不能因保存dtype=64就声称恢复了精度。这里控制了同一字段、变换、行序与mask，经典与神经运算精度本身仍不同；当前README对此已有准确说明。

## 单调校准与最终ensemble一致性

根[eval_harness.py:55](../eval_harness.py)只用该split的Octcal logit/y拟合sum BCE+0.5*a²/1e6，a>=1e-6、b不罚；[eval_harness.py:90](../eval_harness.py)没有混入fit或Jan标签。90run的a全部为正，本次独立复算三期calprob、校准目标、梯度及精确定义的θ−P(θ−grad)投影梯度都与保存值一致。

有5格落在a=1e-6下界：split20261113__full141__AE__s2028, split20261113__full141__column-gate__s2027, split20261113__full141__column-gate__s2028, split20261113__full141__mean__s2028, split20261114__base8__mean__s2028。它们近似常数校准，不能由优化success推论原始排名已被验证有信息。cal只有42正例；校准后的同cal指标为拟合内再代入，不能作无偏验证。90个success中，实际投影梯度大于1e-10的有78格，最大2.7543e-06；优化器可能由ftol停止，记录实际梯度是必要的，不将success重新包装为达到gtol。

根task_plan §35与[statistics_core.py:25](../statistics/statistics_core.py)一致：canonical split20261111按客户/日期一对一对齐，主ensemble为三个seed各自校准概率的均值，概率损失、AP及名单必须用这同一列；确定性LR只一份。[statistics_core.py:41](../statistics/statistics_core.py)的raw-logit均值是另列诊断。不同模型的单调校准斜率/截距不同，所以“各自单调”不意味着mean(logit)与mean(calprob)的ensemble排序相同，不可混接。

本人用neural六个canonical格实际数组独立计算三份calprob算术均值，并打乱一份seed的客户顺序，核根helper仍按键正确还原，差异0。此项核helper及输入绑定，不冒称最终bootstrap/所有家族候选表已被本次重复审完；其最终落盘统计快照由统计代理回执承接。单模型raw排名策略与主概率ensemble是预先区分的两个对象，不将两者AP/命中拼接成同一方案。

三seed范围只表示初始化差异，五训练划分表示同一Oct样本扰动，都不是15个独立时期；固定分数bootstrap也不包含重训/特征选择/方法搜索不确定性。一月已见，未来时间验证与营销因果增量均未由本矩阵证明。

## 是否需要修复与未覆盖范围

本次没有发现需要改模型、分数、split、校准或训练源码的阻塞缺陷；上述混杂多数已在根计划和neural README显式保留。发布主文须继续使用这些边界，不能把“信息档控制”“同初值/同batch”“success”扩写成完全排除机制/优化/数值因素。

本次未独立重训AE、未逐步重演全部优化轨迹、未重新检查P2所有原始订单时点或静态/回写日志假设。后者继续按既有P2来源审计承接。未审本人参与的经典矩阵作为独立放行，也未重新跑统计bootstrap。

## 审查留痕

- 自写显式前向脚本：E:/app-data/codex/scratchpad/is6400-common-comparison-20261112/review-neural/audit_neural.py；SHA256=0b5278bef06ada572cfb1778fd56b880206992fabcc30c7e544bbfc181e45958。
- 独立30模型/90数组CSV：E:/app-data/codex/scratchpad/is6400-common-comparison-20261112/review-neural/independent-90-array-replay.csv。
- 独立汇总回执：E:/app-data/codex/scratchpad/is6400-common-comparison-20261112/review-neural/receipt.json；SHA256=3cdd3d0eb05dd3fe1e418fdbf796cbaf99f952b83b5801e9ae57779df32a998a。
- 独立45文件source/shared哈希回执：E:/app-data/codex/scratchpad/is6400-common-comparison-20261112/review-neural/shared-hash-receipt.json；SHA256=b9e68041513a0d43e68a9f482a5e957f6b8ab86106ad30fb3943d680febc66d5。
- 作者598文件manifest SHA256=d3d02d707daf0240a092d399ae4db7ac05a45e48989a8e7abae9015de7cd5057；作者270数组回执SHA256=f931273a67fc851f8c77323ed705828bfe9e7478241b09215d6452accad9f8f2。
- 共同manifest SHA256=1be6816d26676a2ed08a83be4f7f212e79d13c7fba88d663f84e9d3b904e8d57；harness SHA256=ae94dab62cd4bbd4b1b7c7098601640adaa945a60e15bb12e4d5050156e3ff1c。
- 原神经/经典模型、共同分数、manifest均只读，无Git/看板/外发/安装/April操作。
