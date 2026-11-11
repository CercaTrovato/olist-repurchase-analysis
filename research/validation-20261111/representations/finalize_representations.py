import sys
sys.dont_write_bytecode=True
import hashlib,json,runpy
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from torch import nn
import joblib
from sklearn.metrics import log_loss,brier_score_loss,average_precision_score,roc_auc_score
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent;PRIV=OUT/'private'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(x,n):(OUT/n).write_text(json.dumps(x,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
class Head(nn.Module):
    def __init__(self,k):super().__init__();self.head=nn.Linear(k,1)
    def forward(self,x):return self.head(x).squeeze(1)

def main():
    ns=runpy.run_path(str(OUT/'run_representations.py'));info=json.loads((OUT/'private/preprocess.json').read_text());runs=json.loads((OUT/'run-audit.json').read_text());metrics=pd.read_csv(OUT/'january-metrics.csv');cap=pd.read_csv(OUT/'january-capacity.csv');dims=info['dims']
    assert len(runs)==39 and len(metrics)==78 and metrics.groupby(['candidate','seed']).size().eq(2).all();assert metrics.groupby('candidate').seed.nunique().eq(3).all()
    assert all(sha(p)==expected for p,expected in info['feature_sha256'].items());assert sha(PRIV/'october-split.csv')==info['split_sha256']
    split=pd.read_csv(PRIV/'october-split.csv');assert split.part.value_counts().to_dict()=={'fit':16928,'cal':4232};assert split.loc[split.part.eq('cal'),'y'].sum()==42
    x={p:torch.from_numpy(np.load(PRIV/(p+'-matrix.npz'))['X']) for p in ['fit','cal','january']};checks=[];gate=[]
    for r in runs:
        name=r['candidate'];s=r['seed'];scores=pd.read_csv(PRIV/f'{name}-{s}-january-scores.csv',dtype={'customer_unique_id':'string'});cal=pd.read_csv(PRIV/f'{name}-{s}-calibration.csv')
        assert cal.cal_y.eq(split.loc[split.part.eq('cal'),'y'].reset_index(drop=True)).all()
        if name.startswith(('deep-','rfm-')):
            model=Head(r['extra']['K']);xx={part:torch.from_numpy(np.load(PRIV/f'{name}-{s}-{part}-memberships.npy')) for part in ['cal','january']}
        else:model=ns['Model'](dims,name if name in ns['SUP'] else 'mean');xx=x
        model.load_state_dict(torch.load(PRIV/f'{name}-{s}.pt',weights_only=True));new=ns['inference'](model,xx['january']);newcal=ns['inference'](model,xx['cal']);maxerr=float(np.abs(new-scores.raw_logit.to_numpy()).max());assert maxerr<2e-5;assert np.max(np.abs(newcal-cal.cal_logit.to_numpy()))<2e-5
        platt=joblib.load(PRIV/f'{name}-{s}-platt.joblib');newp=platt.predict_proba(scores.raw_logit.to_numpy(np.float32)[:,None])[:,1];assert np.max(np.abs(newp-scores.platt_probability))<1e-12,name
        for prob,pcol in [('raw','raw_probability'),('platt','platt_probability')]:
            y=scores.y.to_numpy();p=scores[pcol].to_numpy(dtype=np.float32 if prob=='raw' else float);row=metrics.loc[metrics.candidate.eq(name)&metrics.seed.eq(s)&metrics.probability.eq(prob)].iloc[0]
            vals=[log_loss(y,p),brier_score_loss(y,p),average_precision_score(y,p),roc_auc_score(y,p)];assert np.allclose(vals,row[['logloss','brier','AP','AUC']].to_numpy(float),atol=1e-11)
            order=np.lexsort((scores.customer_unique_id.to_numpy(str),-scores.raw_logit.to_numpy()))
            for c in cap.loc[cap.candidate.eq(name)&cap.seed.eq(s)&cap.probability.eq(prob)].itertuples():
                ix=order[scores.cluster_id.to_numpy()[order]==1][:79] if c.policy=='long79' else order[:c.k];assert len(ix)==c.k and int(y[ix].sum())==c.hits
        if name=='column-gate':
            with torch.no_grad():g=torch.sigmoid(model.gate_a*x['fit']+model.gate_b);av=g.mean(0).numpy();sv=g.std(0).numpy()
            for i,c in enumerate(info['encoded_names']):gate.append(dict(seed=s,encoded_column=c,a=float(model.gate_a[i].detach()),b=float(model.gate_b[i].detach()),fit_gate_mean=float(av[i]),fit_gate_std=float(sv[i])))
        checks.append(dict(candidate=name,seed=s,serialized_raw_logit_max_error=maxerr,all_probability_metrics_and_capacity_recomputed=True,same_calibration_rows_and_y=True))
    pd.DataFrame(gate).to_csv(PRIV/'column-gate-distributions.csv',index=False)
    adj=[('mean','global'),('mean','view-attention'),('mean','column-gate'),('mean','AE')]+list(zip(ns['PRE'][:-1],ns['PRE'][1:]))+[('rfm-hard','deep-hard'),('rfm-soft','deep-soft')];delta=[]
    for a,b in adj:
        for s in ns['SEEDS']:
            for p in ['raw','platt']:
                aa=metrics.loc[metrics.candidate.eq(a)&metrics.seed.eq(s)&metrics.probability.eq(p)].iloc[0];bb=metrics.loc[metrics.candidate.eq(b)&metrics.seed.eq(s)&metrics.probability.eq(p)].iloc[0];v=dict(before=a,after=b,seed=s,probability=p)
                for col in ['logloss','brier','AP','AUC']:v['delta_'+col]=float(bb[col]-aa[col])
                delta.append(v)
    pd.DataFrame(delta).to_csv(OUT/'adjacent-component-differences.csv',index=False)
    summary=metrics.groupby(['candidate','probability'])[['logloss','brier','AP','AUC']].agg(['mean','std','min','max']);summary.to_csv(OUT/'seed-summary.csv')
    order=ns['SUP']+ns['PRE']+['rfm-hard','rfm-soft','deep-hard','deep-soft'];fig,axs=plt.subplots(1,3,figsize=(18,9));yy=np.arange(len(order))
    for ax,col,title in zip(axs,['logloss','AP','AUC'],['Natural log loss (lower better)','Average precision','ROC AUC']):
        for p,color,offset in [('raw','#2879ae',-.13),('platt','#c26a21',.13)]:
            ss=summary.loc[(order,p),col] if False else pd.DataFrame([summary.loc[(n,p),col] for n in order]);mean=ss['mean'].to_numpy();err=np.stack([mean-ss['min'],ss['max']-mean]);ax.errorbar(mean,yy+offset,xerr=err,fmt='o',capsize=3,label=p,color=color)
        ax.set_yticks(yy,order);ax.invert_yaxis();ax.set_title(title);ax.grid(axis='x',alpha=.2)
    axs[0].legend();fig.suptitle('Three fixed seeds: dots=mean, whiskers=min/max initialization variation; NOT confidence intervals or temporal stability',fontsize=12);fig.tight_layout();fig.savefig(OUT/'representation-quality.png',dpi=150);fig.savefig(OUT/'representation-quality.svg');plt.close(fig)
    rawcap=cap.loc[cap.probability.eq('raw')];fig,axs=plt.subplots(1,2,figsize=(14,8.5))
    for ax,policy in zip(axs,['K2937','long79']):
        ss=rawcap.loc[rawcap.policy.eq(policy)].groupby('candidate').hits.agg(['mean','min','max']).loc[order];mean=ss['mean'].to_numpy();err=np.stack([mean-ss['min'],ss['max']-mean]);ax.errorbar(mean,yy,xerr=err,fmt='o',capsize=3);ax.set_yticks(yy,order);ax.invert_yaxis();ax.set_title(policy+'; raw-logit ranking');ax.set_xlabel('Positives captured');ax.grid(axis='x',alpha=.2)
    fig.suptitle('Three-seed min/max = initialization variation only; NOT confidence intervals or cross-period stability');fig.tight_layout();fig.savefig(OUT/'representation-capacity.png',dpi=150);fig.savefig(OUT/'representation-capacity.svg');plt.close(fig)
    negative=[dict(candidate=r['candidate'],seed=r['seed'],slope=r['platt_slope']) for r in runs if r['negative_platt_slope']]
    v=json.loads((OUT/'verification.json').read_text());v.update(status='PASS_pending_graph_visual_review',artifact_checks=checks,input_and_split_sha_still_match=True,negative_platt_slopes=negative,calibration_split='16928 fit / 4232 cal; 169 / 42 positives; same rows every model',model_count=39,scored_rows_per_model=29368);dump(v,'verification.json')
    lines=['# P4C 多视图融合、预训练与深聚类结果','', '已完成 39 个固定预算模型：四个监督融合格、五个预训练格及四个聚类成员后端，各 seed2026/2027/2028。所有 January 客户均评分，所有原始结果保留，没有按一月选择模型/种子/epoch/K。January 已见，只是开发验证。','', '## 共同控制与证据','', '141 个结构原始列分六视图；仅 fit16928 拟合后编码 814 维，视图维度46/507/103/102/42/14。fit16928/169正例，cal4232/42正例；同一 stratified random_state=20261111 切分。所有监督50epoch、batch512、Adam.001、未加权BCE、dropout0，无early-stop。预训练20epoch batch256，随后全参数BCE微调；不是冻结编码器的纯无监督复现。','', 'mean/global/view-attention/column-gate 参数13137/13143/13282/14765；预训练含decoder26975，监督阶段移除decoder。全局6个softmax权重不称样本attention；样本attention为共享16->8->1门；列门是对814个编码列逐列sigmoid(a*x+b)，并非原始141列一一权重。','', 'Platt 只用同4232自然分布cal拟合，所有raw logit/cal概率/校准数据保存private。概率指标允许显示Platt对排序的改变，但容量始终按raw logit排序；如斜率为负，Platt会反转排序，不能把原始排名的捕获指标嫁接到校准后排序。只有42个cal正例，校准斜率本身可能不稳。','', f'负 Platt 斜率格数：{len(negative)}，详见 verification.json 与 run-audit.json；全部保留，没有因表现删掉。','', '## 三种子读数','', '下表为三seed均值；seed-summary.csv保存std/min/max。图中横线仅三次初始化的min/max，不是置信区间，也不证明跨期稳定性。','', '| 候选 | raw Logloss | Platt Logloss | raw AP | Platt AP | raw AUC | K2937 raw-ranking mean | 久单79 raw-ranking mean |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for n in order:
        raw=summary.loc[(n,'raw')];pl=summary.loc[(n,'platt')];cc=rawcap.loc[rawcap.candidate.eq(n)].groupby('policy').hits.mean();lines.append(f'| {n} | {raw[("logloss","mean")]:.6f} | {pl[("logloss","mean")]:.6f} | {raw[("AP","mean")]:.6f} | {pl[("AP","mean")]:.6f} | {raw[("AUC","mean")]:.6f} | {cc["K2937"]:.2f} | {cc["long79"]:.2f} |')
    lines+=['','adjacent-component-differences.csv逐seed保留相邻变化。AE->AE-NCE同时加入双mask增广和InfoNCE，不能把差异单独归因于InfoNCE。mean->AE还增加20epoch无监督预算；AE各格之间预训练预算完全一致。三seed负结果不证明所有注意力/表征方法都无效；不得用其中最优seed宣称稳定提升。','', '## 论文机制与简化','', '已读上轮 paper-transfer.md。本文是MVSIB-inspired适配：同伪簇负对只在InfoNCE分母乘.1，不改正对、不删客户、不用真y判FN；伪簇仅fit-X K3。少数簇按人数<fitN/3，绝不等同复购正类；每个有效batch采P2个对角协方差潜向量，仅无监督潜原型一致性，不赋复购y、不送BCE。最后加入视图/共识同簇均值MSE。','', '没有实现原论文不确定性路由、HN hinge/gate、完整MMD、伪样本排斥或安全边界；原论文符号/门控/中心参照歧义未在本实验擅自声称消解。当前FN、prototype、centroid是明确定义的新简化，不称MVSIB精确复现或理论保证。伪原型生成/跳过次数与簇规模记录run-audit，预训练四分项loss在private。','', '深聚类使用最后一格BCE之前的无监督fit latent，K2..8按fit-only sample2000 silhouette选K，不用cal/Jan/y；各seed K选择与全部候选silhouette见deep-k-selection.csv。hard一热与soft负平方距离温度成员送同线性BCE头50epoch，对照fit-RFM K3 hard/soft。此处变换与KMeans均不与Jan共同拟合。','', '## 文件、复核与执行依赖','', '公开聚合：january-metrics.csv（含自然概率、0.5混淆/precision/recall/F1），january-capacity.csv（raw排名K2937、5/10/20%、共同久单cluster1固定79），seed-summary.csv、adjacent-component-differences.csv、deep-k-selection.csv、fusion-weight-distribution.csv、PNG/SVG。private保留变换参数、OHE、同split键、fit/cal/Jan矩阵、模型、cal数据、全Jan raw logits/两种概率、无监督latent、cluster成员和列门分布。','', '保存模型逐行重评分、全部指标与名单捕获从private回算、输入与split SHA核验均记录verification.json。共同久单权威H05-km3-v1 cluster_id=1、12330/90，非重新KMeans标签。','', '源码是本机执行记录，依赖同目录../features/private两张P2对齐表、feature-views.json及历史H05 validation_clusters.csv；不是独立一键复现包。完整依赖与SHA在input-audit.json，代码按run_representations.py、finalize_representations.py运行；需本机已装PyTorch/sklearn，无安装行为。P2静态属性/支付回写缺日志假设继续适用。P2原五候选使用全部21160训练，本轮仅16928拟合，跨两阶段数值不能解释为单模块效果。','', 'April快照/标签解析0；无源数据/Git/看板写入、无外发、无依赖安装。最终系统正式消融仍待候选冻结后；本实验相邻差异只是预定模块验证。']
    lines+=['','RFMlog 参考的具体口径：本矩阵对 R、F、M 三列全部 log1p，再仅fit训练部分 StandardScaler/KMeans K3；P3/P4A及H05采用R原值、仅logF/logM，因此这里的rfm-hard/rfm-soft不称H05复现，跨矩阵deep对H05的差异不能直接归因于深表征。共同久单诊断仍逐键使用权威H05 cluster_id=1，不由本矩阵RFM重新编号。']
    (OUT/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    files=[{'path':p.relative_to(OUT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p),'private':'private' in p.relative_to(OUT).parts} for p in OUT.rglob('*') if p.is_file() and p.name!='manifest.json'];dump({'files':files,'private_rows_are_not_public':True},'manifest.json');print('VERIFIED',len(checks),'negative_slopes',negative,'files',len(files))

if __name__=='__main__':main()
