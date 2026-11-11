# P4A 独立交叉审查

审查日期2026-11-11。审查者未参与P4A撰写或训练；先顺读 `group-learning/README.md`、`plan.md`，再核代码与private原始分数。P4A本身未重训；后续根代理专门授权的单项数值收敛诊断独立冻结、独立保存，不改原矩阵或选择赢家。

结论：P4A的fit/cal隔离、权威久单切片、16模型回放、64行概率及224行容量计算通过独立复算，核心负结果表述适度。发现1项整合前必须补清的跨模块基线说明缺口（P2），不是本模块数据泄漏或算错。主文P4当前仍标“冻结矩阵执行与核验中”，未把未完成状态误判为错误。

## F1／P2：共同客户不等于共同已求解的LR基线，跨模块必须带优化停止口径

位置：`group-learning/README.md:7-9` 的matched／共同口径；`objectives/README.md:13-14` 的47命中参照；主文 `E:/app-data/codex/scratchpad/is6400-round3-20261111/git-release/docs/team/validation-execution.md:82` 合并P4结果时适用。对应代码为 `group-learning/run_group_learning.py:71-95` 与 `objectives/run_objectives.py:20`、其LR拟合部分；下述不是原件或群机制错误。

P4A/B的fit客户集合、fit/cal索引和实际fit顺序相同，fit/cal/Jan全部34维输入矩阵逐元素完全相同，最大差0；C也都是1。但P4A用sum BCE目标与很严格的自定义L-BFGS-B停止设置，P4B用sklearn默认 `tol=1e-4`，该阈值检查的是均值目标梯度。因此P4B默认LR的“已结束”不能当成与P4A相同精度的凸最优解。

|同一sum目标评估|P4A unweighted|P4B默认unweighted|P4A balanced|P4B默认balanced|
|---|---:|---:|---:|---:|
|sum objective|921.298745182|922.161852205|11081.291632290|11081.430447463|
|sum梯度最大值|0.0000880165|1.4725427893|0.0050454165|1.4301939604|
|mean梯度最大值|5.20e-9|8.70e-5|2.98e-7|8.45e-5|
|迭代数|107|21|410|104|
|Jan K2937命中|44|47|43|42|

unweighted的系数最大差0.340984，Jan最大概率差0.0303453，Top10%选择状态不同410个客户；balanced分别为0.138471、0.0283676、30个客户。这不是机器最后几位浮点噪声。也不是不同预处理／客户／C造成的模型差。

本机安装源码 `D:/anaconda3/Lib/site-packages/sklearn/linear_model/_logistic.py:355-367,451-466` 明确在mean目标中使用 `l2_reg_strength=1/(C*sw_sum)` 和 `gtol=tol`。乘回sw_sum后与P4A的 `sum BCE + .5||beta||²` 是同一C1目标，而停止阈值不是同一尺度；sklearn默认mean梯度8.70e-5确实已经满足1e-4。这里同时有不同初值／线搜索设置，不能只看参数名“lbfgs”就说逐人相同。

根代理随后授权的独立单项诊断见 [numerical-convergence-audit/plan.md](../numerical-convergence-audit/plan.md)、[verification.json](../numerical-convergence-audit/verification.json)：只新增一次相同fitX/y、相同C1的sklearn未加权LR，`tol=1e-10,max_iter=2000`，没有依据Jan选配置。130iter后sum目标921.298745177，与P4A差4.87e-9；系数最大差3.99e-5，Jan概率最大差2.18e-6，Top10%名单与P4A完全相同，44命中。与旧默认P4B仍差410键／47命中。这个受控诊断足以将主要差异归因求解停止精度，而不是群机制。诊断请求tol1e-10不等于实测已达该梯度阈值：实测mean梯度2.02e-8，故只称“近同解”，不称严格KKT认证。

影响与所需修复：P4A内部同求解器对照有效，P4B原冻结结果仍应原样保留；合并表与主文必须给基线区分 `P4A严格sum求解`／`P4B默认tol`，说明“同fit、同矩阵、同C，优化停止精度不同”。不能把focal／采样／群分支相对跨模块44或47的差自动当组件因果。将这项数值诊断单列即可，无需重开所有候选。修复后只复核这段文档和相关对照标题，不重复训练或重审全篇。

## 已独立核实的范围

### 客户、表示与群统计隔离

- 重新调用bounded read_dev，原始开发行数50528；Oct21160/211，fit16928/169，cal4232/42，Jan29368/230。重新生成split与保存索引逐元素相同。
- P4A/B fit有序键CSV SHA256为 `7cbabe7b6543fd0e05daf4ab94bb9355d48be7ca6cd76d46ab11fa10914b028d`，cal有序键为 `2e96521358e596074e462139937a72df32ba89a0a0aec2d3eef238ef3bbdfbe3`。本哈希是带表头 `customer_unique_id,snapshot_date`、UTF-8/LF CSV的有序字节。根级 `cross-module-split-audit.json` 的统一sorted-fit哈希为 `037940a31f4faca2a82b84c59e72a890ff021cfbde14a9bd443973121ff028b9`；两种哈希口径不同，不混用。
- original8 scaler均值与仅fit的log1p列均值一致；OHE类别只来自fit。保存fit/cal/Jan数组与变换重放逐元素相同，P4A与P4B对应数组也全部逐元素相同。RFM群变换／群模型代码只在fit调用fit，cal／Jan只transform与predict。
- 独立重算hard3、hard_geometry、soft_bic全部fit/cal/Jan门控，与保存权重逐元素一致；相关初始化只用fit的X/y与fit权重，重算最大差分别4.93e-16、1.84e-16、1.73e-17。没有把cal/Jan标签纳入相关统计。
- KMeans silhouette只用训练侧固定2000人；GMM BIC只用fit。K2与GMM搜索上界K8的有限意义在README已说明，未冒称监督最优群数或真实群数。

