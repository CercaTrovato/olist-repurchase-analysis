# 第三轮图表和公开汇总

[研究结果](../../docs/team/round-3-results.md) · [图表使用指南](../../docs/team/visual-assets.md) · [成员任务](../../docs/team/round-3/README.md)

本目录提供13幅PNG与SVG、逐图汇总、第三轮公开聚合数据和三份绘图脚本。图内为英文标签，素材索引配中文图注，便于PPT与报告复用。

## 重新生成图表

在本目录运行以下命令。环境使用 Python、numpy、pandas、matplotlib，具体实跑版本为 numpy 1.26.4、pandas 2.3.3、matplotlib 3.9.2。

```powershell
python render_figures.py
python render_additional_figures.py
python render_new_figures.py
```

三份脚本顺序读取本目录的公开汇总，写入 figures/、chart-data/ 与 figure-index.json。SVG 保留文本，PNG为240dpi。模型训练与逐人数据在组内的版本化研究包保存，公开绘图只依赖这里的聚合数据。

## 证据范围

- baselines 为十月训练、一月验证的六方法对照，条件bootstrap包含固定分数下的客户重采样，不能用来证明新时期泛化。
- features 为配送/评价四版，字段先冻结再评分，预测日之后的事件被排除，缺失单列。
- time-and-profiles 的覆盖、群画像和试验规划分别解释为日期审计、历史描述及设计假设。
- 四月原有回测为已见补充结果。本批不使用其反馈选模型。
- 实际组员交件状态在项目当前进度页维护，本地影子结果独立列出。
