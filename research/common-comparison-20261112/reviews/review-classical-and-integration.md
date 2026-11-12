# 经典实现与共同方案独立复核

审查者没有参与 `classical_engine.py`、`run_classical.py`、`prepare_shared.py` 或根 `eval_harness.py` 的实现。本次先读源码、冻结方案和分数语义补充，再用自己的脚本进行 NumPy 数值复算及保存模型抽核。**审查者撰写的 neural 不属于本次独审范围**，不以本报告认证神经实现或整个155格的最终科学结论。

结论：本次范围内未发现需修复的实质实现错漏。65个经典模型身份已齐，canonical保存模型、共享输入、目标/梯度和共同评价通过独立复算。实际停止、native桥接表示包、raw概率与logit的不同语义必须继续保留；本报告不判断赢家，也不替代随后完整矩阵统计。

## 实际检查量

|检查|实际范围与结果|
|---|---|
|经典模型身份|65个身份齐全且唯一：WLR10、ULR10、encodedCB30、nativeCB15；五split、两信息档和三seed配置吻合|
|来源与元数据|全65的metadata哈希、split/信息档/家族/seed、fit键SHA、共享文件SHA与当前manifest逐项吻合|
|H02原始口径|直接从ZIP各读前50,528行feature/label；只有Oct/Jan，组合键、y、state与shared raw逐键一致，原7数值最大差0；不读四月|
|共享五split|总宽808/813/817/813/812、base8恒34列；fit16928/169、cal4232/42且不交叉；median/数值scaler均值/类别字典及rare支持只由fit产生|
|canonical原8重算|以NumPy的fit均值/方差计算log1p原7数值标准化，并独立拼state独热；fit/cal/Jan与根保存子矩阵最大差均1.8644e-12|
|canonical保存模型|13个：WLR/ULR各两档共4，encodedCB两档三seed共6，nativeCB三seed共3；三期39个logit数组独立重放，最大绝对差7.1054e-15|
|canonical LR训练诊断|4个模型独立NumPy重算完整系数/bias梯度及求和目标，与保存gradient、metadata和真实optimizer fun一致|
|canonical校准|13个模型独立重算自然cal的Platt目标/梯度，三期raw/cal概率与根NPZ一致；WLR的prior保持独立诊断|
|共同指标与策略|独立复算280行Logloss/Brier/AP/AUC及112行容量/三群支持，全部与record一致|
|有限精度排序|canonical 13模型×global2937/long79共26组，分别核logit/raw probability/calibrated三种分数；本次抽核集合差均0，不推广为所有run必然如此|

以上不是复用作者 `verify_model` 或 `loss_gradient` 的输出作为独审：检查脚本没有导入经典引擎，也没有调用任何fit。LR预测由保存coef/bias和矩阵直接作NumPy乘加；CB只调用保存模型的原生推理接口；目标、梯度、概率损失和名额筛选另外实现。AP/AUC使用sklearn的同分组处理，名单才按固定客户键破平。

## fit/cal隔离和同值X

`run_classical` 只从共同loader读取split/矩阵；WLR/ULR的fit只接 `X_fit,y_fit`，encodedCB接同一份float64数组，没有另行变换、筛客户或混入cal。源代码未给CB传eval_set、earlystop或校准标签，固定300棵树；原生桥接也只接fit行及真实fit y。全65身份/source核对包含逐split原始文件哈希，canonical模型重放使用直接读取共享CSR并按已保存mask计算的数组，能重现训练时保存的三期分数。

共享lineage逐列绑定掩码。base8只含原8字段，其中7数值与state编码共34列，没有任何extra missing flag、`last_customer_state`或其他相关代理进入mask。canonical里full→base后的新增列全为0，保留列与full逐元素相同，六视图宽度未变。原8标准化/OHE的独立NumPy对照见上表。

数值median/scaler均值与类别字典对五split重新计算；没有根据cal/Jan拟合的证据。全结构字段仍承接P2静态维表/支付及回写时点假设，本次数值复算不把这些假设变成严格生产时点可恢复性认证。

