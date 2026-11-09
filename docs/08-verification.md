# 发布前验证记录

这是 2026-10-04 的历史验证记录。当前团队首轮的结果、按群复算与文件缺口见 [首轮交付结果](team/evidence/README.md)。

## 已执行

- 从随仓库提供的ZIP解压9个CSV，CRC与逐文件SHA-256匹配。
- 在独立仓库目录中执行 `scripts/run_catboost.py`、`scripts/compare_models.py` 与 `scripts/run_segmentation.py`；使用相对路径，没有读取维护者的课程目录。
- 分类四模型和简单规则的四个指标，与保留的初次探索结果一致；分群指标亦一致。
- 两份Notebook从独立空内核运行：数据入门16个代码格、复购指标讲解5个代码格，均无错误输出。
- Markdown本地链接、Python语法、指标分母计算及五页PPT压缩包结构检查通过。
- PPT沿用已在Microsoft PowerPoint逐页查看的五页版本；公开副本仅清理作者元数据，不改幻灯片和讲稿内容。

## 环境与边界

实际运行使用Windows、Python3.12.3、numpy1.26.4、pandas2.3.3、scikit-learn1.5.1、CatBoost1.2.8、matplotlib3.9.2。没有另建一个空操作系统或全新虚拟环境安装所有依赖，也未在macOS/Linux重新验证。

没有独立真人零基础试读评分；没有完整聚类反馈实验；没有真实营销干预；没有确认性的多时间测试或置信区间。本页记录的数字属于截至 2026-10-04 的探索实验。

## 怎样自行检查

在根目录运行 `python scripts/verify_release.py`，检查链接、数据指纹和记录的指标算术。它不会训练模型。重新训练按运行指南执行；不要直接替换历史results，先比较outputs并记录差异。
