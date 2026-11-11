# Q01–Q18 逐步验证的可复算材料

用户已于 2026-11-11 明确授权开测。当前阶段与结论见 [执行进度](../../docs/team/validation-execution.md)，[质疑表](../../docs/team/research-questions.md) 保留原始问题。

- [P1 概率、分类与策略](probability/README.md)
- [P2 全字段、地区和距离](features/README.md)
- [P3 异常检测与分群结构](structure/README.md)
- [P4A 群统计权重与共享支路](group-learning/README.md) · [P4B 不平衡与目标函数](objectives/README.md)
- [P4C 注意力、论文启发表征和深度分群](representations/README.md)
- [关键 LR 数值控制](convergence/README.md) · [跨矩阵停止精度诊断](numerical-convergence-audit/README.md) · [群成员后端优化控制](cluster-head-control/README.md)
- [当前问题状态 JSON](question-register.json)

本目录仅公开已核聚合数据、配置、代码与 PNG/SVG。逐人键/分数、模型、训练矩阵、错误轮和全量逐阈值曲线保留本地，不通过递归上传发布。原运行回执包含这些私有产物的哈希；公开 evidence-manifest.json 只列本目录实际发布字节。文本统一 LF，因此与源机 CRLF 字节哈希可能不同。

代码是原始执行记录，依赖项目内已授权 H02/H05 及历史结果目录，含本机路径；它不是独立下载安装即跑的公共数据包。聚合 CSV 与 SVG/PNG 可直接阅读和复用；每阶段 README 说明输入、边界和核验。数据无条件重建及模型下载未作为本批发布成果宣称。

训练/校准使用十月，一月是已见开发比较，四月本轮不新评分或解析快照/标签。所有客户评分，K=2937、久单群内独立 K=79 仅作策略读数。多种子不是多个未见时期；固定分数 bootstrap 不涵盖重训、探索选择和时间漂移。
