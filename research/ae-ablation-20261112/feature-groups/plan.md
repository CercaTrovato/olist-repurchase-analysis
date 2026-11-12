# 六信息块条件依赖实验

固定父级 task_plan.md，六块按 data-manifest.json view_order 和 split dims 整段置零，每次从完整未改 full141 复制，不删列、分支或维数。fit/cal/Jan 同段置零，其余元素完全相同。每块×五 split×三 seed＝90 个从头 AE20+BCE50；旧 full AE15 格只读配对。

直接复用父 neural_models.py，float32、CPU2、hidden16、Adam.001、预训 batch256、监督 batch512、dropout0；从同 seed 初始化，分别核旧 full AE encoder/head 初始化、预训/监督批次序列 hash。重建目标即遮蔽后的输入。保存 float64 logits，拟合仅 fit，cal 仅拟合父正斜率 Platt。

先生成源与输入冻结、fit-only 一轮预训＋一轮监督计时小试，不输出 cal/Jan 评分；等根 READY/candidate-freeze 后执行正式固定矩阵。保留失败，不依据 Jan 改字段/参数。每格保存模型、预训模型、曲线、分数、metadata，并由另一个脚本重载模型独立前向核对 logits 和指标。

逐人分数、模型、原始曲线为 private。公开只无身份聚合、源码、mask nnz/hash 与训练诊断 PNG/SVG。零分支仍可学常量；其余块有语义代理；置零重建目标更易。本实验只能解释条件于其余块的表示依赖/冗余补偿，不能当原始信息因果重要性，六贡献不能相加。不是正式小组采用。
