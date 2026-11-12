"""Read-back aggregation for the fixed classical matrix; no fitting."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent;ROOT=OUT.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(x,n):(OUT/n).write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
def main():
    index=json.loads((OUT/'models-index.json').read_text());assert len(index)==65
    counts=pd.Series([x['family'] for x in index]).value_counts().to_dict();assert counts=={'encodedCatBoost':30,'nativeCatBoost':15,'weightedLR':10,'unweightedLR':10}
    freeze=json.loads((OUT/'frozen-config.json').read_text());assert sha(OUT/'classical_engine.py')==freeze['engine_sha256'];assert sha(OUT/'run_classical.py')==freeze['driver_sha256'];assert sha(ROOT/'eval_harness.py')==freeze['eval_harness_sha256'];assert sha(ROOT/'shared/data-manifest.json')==freeze['shared_manifest_sha256']
    shared=json.loads((ROOT/'shared/data-manifest.json').read_text());source_checks={p:sha(p)==h for p,h in shared['sources'].items()};assert all(source_checks.values())
    for split,d in shared['splits'].items():
        for n,h in d['files'].items():assert sha(ROOT/'shared/private'/f'split-{split}'/n)==h
    training=[];metrics=[];capacities=[];cbcurves=[];numerics=[];calibration=[];file_checks=[]
    for x in index:
        directory=OUT/x['private_directory'];m=json.loads((directory/'metadata.json').read_text());assert sha(directory/'metadata.json')==x['metadata_sha256'];assert all(e==0 for e in x['reloaded_logit_max_errors'].values())
        record=json.loads((OUT/x['root_record_path']).read_text());assert record['family']==x['family'] and record['information']==x['information'] and record['split_id']==x['split'];assert record['shared_manifest_sha256']==freeze['shared_manifest_sha256'];assert record['eval_harness_sha256']==freeze['eval_harness_sha256'];assert sha(ROOT/record['score_file'])==record['score_sha256']
        logs=np.load(directory/'logits.npz');scores=np.load(ROOT/record['score_file']);assert all(logs[p].dtype==np.float64 and len(logs[p])==n for p,n in [('fit',16928),('cal',4232),('jan',29368)])
        for p in ['fit','cal','jan']:assert np.array_equal(logs[p],scores[p+'_logit'])
        row={k:x[k] for k in ['model_id','family','information','split','seed','training_seconds']};row['input_columns']=m['input_columns'];row['fit_rows']=m['fit_rows'];row['input_representation']='raw_native_fields' if x['family']=='nativeCatBoost' else 'root_shared_encoded';row['information_exposed_columns']=m['source']['base_encoded_columns'] if x['information']=='base8' else m['input_columns'];row['raw_calibration_top2937_selection_symmetric_difference']=record['Jan_raw_vs_calibrated_selected_symmetric_difference']
        if x['family'] in ['weightedLR','unweightedLR']:
            d=m['training_objective'];opt=m['optimizer'];assert len(opt)==1 and m['parameters']['tol']==1e-10 and m['parameters']['max_iter']==5000
            grad=np.load(directory/'gradient-sum.npy');assert abs(np.max(np.abs(grad))-d['gradient_sum_inf'])<1e-12
            assert abs(opt[0]['fun']*d['weight_sum']-d['sum_objective'])<1e-6
            assert abs(opt[0]['jac_inf']-d['gradient_weighted_mean_inf'])<1e-12
            row.update(linear_parameter_count=m['input_columns']+1,n_iter=m['n_iter'][0],optimizer_success=opt[0]['success'],optimizer_message=opt[0]['message'],warnings=' | '.join(m['warnings']),**{k:v for k,v in d.items() if isinstance(v,(int,float,bool))})
            numerics.append({k:row[k] for k in row})
        else:
            assert m['tree_count']==300 and not m['eval_set_used'] and not m['early_stopping_used'] and not m['class_weight_used'];loss=pd.read_csv(directory/'fit-loss.csv');assert len(loss)==300
            model=CatBoostClassifier();model.load_model(str(directory/'model.cbm'));leaf_count=int(len(model.get_leaf_values()));row.update(tree_count=300,CB_leaf_value_count=leaf_count,final_fit_Logloss=m['final_fit_Logloss'])
            loss=loss.assign(model_id=x['model_id'],family=x['family'],information=x['information'],split=x['split'],seed=x['seed']);cbcurves.append(loss)
        calibration.append({k:record[k] for k in ['run_id','family','information','split_id','seed']}|record['calibration']);metrics+=record['metrics'];capacities+=record['capacities'];training.append(row);file_checks.append(dict(model_id=x['model_id'],three_periods_reloaded=True,root_record_and_float64_scores_match=True))
    assert len(metrics)==1400 and len(capacities)==560
    tr=pd.DataFrame(training);num=pd.DataFrame(numerics);curve=pd.concat(cbcurves,ignore_index=True);tr.to_csv(OUT/'training-summary.csv',index=False);num.to_csv(OUT/'LR-optimization-diagnostics.csv',index=False);curve.to_csv(OUT/'CB-fit-loss.csv',index=False);pd.DataFrame(calibration).to_csv(OUT/'calibration-diagnostics.csv',index=False);pd.DataFrame(metrics).to_csv(OUT/'metrics.csv',index=False);pd.DataFrame(capacities).to_csv(OUT/'capacities.csv',index=False)
    fig,axs=plt.subplots(1,2,figsize=(12,4.5))
    for (family,information),d in num.groupby(['family','information']):
        d=d.sort_values('split');label=family+'/'+information;axs[0].plot(d.split.astype(str),d.gradient_weighted_mean_inf,'o-',label=label);axs[1].plot(d.split.astype(str),d.n_iter,'o-',label=label)
    axs[0].set_yscale('log');axs[0].axhline(1e-10,color='black',linestyle='--',label='configured gtol');axs[0].set_title('Actual weighted-mean gradient infinity norm');axs[1].set_title('LBFGS iterations');axs[0].legend(fontsize=7);axs[1].legend(fontsize=7)
    for ax in axs:ax.tick_params(axis='x',rotation=30);ax.grid(alpha=.2)
    fig.suptitle('Optimizer termination diagnostics; successful ftol stop does not certify gtol');fig.tight_layout();fig.savefig(OUT/'LR-optimization.png',dpi=150);fig.savefig(OUT/'LR-optimization.svg');plt.close(fig)
    fig,axs=plt.subplots(1,3,figsize=(15,4.3))
    for ax,(family,info) in zip(axs,[('encodedCatBoost','base8'),('encodedCatBoost','full141'),('nativeCatBoost','full141')]):
        dd=curve.loc[curve.family.eq(family)&curve.information.eq(info)&curve.split.eq(20261111)]
        for s,g in dd.groupby('seed'):ax.plot(g.iteration,g.fit_Logloss,label=str(int(s)))
        ax.set_title(family+'/'+info);ax.set_xlabel('Iteration');ax.set_ylabel('Unweighted fit Logloss');ax.grid(alpha=.2);ax.legend()
    fig.suptitle('Canonical split20261111, all3 fixed seeds; training curves are not Jan performance');fig.tight_layout();fig.savefig(OUT/'CB-fit-curves.png',dpi=150);fig.savefig(OUT/'CB-fit-curves.svg');plt.close(fig)
    reached=int(num.weighted_mean_gradient_at_or_below_tol.sum());messages=num.optimizer_message.value_counts().to_dict();warnings=int(num.warnings.astype(str).str.len().gt(0).sum());selection_changes=int(tr.raw_calibration_top2937_selection_symmetric_difference.gt(0).sum())
    lines=['# 统一经典模型矩阵','', '固定65格已完成：WLR10、未加权LR桥接10、统一编码CatBoost30、原生类别CatBoost桥接15。所有模型、信息档、训练划分与seed完整保留；不依据一月调参或挑种子。本目录只负责经典矩阵，跨家族/跨划分的配对结论由根统计统一汇总，不自动更换正式模型。','', '## 输入与公平比较范围','', '五个80/20分层划分来自根shared loader，split20261111..20261115。各fit16928/169正例、cal4232/42正例，Jan29368/230全量评分，权威久单H05 cluster1=12330/90、独立top79。编码X均float64，维度依次808/813/817/813/812；base8保留原8独立log1p/StandardScaler/state-OHE的34个编码列，其他列由根loader置0。WLR/ULR/编码CB读取与神经分支完全相同的信息档X，不自行split/重编码。','', 'nativeCB是单列桥接：原141列、8个原生类别，类别缺失__MISSING__，数值只用fitmedian填补、不log/scale；因此与编码CB不同输入表达，不能当完全相同X的模型效应。原静态/录入回写假设承接P2，不声称恢复严格生产历史时点。','', 'WLR C1/balanced、ULR只把class_weight改None，均LBFGS tol1e-10 max5000。CB depth3/iterations300/lr.03/l2_leaf_reg10/unweighted/CPU2；无eval_set、无earlystop。原全Oct训练50命中存档未覆盖，不能与本轮80%fit当同训练信息的模型效应。','', '## 求解与实测收敛','', f'20个LR中实际归一化梯度inf<=1e-10有{reached}个；有warning的{warnings}个。真实停止message分布：{messages}。无warning/优化器success不代表满足配置gtol。详见LR-optimization-diagnostics.csv与私有完整梯度。','', 'LR独立核sum weighted BCE+0.5||coef||²/C，intercept不罚。WLR正/负样本权重为N/(2*Nclass)，ULR均为1；完整sum目标梯度与求解器加权均值尺度梯度同时报告，二者相差weight_sum16928。捕获SciPy返回fun/jac/options，验证fun*weight_sum与独立sum目标、内部jac_inf与独立归一化梯度吻合。优化器因ftol停止时照实保留，没有临时更改参数或追加拟合挑赢家。','', '所有45个CB都实际训练300轮，完整13500行fit Logloss在CB-fit-loss.csv；fit loss只是训练曲线，不是Jan科学验证。CPU2时间见training-summary.csv，小试4个正式格保存后直接复用，未额外重训。','', '## 统一校准、输出与核验','', '每个run均调用根eval_harness.write_run，使用同4232自然分布cal进行受约束单调Platt，概率/排序/全体与群域由根统一计算。WLR raw为训练先验尺度诊断，prior修正与calibrated版本分开。cal的calibrated指标为校准拟合内读数，不称无偏。主策略按根协议使用raw logit；校准输出的实际名单差异也保留。','', f'本目录已核65模型×fit/cal/Jan=195次重载，logits误差全部0，三期raw logits与根scoreNPZ逐元素一致，均float64；根score文件SHA、1400指标行/560容量行及所有输入SHA在收尾回读。raw→calibrated全局K2937名单有非零选择差异的模型数={selection_changes}，这是实际有限精度/极小斜率读数，不能未经核对概括为一律不变。','', '公共聚合为metrics.csv、capacities.csv、training-summary.csv、LR-optimization-diagnostics.csv、calibration-diagnostics.csv、CB-fit-loss.csv；单run-record.json包含相同根级聚合。private保留model.joblib/model.cbm、原始float64三期logits、完整sum梯度、每轮fit loss、native填补值和根统一校准分数/参数。公共文件不含客户键/逐人分数。','', '代码为本机执行记录：依赖根eval_harness.py、shared/data-manifest.json及其私有矩阵/原表，不是独立可下载一键复现包。最终训练源码/参数/根schema SHA在frozen-config.json，源输入/每split文件SHA在metadata.source。classical_engine原语不做校准，只有根harness拟合Platt；未更改共享数据或候选科学配置。','', '本目录图只说明训练曲线与求解器；三seed/五训练划分都不是独立未来时期。科学质量、共同久单、配对差/名单稳定性与固定分数区间由根statistics按预先规则汇总，不把某个最高seed或旧全Oct成绩当稳定提升。没有April新评分/标签解析、Git、看板、依赖安装或外部写入。']
    (OUT/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    receipt=dict(status='PASS_pending_visual_review',model_count=65,family_counts=counts,model_period_replays=195,max_logit_replay_error=0.,float64_score_arrays_match_root=True,metric_rows=1400,capacity_rows=560,LR_actual_gtol_reached=reached,LR_optimizer_messages=messages,LR_warning_runs=warnings,CB_all_actual_iterations=300,CB_fit_loss_rows=len(curve),input_sha_checks=source_checks,models=file_checks,April_snapshot_rows_read=0,new_April_scores=0,root_harness_sha256=freeze['eval_harness_sha256']);dump(receipt,'verification.json')
    files=[dict(path=p.relative_to(OUT).as_posix(),bytes=p.stat().st_size,sha256=sha(p),private='private' in p.relative_to(OUT).parts) for p in OUT.rglob('*') if p.is_file() and p.name!='manifest.json'];dump(dict(files=files,private_rows_not_public=True),'manifest.json');print('FINALIZED',receipt['model_count'],receipt['family_counts'],'files',len(files),'LR_gtol',reached)
if __name__=='__main__':main()
