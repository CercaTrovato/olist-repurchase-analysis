"""Aggregate training support only; common root harness owns outcome metrics/calibration."""
import hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent
rows=pd.read_csv(OUT/'run-support.csv')
assert len(rows)==90 and rows.status.eq('complete').all()
curves=pd.read_csv(OUT/'supervised-curves.csv')
pre=pd.read_csv(OUT/'pretrain-curves.csv')
assert len(curves)==4500 and len(pre)==600
fidelity=json.loads((OUT/'source-fidelity.json').read_text())
assert fidelity['status']=='PASS'
freeze=json.loads((OUT/'source-freeze.json').read_text())
for name in ['plan.md','neural_models.py','run_neural.py','verify_neural.py']:
    assert hashlib.sha256((OUT/name).read_bytes()).hexdigest()==freeze['files_sha256'][name]
assert hashlib.sha256((OUT.parent/'eval_harness.py').read_bytes()).hexdigest()==freeze['files_sha256']['root_harness']
assert hashlib.sha256((OUT.parent/'shared/data-manifest.json').read_bytes()).hexdigest()==freeze['files_sha256']['root_manifest']
records=[json.loads((OUT/name).read_text(encoding='utf-8')) for name in rows.common_record_file]
calibration=[dict(run_id=r['run_id'],family=r['family'],information=r['information'],split_id=r['split_id'],seed=r['seed'],
                  success=r['calibration']['success'],active_lower_bound=r['calibration']['active_lower_bound'],
                  slope=r['calibration']['a'],projected_gradient_inf=r['calibration']['projected_gradient_inf'],
                  message=r['calibration']['message'],Jan_raw_vs_calibrated_selected_symmetric_difference=r['Jan_raw_vs_calibrated_selected_symmetric_difference']) for r in records]
pd.DataFrame(calibration).to_csv(OUT/'calibration-status.csv',index=False,lineterminator='\n')
metrics=[row for record in records for row in record['metrics']]
capacities=[row for record in records for row in record['capacities']]
pd.DataFrame(metrics).to_csv(OUT/'common-metrics.csv',index=False,lineterminator='\n')
pd.DataFrame(capacities).to_csv(OUT/'common-capacities.csv',index=False,lineterminator='\n')
support=[]
for (split,information,family),group in rows.groupby(['split','information','family'],sort=True):
    support.append(dict(split=split,information=information,family=family,seeds=len(group),
        final_fit_BCE_mean=group.final_fit_BCE.mean(),final_fit_BCE_min=group.final_fit_BCE.min(),final_fit_BCE_max=group.final_fit_BCE.max(),
        constant_fit_BCE=group.constant_fit_BCE.iloc[0],supervised_parameters=int(group.supervised_parameters.iloc[0]),
        pretraining_parameters=int(group.pretraining_parameters.iloc[0]),supervised_seconds_sum=group.supervised_seconds.sum(),
        pretraining_seconds_sum=group.pretraining_seconds.sum()))
pd.DataFrame(support).to_csv(OUT/'training-support-by-split.csv',index=False,lineterminator='\n')
fig,axes=plt.subplots(1,2,figsize=(13,4.5),sharey=True)
colors={'mean':'#4477aa','column-gate':'#cc6677','AE':'#228833'}
for ax,information in zip(axes,['base8','full141']):
    for family in ['mean','column-gate','AE']:
        group=rows.loc[rows.information.eq(information)&rows.family.eq(family)].groupby('split').final_fit_BCE.agg(['mean','min','max'])
        x=np.arange(5)
        ax.errorbar(x,group['mean'],yerr=np.stack([group['mean']-group['min'],group['max']-group['mean']]),fmt='o-',color=colors[family],label=family)
    ax.axhline(rows.constant_fit_BCE.iloc[0],c='gray',ls=':',label='Fit constant-prevalence BCE')
    ax.set_xticks(np.arange(5),['1111','1112','1113','1114','1115'])
    ax.set(xlabel='Stratified split suffix, 2026',title=information)
    ax.grid(alpha=.2)
axes[0].set_ylabel('Final model fit BCE (lower is better)')
axes[0].legend(fontsize=8)
fig.suptitle('Training support only; bars = three-seed min/max, not confidence intervals')
fig.tight_layout()
for ext in ['png','svg']:fig.savefig(OUT/f'fit-optimization-support.{ext}',dpi=150)
plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(13,4.5))
for ax,information in zip(axes,['base8','full141']):
    for family in ['mean','column-gate','AE']:
        group=curves.loc[curves.information.eq(information)&curves.family.eq(family)].groupby('epoch').online_mean_BCE.agg(['mean','min','max'])
        ax.plot(group.index,group['mean'],color=colors[family],label=family)
        ax.fill_between(group.index,group['min'],group['max'],color=colors[family],alpha=.12)
    ax.set(xlabel='Fixed supervised epoch',ylabel='Online epoch-average BCE',title=information)
    ax.legend();ax.grid(alpha=.2)
