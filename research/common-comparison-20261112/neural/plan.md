# 统一神经矩阵冻结配置

先读根 `../task_plan.md`，本文件先于新评分。只读根制作的共同 matrix / split / 键 / 特征掩码；禁止调用旧数据构造器、重新拟合预处理或重切 split。等待根共享 schema 后仅绑定文件和键名，不改科学配置。

## 唯一候选与预算

5 splits：20261111..20261115；3 seeds：2026/2027/2028；信息档 base8/full141；家族 mean/column-gate/AE，共90个监督模型，AE另30次预训练。仅 CPU2threads。除fit-only计时小试外不增加候选，不跑NCE/FN等、不改宽度或epoch，不读旧Jan成绩选择参数。

每视图Linear(d,16)+ReLU，六视图等权平均，共享Linear(16,1)头。column-gate为x*sigmoid(a*x+b)，a=b=0，初始整体缩放.5；其额外参数显式报告。AE与mean共享主体，decoder每视图Linear(16,d)，每视图各自MSE后六视图等权平均，20epochs/batch256/Adam.001；然后移除decoder，50epochs监督全参数微调。不是按全部编码列统一MSE，也不冻结encoder。

监督均50epochs/batch512/Adam.001/未加权BCE/dropout0，无L2额外项、无earlystop。完整保留上批Model/supervised/pretrain的上述分支。监督generator(seed)，AE预训练generator(seed+901)，与上批一致；同seed/同split两信息档和所有候选监督顺序严格配对；初始化先seed后建enc/head，gate零参数和AE decoder在head之后构建，不改变共享enc/head的初始值。AE预训练阶段的顺序也在各信息档配对。

## 共同矩阵与已知限制

根完整float64六视图矩阵的原8编码列由mask标记。base8只把额外列置0，保留总维度、六分支形状与总参数；新增常数占位不提供客户信息，但可由分支bias形成常数。AE的重建任务在base8/full141间也改变，且额外20轮预算、gate初始.5缩放仍留待后续消融，不作纯模块因果结论。

训练输入转float32；保存实际float32推理所得logit为float64容器，避免CSV再解析量化，不声称恢复float32已损失的计算精度。保存每run fit/cal/Jan logits与curve/state_dict；模型/键/逐人结果全部private。报告最终模型fit BCE（与fit常数基率BCE比较），不把在线epoch平均loss当最终模型loss。AE另外给逐epoch和最终fit-only per-view-average MSE。

## 评价与停止边界

只给根eval_harness传保存logits，由共同harness做cal自然分布拟合、raw/校准评价及名单核验。单run主策略raw排名并核单调校准；canonical ensemble按根最新指令用mean calibrated probability作统一分数，不混接mean-logit AP与另一名单。根原plan若仍写mean-logit，以最新指令修正后为准，本子任务不自行选择ensemble。

先fit-only两epoch计时小试，不算正式90模型，不对pilot评分cal/Jan，不依据Jan变更配置。正式运行保留所有失败，不因负结果重启或换参数；发现NaN/Inf或缺matrix/schema则停止受影响项并报告。期望数据fit16928/169、cal4232/42、Jan29368/230，固定共同H05久单由根harness管理。

不安装、不外发、不改原件或共享矩阵、不操作Git/看板、不读四月。输出仅本neural目录和任务scratch/neural，原模型/结果不覆盖。

## 已绑定的共享接口

根于2026-11-12确认SHARED_READY：5 split总维度808/813/817/813/812，base8恒34列。全部模型直接调用根 `eval_harness.load_split(split,information,dense=True,dtype=float32)`，原始float64矩阵的读取、mask和行序完全由根接口负责，本地不实现第二套loader或mask。每run直接调用同根 `write_run` 生成共同calibration/metrics/capacities及NPZ/JSON，不另造校准或评估。根的manifest/harness与本地driver/model/plan哈希在pilot前绑定于source-freeze.json。