## LR目标和真实终止

WLR权重独立核为 `N/(2*Nclass)`，ULR全1，C均1，bias不罚。复算目标为求和weighted BCE加 `0.5*||coef||²/C`；完整求和梯度再除权重和，才与求解器的weighted-mean gtol尺度对应。保存optimizer fun也等于该求和目标除权重和，不能把两种尺度直接混比。

|canonical模型|求和目标|求和梯度∞|weighted-mean梯度∞|实际迭代|
|---|---:|---:|---:|---:|
|WLR/base8|11081.291631|8.4112e-4|4.9688e-8|424|
|WLR/full141|5962.042360|2.2224e-3|1.3128e-7|1770|
|ULR/base8|921.298745|4.4472e-5|2.6271e-9|132|
|ULR/full141|789.874485|1.5030e-4|8.8790e-9|703|

20个LR的真实optimizer message均为 `CONVERGENCE: REL_REDUCTION_OF_F_<=_FACTR*EPSMCH`。虽然optimizer success全部为真、没有warning，**gtol1e-10实测达标为0/20**。这与源码保存的诊断一致：本批按相对函数变化停止，不是严格梯度阈值全部达成。审查不把它写成失败，也不把success改写成精确最优；不据此自动再调精度或扩搜索。

## Native CatBoost桥接

canonical native的141个原字段列序与共享raw完全一致。数值median由fit行独立重算，与保存的native preprocess一致；cal/Jan只沿用该median，类别缺失用 `__MISSING__`，没有新增标签编码或未来y进入X。三个native保存模型的三期预测可复现。

它与encodedCB并非相同X：native使用原始数值尺度、fit median、原生类别/类别缺失；encoded包使用log/scale、固定extra missing flags、rare OHE等。因此桥接差异是**编码、数值变换、缺失处理的整个表示包**，不能单独归因于类别编码。`explanation-draft.md`及统计schema/plan目前已作此限制，不需要把真实桥接强改成另一模型或重训。

## 校准主分数、诊断分数和ties

根harness从开始分别输出raw/calibrated，WLR另有prior；它为每个variant各自计算指标和容量，没有把raw的AP直接嫁接calibrated名单。主比较取calibrated的规则由 `protocol-clarification.md` 和统计adapter明确：单run用对应cal概率，canonical三seed用cal概率算术均值，以同一score作概率、排序和名单；mean(raw logit)只作另列诊断。

原冻结计划“raw logit主策略”与后续主概率规则之间的解释依赖这份补充，发布时应继续保留补充链接和版本，不把原计划的raw容量列改名成calibrated。实际harness的raw容量按expit(logit)排名，而metadata的raw-versus-cal差以logit为参照；补充已明确两者不同。

数学正斜率不等于有限精度下绝无新ties。独立抽核canonical的raw logit / raw probability / calibrated后，26组global/long选择集合未变；但这只认证本次抽核，不免除根统计对完整155模型的ties审计。AP/AUC仍按概率同分组，不按客户键人为拆成不同概率。cal校准后指标是再代入读数，不当作无偏泛化。

## 证据和范围边界

独立脚本：`E:/app-data/codex/scratchpad/is6400-common-comparison-20261112/classical-review/classical_audit.py`。机器回执为同目录 `receipt.json`；另有canonical replay/gradient/ties和all65 identity/stop四份CSV。脚本SHA256：`d7b68c10308288fd2e0c2e674786b3f4535d7fa3b44297de5c2b56f72d7cdff2`。

本次对全65核身份/source/停止元数据，对canonical13个做数值模型重放；**没有声称独立重放全部65模型**。没有重新从9张原始订单表构造141列，没有重训、没有执行真实bootstrap或读取神经模型作为独审。统计仍由另一个冻结流程完成，不因65经典模型齐全就宣称最终研究/正式采用已完成。没有Git/看板操作、外发或四月读取/新评分。
