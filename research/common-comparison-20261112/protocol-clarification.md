# 统一分数语义补充

2026-11-12，独立源码核查时补充。原冻结task_plan的“主策略raw logit”与随后明确的“主ensemble均值校准概率”有语义歧义；不改原文件哈希，不覆盖任何已运行模型或记录。

本轮实际eval_harness从开始就分别保存raw、calibrated、weighted prior三个variant。统一**主要比较**使用calibrated probability：单run指标/名单取该variant，三seed ensemble取其概率均值，概率误差、AP/AUC与名单使用同一score。这是在任何模型结果前明确的ensemble规则在单run面板上的一致应用，不按结果择分数。

raw sigmoid probability及weighted prior仅作独立诊断。当前harness的raw容量确实按expit(raw_logit)计算；metadata的raw-versus-cal选择差则以raw_logit为参照。数学上的单调变换在有限精度下可能产生ties，统计审查将独立保留raw_logit/raw_probability/calibrated三个排序间的实际选择差，不能以a>0推定逐人名单必定相同。AP按同一概率的ties处理，不用客户键拆AP ties。

不修改学习器、信息掩码、拆分、epoch、校准目标/约束、主ensemble或bootstrap配置；没有新增训练，也不根据零星一月成绩调整。统计adapter在完整155格前冻结并在RUN_STATS门禁后执行。完整结果不删除不利variant。
