# 结果前共享源码与数学核查

结论：当前prepare_shared.py与eval_harness.py满足共同矩阵、fit-only预处理与单调Platt定义。此审查未读取任何零星模型记录或score NPZ，不训练真实模型、不bootstrap。raw策略语义细节已由根protocol-clarification.md明确，主单run与ensemble统一校准概率，addendum SHA绑定。

Platt目标是sum(logaddexp(0,a*z+b)-y*(a*z+b))+.5*a²/1e6。导数为sum((sigmoid-y)*z)+a/1e6及sum(sigmoid-y)，b不罚，Hessian半正定；a>=1e-6保证数学正斜率。当前θ-P(θ-grad)梯度映射正确：在下界且grad_a>=0时映射0，grad_a<0仍保留下降证据。active_lower_bound只是容差标签，projected_gradient_inf独立记录；success／请求tol不是梯度达标证明。独立公式有限差分最大误差5.10e-9，四个边界／内点投影案例通过；无真实cal拟合。

数学单调不保证浮点expit不生ties，因此完整结果阶段另核logit/raw_probability/calibrated真实名单与AP ties。harness raw容量按raw概率，metadata logit-vs-cal有不同参照；补充协议已区分，统计不混接规则。

五split独立共享审计：总宽808/813/817/813/812；原8均34列；所有额外missing与last_customer_state等代理列均不在base mask。显式CSR乘mask再eliminate_zeros后额外NNZ全0，完整宽度／六视图不变。canonical实际load_split与显式mask逐元素相同。独立fit-only StandardScaler(log1p原7数值)+state无rare OHE重算fit/cal/Jan原8子矩阵，最大差4.36e-12。

bounded H02双键、标签及原8值与shared原表逐项一致，权威H05训练／Jan群逐键一致。五split索引重新生成并核完整互斥分区，fit16928/169、cal4232/42、Jan29368/230、久单12330/90。完整支持／维数见shared-support-audit.csv与shared-matrix-audit.csv。上游字段时点限制继续承接，此审查不认证原字段绝无回写。

零输入分支仍可学常量bias，AE零占位重建／额外20epoch／门初始.5缩放属于模型包已知限制，没有声称已移除或已完成因果消融。nativeCB桥接也含missing、median、log/scale，不能只归类别编码。

shared-source-audit.json只认证数学和共同输入；adapter-binding.json的BOUND_WAITING_ROOT_RUN_STATS不是155模型／真实统计验收完成。
