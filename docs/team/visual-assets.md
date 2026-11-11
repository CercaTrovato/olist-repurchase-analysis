# PPT 与报告图表素材

[当前结果](round-3-results.md) · [第三轮成员任务](round-3/README.md) · [绘图源码与数据](../../research/round3/README.md)

2026-11-11。共13幅图，每幅提供PNG、可编辑SVG、数据和中文读法。默认图内英文，适合英文展示。LR为逻辑回归，GCN为图卷积模型。K代表名单人数。

## 建议用于主线的图

07说明强基线，09说明小差异的不确定性，03区分名单覆盖与群内排名，11呈现本轮新增信息结果，10交代评价边界。12与13适合业务建议，其他图作研究扩展。

![六方法比较](../../research/round3/figures/07-six-method-comparison.png)

![新增字段消融](../../research/round3/figures/11-new-information-ablation.png)

## 全部素材

### 01-group-size-and-rates

一月分群规模与复购率。近期单单16,335人、久单12,330人、多单703人。多单群复购率较高。单单指历史半年内只买一次。

[PNG](../../research/round3/figures/01-group-size-and-rates.png) · [SVG](../../research/round3/figures/01-group-size-and-rates.svg) · [数据](../../research/round3/chart-data/01-groups.csv)

### 02-fields-by-weighting

一月相同2,937个名额，三字段加权51→48，八字段加权46→50。加权收益取决于输入组合。

[PNG](../../research/round3/figures/02-fields-by-weighting.png) · [SVG](../../research/round3/figures/02-fields-by-weighting.svg) · [数据](../../research/round3/chart-data/02-weighting.csv)

### 03-global-versus-fixed-group

加入群号全局50→52，但固定久单79名额仍命中2人。两项交互和金额单项交互都降为全局42、固定久单0。

[PNG](../../research/round3/figures/03-global-versus-fixed-group.png) · [SVG](../../research/round3/figures/03-global-versus-fixed-group.svg) · [数据](../../research/round3/chart-data/03-h05-totals.csv)

### 04-graph-design-grid

格内为三种子命中中位数，括号为最小—最大。所有结果来自同一已见一月，不是三期验证。

[PNG](../../research/round3/figures/04-graph-design-grid.png) · [SVG](../../research/round3/figures/04-graph-design-grid.svg) · [数据](../../research/round3/chart-data/04-graph-grid.csv)

### 05-gcn-residual-contrast

同卖家图、两层8维。加残差与对比后的全局命中46/48/44，久单0/1/0。点是随机种子，不能解释为时间稳定性。

[PNG](../../research/round3/figures/05-gcn-residual-contrast.png) · [SVG](../../research/round3/figures/05-gcn-residual-contrast.svg) · [数据](../../research/round3/chart-data/05-residual.csv)

### 06-feature-evidence-shift

久单群家具装饰候选在十月差异较大，到一月差距收窄。历史比例用于提出特征假设，模型增益另验。

[PNG](../../research/round3/figures/06-feature-evidence-shift.png) · [SVG](../../research/round3/figures/06-feature-evidence-shift.svg) · [数据](../../research/round3/chart-data/06-category-shift.csv)

### 07-six-method-comparison

一月同取2,937人，最近购买30，多单优先48，三字段51，原八字段46，加权50，加群号52。较高的单期分数仍需结合差异区间判断。

[PNG](../../research/round3/figures/07-six-method-comparison.png) · [SVG](../../research/round3/figures/07-six-method-comparison.svg) · [数据](../../research/round3/chart-data/07-baseline-10pct.csv)

### 08-capacity-sensitivity

统一比较5%、10%、20%容量，候选排序随名额改变。连线辅助读取三个已计算容量点。

[PNG](../../research/round3/figures/08-capacity-sensitivity.png) · [SVG](../../research/round3/figures/08-capacity-sensitivity.svg) · [数据](../../research/round3/chart-data/../data/baselines/january-metrics.csv)

### 09-conditional-uncertainty

点为观察到的命中差，线为2,000次配对客户重采样95%百分位区间。加权相对最近购买+20[7,34]，与另外三种强对照的区间均跨0。已拟合分数条件下的区间不包含重训或新时期的不确定性。

[PNG](../../research/round3/figures/09-conditional-uncertainty.png) · [SVG](../../research/round3/figures/09-conditional-uncertainty.svg) · [数据](../../research/round3/chart-data/09-bootstrap-differences.csv)

### 10-time-window-validity

候选日期的90天目标与已见一月/四月目标日历重叠。7月目标虽不重叠，但有25天超出源合格事件日期上界。日历重叠不是逐客户标签完全相同的证明，数据日期覆盖也不证明无漏采。

[PNG](../../research/round3/figures/10-time-window-validity.png) · [SVG](../../research/round3/figures/10-time-window-validity.svg) · [数据](../../research/round3/chart-data/10-time-windows.csv)

### 11-new-information-ablation

冻结两个新字段组后，一月全局原版50，配送46、评价45、组合46；久单固定79人分别2、2、1、1。组合版在全局给久单281个名额、命中4，与固定名额结果同时报告。

[PNG](../../research/round3/figures/11-new-information-ablation.png) · [SVG](../../research/round3/figures/11-new-information-ablation.svg) · [数据](../../research/round3/chart-data/11-new-field-results.csv)

### 12-content-theme-support

床品/卫浴/餐桌用品主题按十月全体历史支持人数选择。一月三群买过的客户为1558/16335、1355/12330、165/703，整体3078/29368。客户按类别去重，比例为历史支持。

[PNG](../../research/round3/figures/12-content-theme-support.png) · [SVG](../../research/round3/figures/12-content-theme-support.svg) · [数据](../../research/round3/chart-data/12-theme-support.csv)

### 13-content-trial-feasibility

假设控制率0.783%、双侧5%、80%功效，识别绝对+0.5个百分点约需每组6420人。历史主题支持池3078人只是联系资格损失前的上限。最小效应需由真实业务价值确定。

[PNG](../../research/round3/figures/13-content-trial-feasibility.png) · [SVG](../../research/round3/figures/13-content-trial-feasibility.svg) · [数据](../../research/round3/chart-data/13-trial-power-planning.csv)

## 使用时保留的说明

一月是已见开发验证，三种随机种子属于同一时期。09的区间条件于已拟合分数，没有重训，模型选择过程与时间泛化未包含。10标的是目标日历重叠与事件日期范围，不能直接解释为逐客户标签相同或源系统完整。13为未来试验设计假设，未执行。

所有图支持结论与限制一并展示。正式采用的模型版本、时间和理由由6号在统一比较后记录。
