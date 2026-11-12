# 本轮17幅统一比较图

2026-11-12。本批17对PNG/SVG，连同原40对共57对主素材。所有图已实际查看。

[本轮结果](common-candidate-comparison.md) · [全部图表索引](visual-assets.md)

## 01 · CB-fit-curves

CatBoost训练曲线，不作为一月泛化收益。

[PNG](../../research/common-comparison-20261112/classical/CB-fit-curves.png) · [SVG](../../research/common-comparison-20261112/classical/CB-fit-curves.svg) · [数据/源码入口](../../research/common-comparison-20261112/classical/README.md)

## 02 · LR-optimization

实际梯度和函数变化停止，程序success不等于达到请求gtol。

[PNG](../../research/common-comparison-20261112/classical/LR-optimization.png) · [SVG](../../research/common-comparison-20261112/classical/LR-optimization.svg) · [数据/源码入口](../../research/common-comparison-20261112/classical/README.md)

## 03 · coverage-versus-within-long79

全局名单给久单更多席位，与固定79人内挑得更准分开看。

[PNG](../../research/common-comparison-20261112/figures/coverage-versus-within-long79.png) · [SVG](../../research/common-comparison-20261112/figures/coverage-versus-within-long79.svg) · [数据/源码入口](../../research/common-comparison-20261112/statistics/canonical-ensemble-capacities.csv)

## 04 · ensemble-five-split-hits

同一概率融合规则跨五个重叠训练/校准划分；是训练扰动，不是五个月。

[PNG](../../research/common-comparison-20261112/figures/ensemble-five-split-hits.png) · [SVG](../../research/common-comparison-20261112/figures/ensemble-five-split-hits.svg) · [数据/源码入口](../../research/common-comparison-20261112/ensemble-five-split-results.csv)

## 05 · AE-reconstruction-curves

AE六视图重建；base8零目标更多，两个档的MSE不能直接当复购能力比较。

[PNG](../../research/common-comparison-20261112/neural/AE-reconstruction-curves.png) · [SVG](../../research/common-comparison-20261112/neural/AE-reconstruction-curves.svg) · [数据/源码入口](../../research/common-comparison-20261112/neural/README.md)

## 06 · fit-optimization-support

最终训练BCE与常数参照；范围为三seed而非CI。

[PNG](../../research/common-comparison-20261112/neural/fit-optimization-support.png) · [SVG](../../research/common-comparison-20261112/neural/fit-optimization-support.svg) · [数据/源码入口](../../research/common-comparison-20261112/neural/README.md)

## 07 · supervised-training-curves

全部神经监督曲线，固定50epoch未用一月早停。

[PNG](../../research/common-comparison-20261112/neural/supervised-training-curves.png) · [SVG](../../research/common-comparison-20261112/neural/supervised-training-curves.svg) · [数据/源码入口](../../research/common-comparison-20261112/neural/README.md)

## 08 · calibration-base8-weightedLR

校准点图：Octcal分位数定箱，Jan每箱N/事件/Wilson区间；校准只使用Octcal，Jan已见。

[PNG](../../research/common-comparison-20261112/statistics/figures/calibration-base8-weightedLR.png) · [SVG](../../research/common-comparison-20261112/statistics/figures/calibration-base8-weightedLR.svg) · [数据/源码入口](../../research/common-comparison-20261112/statistics/README.md)

## 09 · calibration-full141-AE

校准点图：Octcal分位数定箱，Jan每箱N/事件/Wilson区间；校准只使用Octcal，Jan已见。

[PNG](../../research/common-comparison-20261112/statistics/figures/calibration-full141-AE.png) · [SVG](../../research/common-comparison-20261112/statistics/figures/calibration-full141-AE.svg) · [数据/源码入口](../../research/common-comparison-20261112/statistics/README.md)

## 10 · calibration-full141-column-gate

校准点图：Octcal分位数定箱，Jan每箱N/事件/Wilson区间；校准只使用Octcal，Jan已见。

[PNG](../../research/common-comparison-20261112/statistics/figures/calibration-full141-column-gate.png) · [SVG](../../research/common-comparison-20261112/statistics/figures/calibration-full141-column-gate.svg) · [数据/源码入口](../../research/common-comparison-20261112/statistics/README.md)

## 11 · calibration-full141-encodedCatBoost

校准点图：Octcal分位数定箱，Jan每箱N/事件/Wilson区间；校准只使用Octcal，Jan已见。

[PNG](../../research/common-comparison-20261112/statistics/figures/calibration-full141-encodedCatBoost.png) · [SVG](../../research/common-comparison-20261112/statistics/figures/calibration-full141-encodedCatBoost.svg) · [数据/源码入口](../../research/common-comparison-20261112/statistics/README.md)

## 12 · calibration-full141-nativeCatBoost

校准点图：Octcal分位数定箱，Jan每箱N/事件/Wilson区间；校准只使用Octcal，Jan已见。

[PNG](../../research/common-comparison-20261112/statistics/figures/calibration-full141-nativeCatBoost.png) · [SVG](../../research/common-comparison-20261112/statistics/figures/calibration-full141-nativeCatBoost.svg) · [数据/源码入口](../../research/common-comparison-20261112/statistics/README.md)

## 13 · canonical-paired-brier-AP

同一校准概率融合系统的Brier/AP固定score条件差区间。

[PNG](../../research/common-comparison-20261112/statistics/figures/canonical-paired-brier-AP.png) · [SVG](../../research/common-comparison-20261112/statistics/figures/canonical-paired-brier-AP.svg) · [数据/源码入口](../../research/common-comparison-20261112/statistics/README.md)

## 14 · canonical-paired-loss-hits

概率误差改善与名单命中改善分别读；命中差区间含0。

[PNG](../../research/common-comparison-20261112/statistics/figures/canonical-paired-loss-hits.png) · [SVG](../../research/common-comparison-20261112/statistics/figures/canonical-paired-loss-hits.svg) · [数据/源码入口](../../research/common-comparison-20261112/statistics/README.md)

## 15 · model-information-split-ranges

每split先平均seed指标的范围；不是融合概率后指标，后者另表。

[PNG](../../research/common-comparison-20261112/statistics/figures/model-information-split-ranges.png) · [SVG](../../research/common-comparison-20261112/statistics/figures/model-information-split-ranges.svg) · [数据/源码入口](../../research/common-comparison-20261112/statistics/README.md)

## 16 · paired-information-effects

同一学习包full-base字段效应，不把全部字段说成独立新信息。

[PNG](../../research/common-comparison-20261112/statistics/figures/paired-information-effects.png) · [SVG](../../research/common-comparison-20261112/statistics/figures/paired-information-effects.svg) · [数据/源码入口](../../research/common-comparison-20261112/statistics/README.md)

## 17 · selection-stability

名单Jaccard；相同命中可能对应不同客户。

[PNG](../../research/common-comparison-20261112/statistics/figures/selection-stability.png) · [SVG](../../research/common-comparison-20261112/statistics/figures/selection-stability.svg) · [数据/源码入口](../../research/common-comparison-20261112/statistics/README.md)
