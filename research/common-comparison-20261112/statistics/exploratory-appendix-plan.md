# 探索性完整同信息模型包配对附表

2026-11-12，根在首轮完整摘要后明确要求补齐gate-vs-mean、AE-vs-mean两个必要参照；它们是初始引入mean参照的研究目的，但原统计contrast清单没有明列这些单项CI。因此原冻结表原样保留，本附表明确为结果后追加的探索性完整配对，不伪称事前单项confirmatory。

完整生成base8六家族全部15对、full141六家族加nativeCatBoost全部21对，而不是只选择结果有利的对。相同信息档、相同split与seed配对；确定性LR重复用同一模型作参照，不能把重复参照当独立样本。native涉及编码／缺失／数值处理包，不是相同编码单因素。

canonical全部CI直接在既存的相同scope／rep_id bootstrap结果上相减；不重采样、不训练、不改任何模型／阈值／主规则。完整按5split先seed聚合的方向表另存；不做独立binomial或未来时间推断。原canonical-contrasts.json及canonical-paired-bootstrap-intervals.csv不修改。AE额外预算／门初始缩放继续限制机制归因，正式消融仍后置。
