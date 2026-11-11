import sys
sys.dont_write_bytecode=True
import json,hashlib,runpy,shutil
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent
ns=runpy.run_path(str(OUT/'run_features.py'));scores=pd.read_csv(OUT/'private/january-scores.csv',dtype={'customer_unique_id':'string'});key=ns['KEY']
h05=OUT.parent.parent/'is6400-h05-january-handoff-20261110/validation_clusters.csv'
assert hashlib.sha256(h05.read_bytes()).hexdigest()=='509e6df79c758be73c693ea63a5e1ff9a33db97bcbc168d218b47dfe02d55f85'
auth=pd.read_csv(h05,dtype={'customer_unique_id':'string'});check=scores.merge(auth,on=key,validate='one_to_one',suffixes=('_saved','_authority'))
assert check.cluster_id_saved.eq(check.cluster_id_authority).all()
assert scores.cluster_id.eq(1).sum()==12330 and scores.loc[scores.cluster_id.eq(1),'y'].sum()==90
archive=OUT/'private/long-slice-mismatch';archive.mkdir(exist_ok=True)
for name in ['january-capacity.csv','README.md','artifact-verification.json']:
    dest=archive/name
    if not dest.exists():shutil.copy2(OUT/name,dest)
metrics=pd.read_csv(OUT/'january-metrics.csv');caps=[]
for name in metrics.candidate:
    _,c=ns['metrics'](scores,scores[name+'_score'].to_numpy(),name);caps.extend(c)
caps=pd.DataFrame(caps);caps.to_csv(OUT/'january-capacity.csv',index=False)
assert caps.loc[caps.candidate.eq('lr8')&caps.policy.eq('long_fixed79'),'hits'].iloc[0]==1
rd=(OUT/'README.md').read_text(encoding='utf-8');lines=rd.splitlines()
for i,line in enumerate(lines):
    if line.startswith('| ') and any(line.startswith('| '+name+' |') for name in metrics.candidate):
        row=line.split('|');name=row[1].strip();row[-2]=' '+str(int(caps.loc[caps.candidate.eq(name)&caps.policy.eq('long_fixed79'),'hits'].iloc[0]))+' ';lines[i]='|'.join(row)
rd='\n'.join(lines)+'\n'
rd=rd.replace('AUC 并非最高，久单79也未超过基线。','AUC 并非最高；共同久单79诊断以修正后的表格为准。')
rd+='\n共同久单切片已纠正：H05-km3-v1 cluster_id=1（12330 人 / 90 正例），权威 validation_clusters.csv SHA 和逐键 cluster 均核对一致；最初误用 cluster=2 的容量/报告存 private/long-slice-mismatch。只重算固定容量，不重训，不变更全局指标。LR8 久单79重新核为 1，与共同基线一致。\n'
(OUT/'README.md').write_text(rd,encoding='utf-8')
fig,ax=plt.subplots(figsize=(9,4.7));caps.pivot(index='candidate',columns='policy',values='hits').plot.barh(ax=ax);ax.set_xlabel('January positives captured');ax.set_title('Global capacities and long group=1 fixed79');ax.grid(axis='x',alpha=.2);ax.legend(loc='lower right');fig.tight_layout();fig.savefig(OUT/'capacity-comparison.png',dpi=160);fig.savefig(OUT/'capacity-comparison.svg');plt.close(fig)
v=json.loads((OUT/'artifact-verification.json').read_text());v['long_group_correction']={'authoritative_cluster_id':1,'n':12330,'positive':90,'authority_sha256':hashlib.sha256(h05.read_bytes()).hexdigest(),'all_saved_cluster_assignments_equal_authority':True,'lr8_fixed79_hits':1,'models_retrained':False};(OUT/'artifact-verification.json').write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
v=json.loads((OUT/'verification.json').read_text());v['feature_spec_sha256']=hashlib.sha256((OUT/'feature-spec-frozen.md').read_bytes()).hexdigest();v['long_slice_corrected_without_retraining']=True;(OUT/'verification.json').write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
print(caps.loc[caps.policy.eq('long_fixed79')].to_string(index=False))
