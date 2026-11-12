# 经典模型统一矩阵：冻结执行范围

2026-11-12，承接根 task_plan.md。仅 classical 与对应 scratch 写入；不安装、外发、Git、看板，不解析或评分 April。

## 矩阵

只读根提供的共享五划分（20261111..20261115）、float64全宽矩阵和标签。不得自行split或重新编码。base8新增列已经由根共享入口置0，full141完整X；同档矩阵与其他模型相同。根提供native raw拆分作桥接，不自行改变客户范围。

- WLR：两信息档×五划分=10，C1、balanced、lbfgs、tol1e-10、max_iter5000、CPU2。
- 未加权LR桥接：两信息档×五划分=10，与WLR同C/tol/maxiter/solver，仅class_weight=None，区分类别权重与自然BCE方法。
- 编码CatBoost：两档×五划分×seed2026/2027/2028=30，depth3、iterations300、lr.03、l2_leaf_reg10、无classweight、CPU2、无earlystop。
- 原生类别CatBoost：full141×五划分×三seed=15，同参数；类别缺失__MISSING__，数值仅fitmedian，分类列表与原141列按根共享schema。不将原生编码格和编码主格混作同一X。

共65个实际模型（根于任何新结果产生前增加未加权LR桥接）。代码/配置在正式新结果前冻结SHA；共享接口到位只适配loader，并在运行前重新冻结最终源码。全部seed与负结果保留，不据Jan调参/删seed。

## 训练记录与评分

LR独立重算 sum_i(weight_i*BCE_i)+0.5*||coef||²/C（intercept不罚），保存完整系数/截距梯度、inf/L2范数及规范化梯度；记录n_iter、warnings和真实SciPy终止message/gtol/ftol/options，不能用“无warning”代表达到梯度tol。WLR balanced权重为N/(2*Nclass)，ULR权重均为1。报告求解器内部加权均值梯度与sum目标梯度的尺度差别。

CB保存每轮learn Logloss、完整参数、300轮实际迭代与耗时。不用cal/Jan作为eval_set，不earlystop。模型、native变换、sourcehash、fit/cal/Jan float64 raw logits保存在private；公共文件只有聚合记录和脚本，不含逐人。

根eval_harness统一做校准/概率/指标，驱动不自行拟合校准器或替换排名规则。共同久单权威cluster1=12330/90、K79；原全Oct50存档不覆盖，也不与本轮fit80成绩直接当模型作用。

## 小试与估时

共享schema/哈希确认后，先canonical split20261111的WLR两档、编码CB full141 seed2026、nativeCB full141 seed2026按正式完整参数计时（4个正式格，后续直接复用保存模型，不重复训练）。只汇报训练/保存诊断与预算估计，不根据Jan成绩改参数。随后跑剩余61格。

预估以实测秒数外推，未知耗时不写0。任何接口冲突/输入维度或哈希漂移先停相关项回根；可独立完成的记录继续。最后逐模型重载并核fit/cal/Jan logits，源输入hash重核，README明确执行依赖与本批收敛/失败边界。
