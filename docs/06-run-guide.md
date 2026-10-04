# 从下载到运行：零基础操作指南

## 1. 只想阅读，不想运行

直接打开README、术语表、结果说明即可。PPT文件在 `slides/olist-repurchase-briefing.pptx`，点击文件后选择下载。Markdown讲稿可以在GitHub网页直接阅读。

GitHub不直接展示大型ZIP里的CSV，但本仓库已经包含完整官方数据，不需要Kaggle账号。仓库首页 Code → Download ZIP 下载全部文件，解压后保留原目录结构。

## 2. 准备Python

已验证环境是Python 3.12.3；建议用Python 3.11或3.12。没有环境的同学可以安装自己的Python或Anaconda，不要复制别人的本机路径。

Windows：进入项目文件夹，在地址栏输入 `powershell` 打开终端。先检查当前位置：

```powershell
Get-Location
Get-ChildItem
python --version
```

应该能看到README.md、requirements.txt和scripts目录。如果 `python` 无法识别，先打开Anaconda Prompt，或指定你实际安装的解释器路径；不要盲目照抄某位组员的盘符。

## 3. 建立独立环境

在项目根目录运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

第一行创建只供这个项目使用的环境；第二行安装所需库。`-m` 表示用指定Python运行某个模块。requirements.txt记录库的版本，帮助大家复现相同结果。

以下Windows命令全部使用 `.venv\Scripts\python.exe`，不需要修改PowerShell执行策略或激活环境。macOS/Linux对应 `.venv/bin/python`。

安装失败时先检查Python版本和网络，不要未经讨论随意升级所有库；模型结果可能随软件版本变化。

## 4. 解压并检查原始数据

```powershell
.\.venv\Scripts\python.exe scripts/extract_data.py
```

脚本检查ZIP和每个CSV的SHA-256，输出9个OK，然后在 `data/raw/` 出现9个文件。

SHA-256相当于文件指纹，只证明字节与保存的原件相同，不保证每条业务记录没有异常。若已有CSV被改动，脚本会停止，不会覆盖；先保留修改副本并查明原因。

原始压缩包约42.65 MiB，解压约120.34 MiB；安装科学计算库还会占用更多空间。

## 5. 阅读并运行入门Notebook

```powershell
.\.venv\Scripts\python.exe -m jupyterlab
```

浏览器打开后，进入 `notebooks/01-data-guide.ipynb`。Notebook由文字格和代码格组成：选中一格按 Shift+Enter，会运行本格并移动到下一格。

第一次建议顺着读，不要跳着运行。变量只有执行过定义它的代码才存在。想检验完整流程，选择 Kernel → Restart Kernel and Run All Cells。

Notebook里的数据路径自动识别项目根目录。若找不到 `data/raw`，先确认已执行解压脚本，再确认启动位置。Notebook只做数据认识，不训练分类模型。

## 6. 复现分类实验

必须按顺序：

```powershell
.\.venv\Scripts\python.exe scripts/run_catboost.py
.\.venv\Scripts\python.exe scripts/compare_models.py
```

第一个命令准备客户快照、尝试三组CatBoost设置并保存结果。第二个命令复用相同快照，补充逻辑回归、随机森林和HistGradientBoosting。

运行时会显示COHORTS、VALIDATION/TRIAL和TEST结果。耗时取决于电脑；本项目默认限制两个计算线程，不需要GPU。

输出在 `outputs/classification/`，包括结果JSON、比较CSV及匿名客户分数。`results/classification/` 是已经审核的历史记录，不会被重跑覆盖。

同版本、同种子通常应接近已记录结果；小数差异先核环境与输入哈希，不能为了“对上数字”修改数据。若在另一个版本运行，应记录版本与差异。

## 7. 复现分群实验

```powershell
.\.venv\Scripts\python.exe scripts/run_segmentation.py
```

结果在 `outputs/segmentation/`。它比较简单规则、R/M聚类、RFM聚类，并含一个事后诊断规则。该实验的客户资格和分类实验不同，详见结果说明。

绘图需要中文字体。Windows通常有Microsoft YaHei；Linux可安装Noto Sans CJK或使用英文图标签。字体缺失不一定影响数值计算，但可能让图中文字显示方框。

## 8. 常见报错

| 现象 | 先检查什么 |
|---|---|
| `ModuleNotFoundError` | 是否用安装依赖的同一个Python运行 |
| `FileNotFoundError` | 是否在项目目录、是否解压了data |
| CSV哈希不一致 | 原件被修改或下载不完整；不要强制跳过 |
| compare_models找不到results.json | 先运行run_catboost.py |
| Notebook报NameError | 前面的定义格是否执行过；从空内核顺序运行 |
| 内存不足 | 先只运行分类实验；不要同时加载多份地理大表 |
| 图里中文方框 | 检查中文字体，数值结果另行核对 |

## 9. 运行成功不等于项目已完成

成功运行只表示脚本执行完。请继续回答：标签是什么？每个输入当时是否可知？名单精确率与召回率的分母是什么？有没有对最终测试反复调参？聚类反馈是否真的做过？不能把输出文件存在当成业务效果成立。
