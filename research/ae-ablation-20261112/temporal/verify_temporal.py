"""Independent readback. No predictive fitting, no calibrator fitting, no new windows."""
import sys
sys.dont_write_bytecode=True
import hashlib,json
from pathlib import Path
import numpy as np,pandas as pd,joblib,torch
import torch.nn.functional as F
from scipy import sparse
from scipy.special import expit
from catboost import CatBoostClassifier
from sklearn.metrics import log_loss,brier_score_loss,average_precision_score,roc_auc_score
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent;PR=OUT/'private';KEY=['customer_unique_id','snapshot_date'];BASE=['R','F','M','average_item_rows','freight_share','recent30_orders','recent30_spend','state']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(name,value):(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
def main():
    torch.set_num_threads(2)
    frozen=json.loads((OUT/'source-freeze.json').read_text());assert all(sha(p)==h for p,h in frozen['source_sha256'].items())
    idx=np.load(PR/'indices.npz');cats=frozen['categorical_fields'];fields=frozen['fields'];raw={}
    for part,file in [('july','july-full141.csv'),('oct','october-full141.csv')]:raw[part]=pd.read_csv(OUT.parent/'time-audit/private'/file,dtype={c:'string' for c in KEY+cats},float_precision='round_trip')
    july,oct=raw['july'],raw['oct'];frames={'fit':july.iloc[idx['fit']].reset_index(drop=True),'cal':july.iloc[idx['cal']].reset_index(drop=True),'oct':oct}
    keys={p:pd.read_csv(PR/(p+'-rowkeys.csv'),dtype={c:'string' for c in KEY}) for p in frames}
    assert [len(frames[p]) for p in ['fit','cal','oct']]==[11209,2803,21160]
    for p in frames:
        assert frames[p][KEY].astype('string').equals(keys[p][KEY].astype('string'));assert np.array_equal(frames[p].y,keys[p].y)
    # Rebuild transformed values from saved fit-only objects; verify their learned fit statistics independently.
    transformers=joblib.load(PR/'transformers.joblib');blocks={p:[] for p in frames};transform_errors=[]
    for view,transform in transformers.items():
        nums=transform['numeric'];a=frames['fit'][nums].to_numpy(float)
        with np.errstate(all='ignore'):median=np.nanmedian(a,axis=0)
        median=np.nan_to_num(median,nan=0.);assert np.allclose(median,transform['median'],equal_nan=True)
        filled=np.where(np.isnan(a),median,a);fitx=np.where(filled>=0,np.log1p(np.maximum(filled,0)),filled);fitx[:,transform['raw_indices']]=filled[:,transform['raw_indices']]
        assert np.allclose(fitx.mean(0),transform['scaler'].mean_,rtol=1e-10,atol=1e-10);assert int(transform['scaler'].n_samples_seen_)==11209
        for p,fr in frames.items():
            v=fr[nums].to_numpy(float);missing=np.isnan(v);fill=np.where(missing,median,v);x=np.where(fill>=0,np.log1p(np.maximum(fill,0)),fill);x[:,transform['raw_indices']]=fill[:,transform['raw_indices']]
            x=(x-transform['scaler'].mean_)/transform['scaler'].scale_;pieces=[sparse.csr_matrix(np.hstack([x,missing[:,transform['flag_indices']].astype(float)]))]
            for encdata in transform['encoders'].values():
                cols=encdata['fields'];encoder=encdata['encoder'];expected=frames['fit'][cols].fillna('__MISSING__').astype(str)
                for c,categories in zip(cols,encoder.categories_):assert set(expected[c].unique())==set(categories)
                pieces.append(encoder.transform(fr[cols].fillna('__MISSING__').astype(str)))
            blocks[p].append(sparse.hstack(pieces,format='csr'))
    matrices={p:sparse.load_npz(PR/(p+'-full141.npz')).toarray() for p in frames}
    for p in frames:
        calculated=sparse.hstack(blocks[p],format='csr').toarray();diff=float(np.max(np.abs(calculated-matrices[p])));assert diff<1e-11;transform_errors.append(dict(part=p,max_abs_error=diff))
    mask=np.load(PR/'base8-mask.npy');lineage=json.loads((PR/'lineage.json').read_text());assert np.array_equal(mask,np.array([r['field'] in BASE and r['kind']!='missing' for r in lineage]))
    assert not set(r['field'] for r in lineage)&set(KEY+['y','cluster_id'])
    nativeinfo=json.loads((PR/'native-preprocess.json').read_text());num=[c for c in fields if c not in cats];med=frames['fit'][num].median().fillna(0.);assert all(np.isclose(med[c],v) for c,v in nativeinfo['numeric_median'].items());native={}
    for p,fr in frames.items():
        v=fr[fields].copy();v[num]=v[num].astype(float).fillna(med)
        for c in cats:v[c]=v[c].fillna('__MISSING__').astype(str)
        native[p]=v
    support=pd.read_csv(OUT/'run-support.csv');assert len(support)==13;forward=[];allprob={};independent_logits={}
    for row in support.itertuples():
        folder=PR/row.run;saved=np.load(folder/'scores.npz');cal=json.loads((folder/'calibrator.json').read_text());assert (cal['fit_n'],cal['fit_positives'])==(2803,24) and cal['a']>=1e-6-1e-12
        independent_logits[row.run]={};allprob[row.run]={}
        if row.family=='weightedLR':model=joblib.load(folder/'model.joblib')
        elif row.family in ['encodedCB','nativeCB']:model=CatBoostClassifier();model.load_model(str(folder/'model.cbm'))
        else:
            state=torch.load(folder/'model.pt',map_location='cpu',weights_only=False);weights=state['state_dict'];dims=state['dims']
        for p in frames:
            if row.family=='weightedLR':logits=model.decision_function(matrices[p]*mask)
            elif row.family in ['encodedCB','nativeCB']:logits=model.predict(matrices[p] if row.family=='encodedCB' else native[p],prediction_type='RawFormulaVal',thread_count=2)
            else:
                values=[]
                with torch.no_grad():
                    for batch in torch.from_numpy(matrices[p].astype(np.float32)).split(2048):
                        branches=[torch.relu(F.linear(block,weights[f'enc.{i}.weight'],weights[f'enc.{i}.bias'])) for i,block in enumerate(torch.split(batch,dims,dim=1))]
                        latent=(torch.stack(branches,dim=1)*(1/len(dims))).sum(1);values.append(F.linear(latent,weights['head.weight'],weights['head.bias']).squeeze(1))
                logits=torch.cat(values).numpy().astype(np.float64)
            diff=float(np.max(np.abs(logits-saved[p+'_logit'])));assert diff<1e-6,(row.run,p,diff)
            probability=expit(cal['a']*logits+cal['b']);pdiff=float(np.max(np.abs(probability-saved[p+'_calibrated'])));assert pdiff<1e-7
            allprob[row.run][p]=saved[p+'_calibrated'];independent_logits[row.run][p]=logits;forward.append(dict(run=row.run,part=p,logit_max_abs_error=diff,probability_max_abs_error=pdiff))
    for family in ['mean','AE','encodedCB','nativeCB']:
        name=family+'__full141__seedmean';scores=np.load(PR/(name+'-probabilities.npz'));allprob[name]={}
        for p in frames:
            expected=np.mean([allprob[f'{family}__full141__s{s}'][p] for s in [2026,2027,2028]],axis=0);assert np.array_equal(expected,scores[p]);allprob[name][p]=scores[p]
    # Independent metric formulas/readout, and a different stable sorting implementation.
    mtab=pd.read_csv(OUT/'october-metrics.csv');ctab=pd.read_csv(OUT/'october-capacity.csv');fr=keys['oct'];y=fr.y.to_numpy(int);group=fr.cluster_id.to_numpy(int);metricchecks=0;capacitychecks=0
    lr='weightedLR__base8__s2026';prioroffset=np.log((11209-96)/96)
    for system in allprob:
        variants={'calibrated':allprob[system]['oct']}
        if system==lr:variants|={'raw':expit(independent_logits[system]['oct']),'prior':expit(independent_logits[system]['oct']-prioroffset)}
        for variant,prob in variants.items():
            for scope,mask_scope in [('all',np.ones(len(y),bool)),('group0',group==0),('group1',group==1),('group2',group==2),('long',group==1)]:
                yy=y[mask_scope];pp=prob[mask_scope];expected={'n':len(yy),'positives':int(yy.sum()),'mean_probability':float(pp.mean()),'logloss':log_loss(yy,pp,labels=[0,1]),'brier':brier_score_loss(yy,pp),'AP':average_precision_score(yy,pp),'AUC':roc_auc_score(yy,pp)}
                r=mtab.loc[mtab.system.eq(system)&mtab.variant.eq(variant)&mtab.scope.eq(scope)];assert len(r)==1
                assert all(np.isclose(r.iloc[0][k],v,rtol=1e-10,atol=1e-12) for k,v in expected.items());metricchecks+=1
            ranked=fr.assign(score=prob,original_index=np.arange(len(fr))).sort_values(['score','customer_unique_id','snapshot_date'],ascending=[False,True,True],kind='mergesort')
            for policy,k in [('global10',2116),('global5',1058),('global20',4232),('long79',79)]:
                chosen=ranked.loc[ranked.cluster_id.eq(1)].head(k) if policy=='long79' else ranked.head(k);indices=chosen.original_index.to_numpy();r=ctab.loc[ctab.system.eq(system)&ctab.variant.eq(variant)&ctab.policy.eq(policy)];assert len(r)==1;r=r.iloc[0]
                den=78 if policy=='long79' else 211;assert r.k==k and r.hits==int(y[indices].sum()) and np.isclose(r.recall,y[indices].sum()/den)
                for g in [0,1,2]:assert r[f'group{g}_selected']==int((group[indices]==g).sum()) and r[f'group{g}_hits']==int(y[indices][group[indices]==g].sum())
                capacitychecks+=1
    assert metricchecks==95 and capacitychecks==76
    pd.DataFrame(forward).to_csv(OUT/'independent-forward-checks.csv',index=False)
    primary=[lr]+[f+'__full141__seedmean' for f in ['mean','AE','encodedCB','nativeCB']];tab=mtab.loc[mtab.system.isin(primary)&mtab.variant.eq('calibrated')].copy();tab.to_csv(OUT/'primary-october-metrics.csv',index=False)
    ctab.loc[ctab.system.isin(primary)&ctab.variant.eq('calibrated')].to_csv(OUT/'primary-october-capacity.csv',index=False)
    # Fixed primary systems only; no chosen best seed or model-based iteration.
    plot=tab.loc[tab.scope.eq('all')].set_index('system').reindex(primary);fig,axs=plt.subplots(1,3,figsize=(13,4.2))
    labels=['WLR base8','Mean full141','AE20+50 full141','Encoded CB','Native CB']
    for ax,col,title in zip(axs,['logloss','brier','AP'],['October log loss','October Brier','October AP']):ax.barh(labels,plot[col]);ax.set_title(title);ax.grid(axis='x',alpha=.2)
    fig.tight_layout();fig.savefig(OUT/'temporal-comparison.png',dpi=150);fig.savefig(OUT/'temporal-comparison.svg');plt.close(fig)
    sc=pd.read_csv(OUT/'supervised-curves.csv');pc=pd.read_csv(OUT/'pretrain-curves.csv');fig,axs=plt.subplots(1,2,figsize=(12,4.3))
    for (family,seed),g in sc.groupby(['family','seed']):axs[0].plot(g.epoch,g.online_mean_BCE,label=f'{family} s{seed}',alpha=.8)
    for seed,g in pc.groupby('seed'):axs[1].plot(g.epoch,g.online_view_mean_MSE,label=f'AE s{seed}')
    axs[0].set_title('July-fit online supervised BCE');axs[1].set_title('July-fit online reconstruction MSE')
    for ax in axs:ax.set_xlabel('Epoch');ax.legend(fontsize=8);ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(OUT/'temporal-training-curves.png',dpi=150);fig.savefig(OUT/'temporal-training-curves.svg');plt.close(fig)
    dump('verification.json',dict(status='independent_readback_pass',models=13,AE_pretraining_runs=3,model_period_forward_checks=len(forward),metric_scope_rows_recomputed=metricchecks,capacity_rows_recomputed=capacitychecks,transform_errors=transform_errors,max_forward_logit_error=max(r['logit_max_abs_error'] for r in forward),max_calibrated_probability_error=max(r['probability_max_abs_error'] for r in forward),source_frozen_unchanged=True,Oct_fitted=False,April_rows=0))
    dump('outputhash.json',{str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='outputhash.json'})
    print(json.dumps(dict(models=13,metricchecks=metricchecks,capacitychecks=capacitychecks,primary_all=plot[['logloss','brier','AP']].to_dict('index')),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