fig.suptitle('All five splits and three seeds retained; online loss differs from final-model loss')
fig.tight_layout()
for ext in ['png','svg']:fig.savefig(OUT/f'supervised-training-curves.{ext}',dpi=150)
plt.close(fig)
fig,ax=plt.subplots(figsize=(8,4.5))
for information,color in [('base8','#4477aa'),('full141','#cc6677')]:
    group=pre.loc[pre.information.eq(information)].groupby('epoch').online_view_mean_MSE.agg(['mean','min','max'])
    ax.plot(group.index,group['mean'],color=color,label=information)
    ax.fill_between(group.index,group['min'],group['max'],color=color,alpha=.12)
ax.set(xlabel='Fixed unsupervised epoch',ylabel='Equal average of six view MSEs',title='AE reconstruction: target content differs across information tiers')
ax.legend();ax.grid(alpha=.2);fig.tight_layout()
for ext in ['png','svg']:fig.savefig(OUT/f'AE-reconstruction-curves.{ext}',dpi=150)
plt.close(fig)
summary=dict(status='finalized_readback_separate',supervised_models=len(rows),AE_pretraining_runs=30,
    common_metric_rows=len(metrics),common_capacity_rows=len(capacities),calibration_success_count=sum(r['success'] for r in calibration),
    calibration_boundary_count=sum(r['active_lower_bound'] for r in calibration),
    calibration_selection_changed_runs=sum(r['Jan_raw_vs_calibrated_selected_symmetric_difference']>0 for r in calibration),
    final_fit_BCE_minus_constant_min=float(rows.fit_BCE_minus_constant.min()),
    final_fit_BCE_minus_constant_max=float(rows.fit_BCE_minus_constant.max()),
    parameter_counts_by_dimension=rows[['total_input_columns','family','supervised_parameters','pretraining_parameters','pretraining_active_parameters']].drop_duplicates().to_dict('records'),
    supervised_seconds_sum=float(rows.supervised_seconds.sum()),AE_pretraining_seconds_sum=float(rows.pretraining_seconds.sum()),
    finalize_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(OUT/'aggregate-support.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
run_verification=json.loads((OUT/'verification.json').read_text())
readback=json.loads((OUT/'readback-verification.json').read_text())
assert readback['status']=='PASS'
lines=['# 统一神经比较：共享矩阵、固定预算与保存后读回','',
    f"完成 {len(rows)} 个监督模型、30 次 AE 预训练；5 个固定 fit/cal 划分 × 3 seeds × 两档信息 × mean/column-gate/AE。全部候选保留，不用一月挑 seed、epoch 或架构。正式矩阵执行 {run_verification['elapsed_seconds']:.1f} 秒，另有 fit-only 两 epoch 计时小试；小试没有 cal/Jan 评分，不计正式模型。",'',
    '## 共同输入与初始化配对','',
    '所有数据只调用根 eval_harness.load_split(split, information, dense=True, dtype=float32)：五个 split20261111..20261115，每个 fit16928/169 正例、cal4232/42 正例，Jan29368/230 全体评分。完整六视图总维度依次808/813/817/813/812，base8恒34编码列；base8由根接口把所有新增列置0，六分支形状不变。这里没有重新构造特征、拟合变换或重新切分。预处理/矩阵/掩码责任与来源见根共享manifest。','',
    '同 split/seed 的六个模型组合（两个信息档×三家族）enc/head初始值哈希一致；监督 batch 顺序用 generator(seed)，AE 预训练用 generator(seed+901)，各配对格顺序哈希一致。参数形状只随该 split 的训练类别字典改变，不随信息档改变。输入执行为float32；保存logit使用float64容器，只保留实际float32推理值，不声称恢复已损失的计算精度。','',
    '## 模型与预算','',
    '每视图Linear(d,16)+ReLU，六视图等权平均，再Linear(16,1)。mean为必要参照；column-gate先对每编码列施加x*sigmoid(a*x+b)，a=b=0，因此初始整体缩放为0.5。门控新增参数和初始缩放均保留，不把差异解释为纯门机制因果效果。','',
    'AE使用相同enc/head主体，额外每视图Linear(16,d) decoder。预训练20epochs、batch256、Adam.001，loss为六个视图各自MSE再等权平均（不是所有编码列统一MSE）；只用fit X，不使用y。之后移除decoder，用真实fit y监督50epochs、batch512、Adam.001、未加权BCE、dropout0，全参数适配，不冻结encoder、不早停、没有额外L2。mean/gate也完全相同50轮监督预算。','',
    '90×50共4500个监督epoch记录（153000次更新），30×20共600个预训练epoch记录（40200次更新）。这不是新增独立客户或独立时期。AE多了20轮无监督预算，而且base8重建目标有更多常数0列；gate初始缩放及AE额外预算/目标差异留待后续消融，不用本比较宣称已分离全部机制。没有跑NCE/FN/潜原型等额外格。','',
    '## 训练支持（不代替一月评价）','',
    '|信息档/家族|监督模型数|监督参数范围|最终fit BCE均值|最终fit BCE范围|AE预训秒合计|','|---|---:|---:|---:|---|---:|']
for (information,family),group in rows.groupby(['information','family'],sort=True):
    low=int(group.supervised_parameters.min());high=int(group.supervised_parameters.max())
    parameters=str(low) if low==high else f'{low}–{high}'
    lines.append(f"|{information}/{family}|{len(group)}|{parameters}|{group.final_fit_BCE.mean():.6f}|{group.final_fit_BCE.min():.6f}–{group.final_fit_BCE.max():.6f}|{group.pretraining_seconds.sum():.1f}|")
lines+=['',f"共同fit常数BCE为{rows.constant_fit_BCE.iloc[0]:.8f}；各模型相对它的最终fit BCE差范围为{rows.fit_BCE_minus_constant.min():.8f}至{rows.fit_BCE_minus_constant.max():.8f}。这是训练优化支持，不是最优收敛或未见期收益证明。最终模型fit BCE由保存的fit logit重算，和训练过程中权重持续变化的online epoch平均loss分开。",'',
    '监督参数含enc/head，gate另含2D门参数；AE监督时decoder已移除。AE预训练总参数还包括decoder和当时未参与重建损失的17个head参数，run-support另列pretraining_active_parameters排除该head。base8的零占位列不提供客户信息，部分权重因此没有非零输入梯度，但分支bias仍可能学常数。名义保留列数不等于独立信息量。','',
    '![最终模型的fit优化支持](fit-optimization-support.png)','',
    '![所有监督学习曲线](supervised-training-curves.png)','',
    '![AE重建曲线](AE-reconstruction-curves.png)','',
    '## 共同校准与评价','',
    '每个run直接调用根write_run，用Octcal自然分布拟合共同的正斜率单调Platt，并保存raw/校准概率、自然概率指标、全局2937与共同H05久单群内独立79等容量。没有自建第二套校准或指标函数。cal校准后读数是同批cal标签再代入，不当作无偏验证；一月已见，不称盲测。','',
    f"共同harness产生{len(metrics)}行指标、{len(capacities)}行策略；校准success={summary['calibration_success_count']}/90，下界命中{summary['calibration_boundary_count']}格。raw与校准Top2937集合发生变化的run为{summary['calibration_selection_changed_runs']}格；全部保留于calibration-status.csv，不能只据理论单调性省略实际核查。",'',
    '主策略和ensemble由根统一管理：单run读取各自raw排名/正斜率校准；canonical ensemble最终用三个seed校准概率的均值作为统一分数，AP/名单/概率评价不混接不同分数。跨五split的配对差、初始化与划分扰动、研究候选取舍由根统计矩阵回答；本目录不因最高seed宣布赢家。','',
    '## 保存、来源与读回','',
    'run-support.csv保存90格支持、参数、真实时长、最终fitBCE、AE初末MSE和顺序/初始化哈希；supervised-curves.csv / pretrain-curves.csv保存全部曲线。每run公共record来自共同harness，common-metrics.csv / common-capacities.csv只是其原值汇总。private有90个监督state_dict、30个预训练state_dict、逐run三时段logit/曲线、共同raw/校准概率及Platt参数。逐人键/标签只沿根共享private定位，不写公共表。','',
    'source-freeze.json在真实pilot与90模型之前冻结本地plan/model/driver/读回源码和根manifest/harness哈希。source-fidelity.json另用64行合成张量比对原上批源码：初始化/forward/两epoch监督state逐参数相同，AE两epoch预训练state也相同；这不是客户实验，也没读取旧Jan成绩择参数。','',
    f"readback-verification.json为PASS：从保存state_dict用独立显式线性运算重放90个模型的fit/cal/Jan共270个logit数组，全部逐元素相同；float64容器、最终fitBCE、共享初始化与batch顺序、共同harness保存的logit一致。没有在读回调用fit。工程读回不冒称另一位代理的科学独审。",'',
    '本目录只负责固定神经矩阵，最终采用与正式消融由主任务继续。没有安装、外发、Git或看板操作；没有读取或新评分四月。局部完成和最终三端同步分别报告。']
(OUT/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))