### 内部群号与权威H05久单

不仅核人数，还将 `private/jan-keys-outcomes.csv` 的cluster_id按两个键与权威 `is6400-h05-january-handoff-20261110/validation_clusters.csv` 逐人合并，全部完全一致。容量代码 `run_group_learning.py:288-291` 使用该权威 `cluster_id==1`，固定12330人／90正例、群内取79，正确。

fit-only新KMeans K3的Jan内部群号与H05不是同一标签，且因fit范围变化并非完全相同分区：

|新hard3内部群|权威H05 0|权威H05 1（久单）|权威H05 2|
|---|---:|---:|---:|
|0|0|0|703|
|1|16297|34|0|
|2|38|12296|0|

所以内部群2只能说“主要为久单”，不能直接改用它代替共同久单；本次代码没有这样做。README已正确将训练门控群统计与H05评估切片分开。

### 模型回放、主要表与校准对应

没有依赖作者PASS代替自己的核验。独立从保存的8组线性参数、6个torch state_dict、先验／常数规则重建全部16 score变体的cal与Jan logit；再从保存Platt系数重算概率。所有模型的logit最大差均为0；复算64行LL/Brier/AP/AUC，最大差9.89e-17；复算224行5/10/20%与共同久单79容量，整数命中全部相同。模型回放证据足够支持“这些保存模型确实产生了这些分数”，不支持未来时间泛化或自动模型采用。

关键Jan原概率／排序复算如下，包含要求的unweighted、corrinit与identity/ReLU全部三个seed；其他冻结候选也在完整64/224行中核过。

|候选|raw LL|Platt LL|raw AP|K2937命中|权威久单79命中|
|---|---:|---:|---:|---:|---:|
|lr_unweighted|0.045286891|0.045462281|0.028528608|44|1|
|hard3_delta_corr|0.045405724|0.045465512|0.027663736|40|0|
|hard3_delta_zero|0.045405720|0.045465510|0.027663721|40|0|
|identity2026|0.045332241|0.045452882|0.029989135|43|0|
|identity2027|0.045297789|0.045449259|0.028590491|45|0|
|identity2028|0.045253742|0.045376127|0.028107019|46|0|
|ReLU2026|0.045286650|0.045455750|0.028573757|42|0|
|ReLU2027|0.045240613|0.045447204|0.028646679|41|0|
|ReLU2028|0.045218332|0.045385050|0.029127717|42|0|

Platt的输入是对应模型的Octcal原logit，标签仅Octcal42个正例；所有斜率为正，raw／Platt排名指标与容量命中一致，不能把校准后概率变化当新增名单收益。balanced_prior以fit基率加logit偏移，复用balanced模型，没有偷偷增加一轮训练。Octcal Platt再代入读数在报告中明确披露，未称独立泛化。

### 初始化与收敛解释

相关／零初值的可学习delta使用相同固定门控、同一线性logit、同一正L2凸目标；相关初值不改变目标，不能作为新信息解释。保存目标差1.61e-8，参数最大差3.70e-5，Jan概率最大差4.85e-6，容量同为40/0，符合“近同数值解、无已证收益”的解释。

作者没有把scipy success写成所有候选达gtol：README明确其停止原因为ftol，model_fit列出了实际梯度，balanced约0.0050。该披露保留即可；不必为某个理想容差自动加轮。identity与ReLU均643参数、50epoch、同batch512/Adam预算、同种子初始化规则；identity在固定门控内为线性残差、其参数因子化本身不是凸问题，README未宣称全局收敛。ReLU raw LL更低但命中更低、Platt均值近同的结论由表支持，不应升级为稳定改进或普遍失败。

## 主文与完成边界

已顺读 `git-release/docs/team/validation-execution.md`。其P4阶段仍标执行／核验中，P5与正式采用均未确定，并明确同80%划分参照不能与旧full-Oct50命中作单组件归因；这些边界正确。当前不因主文尚未收齐P4细表判错，只要求整合时落实F1的优化器／停止精度标签。P4A自身只说本地冻结实验完成，未冒称整研究、真正未见时间验证或三端同步完成。

本次审查未改P4A/B代码、模型或旧结果，未Git／看板／外部写入；April读取0。可复算审查代码与完整中间证据在 `E:/app-data/codex/scratchpad/is6400-validation-20261111/cross-review-group-learning/`，永久数值诊断另存 `numerical-convergence-audit/`。后续仅定向复核F1文档整合，不重复全矩阵审查。
