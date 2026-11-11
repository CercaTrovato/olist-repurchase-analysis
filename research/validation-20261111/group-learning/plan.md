# P4A 冻结计划

冻结时间 2026-11-11，先于本批任何 Jan 新评分。仅 Oct/Jan，复用通过哈希校验的 `read_dev()`；四月读取 0。Jan 已见，不能作为最终盲测，不据 Jan 结果选赢家。

## 共同拆分与表示

Oct 21,160 人按 y stratified、random_state20261111 分为 fit 16,928 / cal 4,232；所有候选完全同一拆分。仅 fit 的 7 个原数值字段 log1p 后 StandardScaler，state 训练侧 OHE(ignore unknown)，共原 8 输入字段。群拟合也仅 fit：R 原值/logF/logM 标准化的 KMeans K3；K2..8 的固定 2,000 人训练 silhouette 选择（tie1e-3取较小K）；diagonal GMM K2..8 BIC最小选择。KMeans seed42/n_init20，GMM seed42/max_iter300/n_init1，均固定。cal/Jan 只转换与分配。

固定评估全客户 Jan n29,368 / y230、K2937；共同久单永远用既有 H05-km3-v1 cluster_id1 n12,330 / y90，群内独立取79。内部新群号不替换共同 H05 切片。

## 线性候选与相关初值

共享 logit 为 b+xβ。硬群 w 为 KMeans one-hot，软群 w 为 GMM后验。斜率分支 logit=b+xβ+eta·Σ_g w_g·(xδ_g)，eta=.1。

仅 fit 内逐群逐列计算 corr(x_j,y)，常量列或常量 y 置0，tilde_c_gj=corr·npos_g/(npos_g+20)。这是群内相关与小样本收缩，**不是控制变量 ANCOVA**，也不是因果量。

冻结候选：fit基率常数；matched unweighted LR；matched balanced LR raw 与训练prior校正（logit加logit(fit基率)）；硬RFM K3共享+固定相关δ；硬K3可学习δ零初始化；同模型相关初始化；训练几何所选K的相关初始化可学习δ；GMM BIC所选K的软可学习δ；仅K3群one-hot截距（无群特征斜率）。

所有凸线性候选统一 L-BFGS-B、maxiter1000、ftol1e-12、gtol1e-7，目标 sum BCE + .5||β||² + .5||δ||²；共享bias不罚，群截距候选偏移L2系数同为1。固定δ不优化。balanced各类权重=n/(2n_class)，总权重=n。基础LR、群截距和可学习群斜率使用相同fit及优化标准。记录目标、迭代、梯度、success；零/相关初值同凸目标应收敛同解，记录参数与分数差，不把未收敛差异解释为统计初始化收益。

## 共享残差支路

硬RFM K3门控共享hidden16残差：logit=b+xβ+eta·Σ_g w_g·[V_g ReLU(Wx+a)]。同形状identity激活作线性残差对照，参数数与优化预算相同。两者各3seed2026/2027/2028，50epochs、batch512、Adam lr.001、dropout0、未加权BCE。共享β/b从matched unweighted LR初始化，hidden按torch默认初始化，V初始0；所有参数可学习。各weight矩阵与β用 .5/n 的L2，bias不罚；两支路规则相同。CPU2threads，epoch固定不据cal/Jan早停或选seed。

## 校准和评价

每个score变体都只在Oct cal上拟合Platt：单变量raw logit到自然y，LogisticRegression(C=1e6, lbfgs)，不加类权重。raw及Platt校准后都报Jan；balanced prior校正作为独立raw变体也走同一cal流程。Octcal raw指标可用于候选诊断；**Octcal用于拟合Platt，其校准后指标是再代入读数，不是无偏验证**。固定cal用于校准，不能同时称独立验证。

指标：全体自然分布Logloss/Brier/AP/AUC、10等宽箱ECE与calibration-in-the-large，阈值.5混淆/precision/recall/F1；容量5/10/20%（ceil）以及固定久单79的hits/precision/recall/lift和随机期望。不用Jan扫阈值。参数数、时间、训练损失/收敛、训练群统计支持和3seed逐项结果全部保留。原始未校准balanced不当成正确概率；prior校正基于类权重理论，并不保证模型完全校准。

## 保存与读回

所有变换、模型参数、群模型、键序、fit/cal索引、逐人logit/raw/cal概率放private；外层仅聚合CSV/报告/PNG/SVG和代码哈希。读回全部逐人评分，核模型重算/键序/指标。没有安装、外发、Git、看板或原件修改；后续总同步由主代理处理。固定候选只跑这一轮，不无限搜索，不根据Jan宣布胜者。
