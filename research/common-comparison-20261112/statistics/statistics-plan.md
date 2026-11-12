# 统一比较：统计估计方案冻结

2026-11-12，先于本批模型结果读取。当前只核方案／建骨架，不训练，不Git／看板／外发，April读取0。根级task_plan为唯一实验计划；本文件细化统计估计对象。数据adapter待根给实际schema后冻结，不能擅自猜键或把未到数据标完成。

## 必须在结果前对齐的控制

1. canonical主ensemble使用同一客户的三seed单调Platt概率算术均值，以该概率同时计算proper loss、AP/AUC与名单；weighted／unweighted LR确定性各仅一份分数，不伪造三seed。mean(raw logit)为独立诊断规则，只能作排序，不混接其名单与mean(probability)的proper loss／区间。根级计划已在任何新结果前改为概率均值主规则。
2. base8以编码血缘白名单保留原8全部编码、置零所有新增编码／missing／代理字段；同split各家族读取同一矩阵，base/full全宽与六分支维数相同。原8州OHE独立且无rare合并。统计前核矩阵哈希、列mask与参数计数；不把零输入分支说成已删除，它仍可学习常量bias。AE对零占位的重建、额外20epoch预算、门控初值.5缩放均属于模型包，不作纯因果归因。
3. 每split仅fit拟合预处理／模型，cal42正例仅拟合a>=1e-6的单调Platt；保存active-bound、实际梯度／投影KKT、失败／warning。请求tol不能证明收敛。不同split的rare类别／编码宽度可能变化，须保存各自维度／参数；同split对照有效，跨split波动同时含样本和编码变化。
4. 5split重叠、同一Jan重复评价，不是5个新时期；三seed也不是独立时间样本。禁止15次独立binomial或以seed SD充当泛化CI。全部失败、负结果与三seed保留，不依据Jan扩参数或选seed。

## 单运行、配对与稳定性

- 每run保存全体及H05三个群自然LL/Brier/AP/AUC、固定0.5分类／校准诊断；策略global K1469/2937/5874、权威久单K79，另global名单中分配给久单的人数／命中／份额。共同H05 long=cluster1，12330/90，不按新群编号。
- 先保留逐seed原表。信息效应：同split/family/seed的full-base；模型效应：同split/info下各家族对WLR的配对差；信息×模型交互：(full-base)_model-(full-base)_WLR。native类别CB仅桥接full141编码CB的同split/seed，不混充完整2×家族主矩阵。
- 对每split先算三seed均值、SD、min/max和三seed差方向；确定性LR n=1，SD=NaN。再在5个split汇总配对差min/median/max、win/tie/loss及胜出比例，分母固定5，平局不删。loss improvement=-delta，AP/AUC/hits improvement=+delta；连续指标平局容差1e-12，hits为精确差。它们是描述性扰动稳定性，不做独立binomial显著性。
- 名单稳定性分别报告同split跨seed、同seed跨split的global2937与long79 Jaccard、选择变更数、命中差和global久单名额差。相同命中不代表相同客户。所有无序pair仅生成一次，标明依赖结构。

## canonical固定分数配对bootstrap

canonical split=20261111；主ensemble=mean(calibrated_probability)，同一信息档／模型的三seed按两个客户键一对一对齐，WLR一份。不得用mean(LL)冒充LL(mean probability)。保留mean raw-logit诊断在独立表。

全体和久单分别在自身客户经验分布中做2000次配对客户重采样（全体N29368；久单N12330），种子分别2026111201／2026111202。每replicate对所有模型使用同一multinomial客户复制次数。每次重新在带复制的伪客户池中排固定K2937或79；复制的同一客户可占多个名额，边界可只取部分复制。实现用固定score次序与累计复制数精确得到重排结果，不把它当真实联系人去重后的名单。打平继续使用客户键，AP/AUC按概率同分组处理，不以客户键人为拆AP ties。

同一scope的proper loss、AP/AUC、hits/precision/recall与配对差使用同一组重采样计数，保存每replicate。全体bootstrap额外保存global名单中的久单名额／命中。主对照为weightedLR-base8的同canonical概率ensemble，信息对照和native桥接在预定contrast表另列。区间采用2.5/97.5百分位；无多重比较校正，只是固定score条件区间，不包含重训、校准拟合不确定性、重叠split探索或时间漂移。

可附原固定名单的事件占比／损失诊断，但不能把“保持真实唯一名单不动、重采样其标签”与“重新排复制池K”混为同一估计对象，也不把这些离线区间当营销干预效果。任务当前指定的是前述重新排名的客户bootstrap。

## 交付与验收

根在任何新结果前增加unweightedLR的两信息档×5split共10拟合，现主矩阵6家族加nativeCB共155个监督模型，AE预训练30次另计。统计必须单列weighted↔unweighted LR的同split／同信息对照，以区分类权重影响；不能将其新增当根据Jan扩搜。两种LR的确定性各仅算1run。

根级protocol-clarification.md作为只增补、不覆盖的分数语义补充纳入binding SHA：主要单run与ensemble都用calibrated probability；raw sigmoid/prior为独立诊断，另核logit/rawp/calp真实名单变化。nativeCatBoost与encodedCatBoost桥接称“编码及缺失处理包”，包含missing flags、median、数值log/scale及类别表示差，不能单独归为类别编码因果效应。

独立源码、规范化schema／manifest、全部单运行及配对CSV、三seed→五split描述表、canonical逐人ensemble私有分数、bootstrap逐replicate和区间、Jaccard、PNG/SVG与局部核验。读回只复算不训练；用小型已知复制样本对照显式展开客户池／sklearn，验证bootstrap边界、AP/AUC ties和共同计数。schema／结果未到时只报骨架完成，不声称统计完成或正式采用。
