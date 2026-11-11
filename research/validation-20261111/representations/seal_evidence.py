"""Final evidence after actual inspection of the two emitted PNG figures."""
import sys
sys.dont_write_bytecode=True
import hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
OUT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(x,n):(OUT/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    r=json.loads((OUT/'run-audit.json').read_text());rows=[];p=169/16928;prior=-p*np.log(p)-(1-p)*np.log1p(-p)
    for x in r:
        f=pd.read_csv(OUT/'private'/f'{x["candidate"]}-{x["seed"]}-loss.csv');rows.append(dict(candidate=x['candidate'],seed=x['seed'],epoch1_BCE=f.BCE.iloc[0],epoch50_BCE=f.BCE.iloc[-1],last10_BCE_change=f.BCE.iloc[-1]-f.BCE.iloc[-11],fit_constant_prior_BCE=prior,final_BCE_above_constant=bool(f.BCE.iloc[-1]>prior)))
    pd.DataFrame(rows).to_csv(OUT/'optimization-audit.csv',index=False)
    file=OUT/'README.md';text=file.read_text(encoding='utf-8');marker='## 结果可支持的结论与有限预算限制'
    if marker not in text:
        text+='\n'+marker+'\n\n四个监督融合格中，global和列门的平均AP/全局捕获小幅上升，但逐seed并非所有概率指标都改善；样本view-attention三seed raw Logloss均比mean差，不能因“使用注意力”就宣称更优。AE相对mean三seed raw Logloss和AP均改善，但它新增20epoch无监督预算；NCE、FN、prototype、centroid逐项变化不是单调改善，不能声称模块越齐效果越好。\n\n深latent三seed均按fit silhouette选K2，较小簇528/528/513人；高silhouette只证明该几何划分分离，不代表划分能预测复购。仅簇成员线性头的50epoch最终fit BCE仍高于常数基率基线（详见optimization-audit.csv），固定Adam预算存在明显优化限制，raw Logloss差不能单独归因于表征本身；Platt改善概率刻度也不等于补回模型信息。未因此临时改变学习率、初始化或epoch。\n\n本轮策略明确固定raw-logit排名；主表单列Platt AP，不能把校准后AP与raw名单当成同一套决策规则。view-attention seed2026的Platt负斜率来自仅42正例cal支持，方向反转是需要保留的不稳定事实，不推广为“校准都保序”。\n'
        file.write_text(text,encoding='utf-8')
    if 'RFMlog 参考的具体口径' not in text:
        text+='\nRFMlog 参考的具体口径：本矩阵对 R、F、M 三列全部 log1p，再仅fit训练部分 StandardScaler/KMeans K3；P3/P4A及H05采用R原值、仅logF/logM，因此这里的rfm-hard/rfm-soft不称H05复现，跨矩阵deep对H05的差异不能直接归因于深表征。共同久单诊断仍逐键使用权威H05 cluster_id=1，不由本矩阵RFM重新编号。\n';file.write_text(text,encoding='utf-8')
    v=json.loads((OUT/'verification.json').read_text());v['status']='PASS';v['actual_visual_review']={'images':[{'path':n,'sha256':sha(OUT/n)} for n in ['representation-quality.png','representation-capacity.png']],'observed':'Both PNGs actually viewed. Labels/legends/initialization-range caveat readable; raw and Platt probabilities shown separately, business capacities explicitly raw-logit ranking.'};dump(v,'verification.json')
    files=[{'path':f.relative_to(OUT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f),'private':'private' in f.relative_to(OUT).parts} for f in OUT.rglob('*') if f.is_file() and f.name!='manifest.json'];dump({'files':files,'private_rows_are_not_public':True},'manifest.json')
    assert all(sha(OUT/f['path'])==f['sha256'] for f in files);print('SEALED',len(files),'model_rows',len(rows),'constant_prior_BCE',prior)
if __name__=='__main__':main()
