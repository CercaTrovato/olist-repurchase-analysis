# 概率层冻结方案

仅处理上层 task_plan.md 中 6 个窗口策略单元及固定 WLR、ULR、native CatBoost 三家族。25 个新基础模型，Jan single 5 个旧基础模型逐键核验、加载原件并回放，绝不重训。每个窗口客户全覆盖，容量排序由价值层负责。禁止四月数据。

新 WLR/ULR 数值取固定 base8 的前 7 个字段，log1p 后用 fit 的 StandardScaler；state 独立 fit OHE，未知值全零。native CatBoost 仅 141 字段、fit 数值中位数、类别缺失 __MISSING__，固定 300 轮无早停。保存输入 SHA、转换器、模型、逐 split 原始 logit/raw p/校准 p，校准仅用 cal。

复用 common/eval_harness.py 的 fit_monotone_platt 和 apply_calibration 数学函数，运行不使用其硬编码加载/输出函数。每个基础模型独立校准，CB 主概率为三 seed 校准概率均值。cal 校准后指标明确为训练内拟合读数。LR 记录优化器终止原因与真实梯度，不将 ftol 终止说成 gtol 达标。

主表为 private/cells/{V}__{strategy}/primary-eval-probabilities.csv，唯一双键 customer_unique_id,snapshot_date，列 p_wlr,p_ulr,p_catboost,cluster,evaluation_date,strategy。不含未来真实 y/G/N。对应私有 primary-{fit,cal}-probabilities.csv 亦保存。probability-manifest.json 仅在 6 单元全部完成且回放通过后 status=READY。

公开 proper-metrics.csv 为全量及 H05 群 LL/Brier/AP/AUC、sum(p)、实际正例数、校准支持；calibration-bins.csv 固定 [0,.005,.01,.02,.05,.1,.2,.5,1] 箱；不搜索箱界、阈值或根据 eval 重训。独立 verify_probability.py 仅加载模型/转换器、回放概率并复算指标，不拟合。

所有新拟合必须 data-manifest.status=READY，且 root-authorization.json 绑定主计划、data manifest 与本 driver SHA 后才开始。失败写 failures.json，保留现场，不按 eval 改参数。
