"""Frozen P4C CPU-only multiview comparisons. No April input; see plan.md."""
import sys
sys.dont_write_bytecode=True
import os
os.environ['OMP_NUM_THREADS']='2';os.environ['MKL_NUM_THREADS']='2'
import argparse,copy,hashlib,json,time,random,warnings,gc
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from torch import nn
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler,OneHotEncoder
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score,log_loss,brier_score_loss,average_precision_score,roc_auc_score,confusion_matrix,precision_recall_fscore_support
from sklearn.linear_model import LogisticRegression
from threadpoolctl import threadpool_limits
import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

torch.set_num_threads(2);torch.set_num_interop_threads(2)
OUT=Path(__file__).resolve().parent;PRIV=OUT/'private';FEATURES=OUT.parent/'features';KEY=['customer_unique_id','snapshot_date']
SEEDS=[2026,2027,2028];SUP=['mean','global','view-attention','column-gate'];PRE=['AE','AE-NCE','AE-NCE-FN','AE-NCE-FN-prototype','AE-NCE-FN-prototype-centroid']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(x,n):(OUT/n).write_text(json.dumps(x,indent=2,ensure_ascii=False,default=str)+'\n',encoding='utf-8')
def csv(x,n):x.to_csv(OUT/n,index=False,lineterminator='\n')
def seed(s):random.seed(s);np.random.seed(s);torch.manual_seed(s)

def prepare():
    spec=json.loads((FEATURES/'feature-views.json').read_text());fields=spec['views']['full-structure'];cats=spec['categorical_columns'];views=spec['logical_views']
    paths=[FEATURES/'private/october-features.csv',FEATURES/'private/january-features.csv'];dtypes={c:'string' for c in cats+KEY}
    tr=pd.read_csv(paths[0],usecols=KEY+['y']+fields,dtype=dtypes);ja=pd.read_csv(paths[1],usecols=KEY+['y']+fields+['cluster_id'],dtype=dtypes)
    assert (len(tr),int(tr.y.sum()),len(ja),int(ja.y.sum()))==(21160,211,29368,230)
    fit,cal=train_test_split(np.arange(len(tr)),test_size=.2,random_state=20261111,stratify=tr.y);fit=np.sort(fit);cal=np.sort(cal)
    assert (len(fit),len(cal))==(16928,4232)
    split=tr[KEY+['y']].copy();split['part']='fit';split.loc[cal,'part']='cal';csv(split,'private/october-split.csv')
    arrays=[[],[],[]];dims=[];metadata={};encoded=[]
    for view,cols in views.items():
        cc=[c for c in cols if c in cats];nc=[c for c in cols if c not in cats]
        v=tr[nc].to_numpy(float);w=ja[nc].to_numpy(float);med=np.nanmedian(v[fit],axis=0);med=np.nan_to_num(med,nan=0.)
        def num(a):
            missing=np.isnan(a).astype(np.float32);z=np.where(np.isnan(a),med,a)
            z=np.where(z>=0,np.log1p(np.maximum(z,0)),z)
            for i,c in enumerate(nc):
                if c.endswith('_lat') or c.endswith('_lng'):z[:,i]=np.where(np.isnan(a[:,i]),med[i],a[:,i])
            return z,missing
        a,am=num(v);b,bm=num(w);scale=StandardScaler().fit(a[fit]);a=scale.transform(a);b=scale.transform(b)
        parts=[np.hstack([a[fit],am[fit]]),np.hstack([a[cal],am[cal]]),np.hstack([b,bm])]
        names=nc+[c+'__missing' for c in nc];ohe=None
        if cc:
            ta=tr[cc].fillna('__MISSING__').astype(str);tb=ja[cc].fillna('__MISSING__').astype(str)
            ohe=OneHotEncoder(min_frequency=20,handle_unknown='infrequent_if_exist',sparse_output=False,dtype=np.float32).fit(ta.iloc[fit])
            for i,x in enumerate([ta.iloc[fit],ta.iloc[cal],tb]):parts[i]=np.hstack([parts[i],ohe.transform(x)])
            names+=list(ohe.get_feature_names_out(cc));joblib.dump(ohe,PRIV/(view+'-ohe.joblib'))
        for target,a in zip(arrays,parts):target.append(a.astype(np.float32))
        dims.append(parts[0].shape[1]);metadata[view]={'raw_fields':cols,'numeric_fields':nc,'categorical_fields':cc,'median':med.tolist(),'scale_mean':scale.mean_.tolist(),'scale_std':scale.scale_.tolist(),'encoded_names':names,'dimension':dims[-1]};encoded+=names
    X=[np.hstack(a) for a in arrays];Y=[tr.y.to_numpy(np.float32)[fit],tr.y.to_numpy(np.float32)[cal],ja.y.to_numpy(np.float32)]
    for part,a,y in zip(['fit','cal','january'],X,Y):np.savez_compressed(PRIV/(part+'-matrix.npz'),X=a,y=y)
    # Authoritative H05 assignment. No rerun KMeans labels for this slice.
    h05=OUT.parent.parent/'is6400-h05-january-handoff-20261110/validation_clusters.csv';assert sha(h05)=='509e6df79c758be73c693ea63a5e1ff9a33db97bcbc168d218b47dfe02d55f85'
    auth=pd.read_csv(h05,dtype={'customer_unique_id':'string'});z=ja[KEY+['cluster_id']].merge(auth,on=KEY,validate='one_to_one',suffixes=('_saved','_h05'));assert z.cluster_id_saved.eq(z.cluster_id_h05).all()
    assert (ja.cluster_id.eq(1).sum(),int(ja.loc[ja.cluster_id.eq(1),'y'].sum()))==(12330,90)
    info={'feature_sha256':{str(p):sha(p) for p in paths+[FEATURES/'feature-views.json']},'fit_n':len(fit),'fit_positive':int(Y[0].sum()),'cal_n':len(cal),'cal_positive':int(Y[1].sum()),'jan_n':len(ja),'jan_positive':int(Y[2].sum()),'dims':dims,'view_order':list(views),'total_encoded':sum(dims),'preprocess_fit':'fit16928 only','metadata':metadata,'encoded_names':encoded,'split_sha256':sha(PRIV/'october-split.csv'),'H05_authority_sha256':sha(h05),'april_snapshot_rows_read':0}
    dump(info,'private/preprocess.json');dump({k:v for k,v in info.items() if k not in ['metadata','encoded_names']},'input-audit.json')
    rfm=[np.log1p(tr[['R','F','M']].to_numpy(float)[i]) for i in [fit,cal]]+[np.log1p(ja[['R','F','M']].to_numpy(float))];rs=StandardScaler().fit(rfm[0]);rfm=[rs.transform(x) for x in rfm];joblib.dump(rs,PRIV/'rfm-scale.joblib')
    return [torch.from_numpy(a) for a in X],[torch.from_numpy(y) for y in Y],dims,tr.iloc[fit].reset_index(drop=True),tr.iloc[cal].reset_index(drop=True),ja,rfm,info

class Model(nn.Module):
    def __init__(self,dims,kind='mean',decoder=False):
        super().__init__();self.dims=dims;self.kind=kind;self.enc=nn.ModuleList([nn.Linear(d,16) for d in dims]);self.head=nn.Linear(16,1)
        if kind=='global':self.weight=nn.Parameter(torch.zeros(len(dims)))
        if kind=='view-attention':self.gate=nn.Sequential(nn.Linear(16,8),nn.Tanh(),nn.Linear(8,1))
        if kind=='column-gate':self.gate_a=nn.Parameter(torch.zeros(sum(dims)));self.gate_b=nn.Parameter(torch.zeros(sum(dims)))
        self.dec=nn.ModuleList([nn.Linear(16,d) for d in dims]) if decoder else None
    def encode(self,x,return_views=False):
        if self.kind=='column-gate':x=x*torch.sigmoid(self.gate_a*x+self.gate_b)
        v=torch.stack([torch.relu(e(q)) for e,q in zip(self.enc,torch.split(x,self.dims,dim=1))],dim=1)
        if self.kind=='global':w=self.weight.softmax(0).expand(len(x),-1)
        elif self.kind=='view-attention':w=self.gate(v).squeeze(-1).softmax(1)
        else:w=torch.full((len(x),len(self.dims)),1/len(self.dims),device=x.device)
        z=(v*w.unsqueeze(-1)).sum(1)
        return (z,v,w) if return_views else z
    def forward(self,x):return self.head(self.encode(x)).squeeze(1)

def inference(m,x,latent=False):
    m.eval()
    with torch.no_grad():return torch.cat([m.encode(b) if latent else m(b) for b in x.split(2048)]).numpy()

def supervised(m,x,y,epochs,s,headonly=False):
    m.train();params=[p for p in m.parameters() if p.requires_grad];opt=torch.optim.Adam(params,lr=.001);gen=torch.Generator().manual_seed(s);hist=[];start=time.time()
    for epoch in range(epochs):
        total=0.;ix=torch.randperm(len(x),generator=gen)
        for b in ix.split(512):
            opt.zero_grad(set_to_none=True);logits=m(x[b]);loss=nn.functional.binary_cross_entropy_with_logits(logits,y[b]);loss.backward();opt.step();total+=float(loss.detach())*len(b)
        hist.append({'epoch':epoch+1,'BCE':total/len(x)})
    return hist,time.time()-start

def nce(z1,z2,labels=None):
    n=len(z1);z=nn.functional.normalize(torch.cat([z1,z2]),dim=1);logits=z@z.T/.2;selfmask=torch.eye(2*n,dtype=torch.bool);positive=(torch.arange(2*n)+n)%(2*n)
    if labels is not None:
        ll=labels.repeat(2);same=ll[:,None].eq(ll[None,:]);same[torch.arange(2*n),positive]=False;logits=logits+torch.where(same,torch.tensor(np.log(.1)),torch.tensor(0.))
    logits=logits.masked_fill(selfmask,-1e9)
    return nn.functional.cross_entropy(logits,positive)

def pretrain(m,x,kind,pseudo,epochs,s):
    gen=torch.Generator().manual_seed(s+901);opt=torch.optim.Adam(m.parameters(),lr=.001);labels=torch.as_tensor(pseudo,dtype=torch.long);counts=np.bincount(pseudo);minor=set(np.flatnonzero(counts<len(pseudo)/3).tolist());hist=[];start=time.time();protoevents=0;skips=0
    for epoch in range(epochs):
        total=np.zeros(4);ix=torch.randperm(len(x),generator=gen);m.train()
        for b in ix.split(256):
            q=x[b];lab=labels[b];opt.zero_grad(set_to_none=True)
            if kind=='AE':z,v,_=m.encode(q,True);za=zb=z
            else:
                qa=q*(torch.rand(q.shape,generator=gen)>.1);qb=q*(torch.rand(q.shape,generator=gen)>.1);za,va,_=m.encode(qa,True);zb,vb,_=m.encode(qb,True);z=(za+zb)/2;v=(va+vb)/2
            target=torch.split(q,m.dims,dim=1);rec=sum(nn.functional.mse_loss(dec(v[:,i]),part) for i,(dec,part) in enumerate(zip(m.dec,target)))/len(m.dims)
            contrast=nce(za,zb,lab if 'FN' in kind else None) if kind!='AE' else z.sum()*0
            proto=z.sum()*0;align=z.sum()*0
            if 'prototype' in kind:
                losses=[]
                for c in minor:
                    zz=z[lab.eq(c)]
                    if len(zz)<2:skips+=1;continue
                    mu=zz.mean(0);var=zz.detach().var(0,unbiased=True)*(2/len(zz))+1e-4;fake=mu.detach()[None,:]+torch.randn((2,16),generator=gen)*torch.sqrt(var)[None,:]
                    losses.append(nn.functional.mse_loss(nn.functional.normalize(mu,dim=0),nn.functional.normalize(fake,dim=1).mean(0)));protoevents+=1
                if losses:proto=torch.stack(losses).mean()
            if 'centroid' in kind:
                losses=[]
                for c in range(3):
                    mask=lab.eq(c)
                    if mask.sum()<2:continue
                    consensus=z[mask].mean(0)
                    for vi in range(6):losses.append(nn.functional.mse_loss(v[mask,vi].mean(0),consensus))
                if losses:align=torch.stack(losses).mean()
            loss=rec+.005*contrast+.005*proto+.005*align;loss.backward();opt.step();total+=np.array([float(t.detach()) for t in [rec,contrast,proto,align]])*len(b)
        hist.append(dict(epoch=epoch+1,reconstruction=total[0]/len(x),InfoNCE=total[1]/len(x),prototype=total[2]/len(x),centroid=total[3]/len(x)))
    return hist,time.time()-start,{'pseudo_counts':counts.tolist(),'minority_pseudo_clusters':sorted(minor),'prototype_generated_events':protoevents,'prototype_skipped_cluster_batches':skips,'pseudo_has_y':False}

def measures(ja,p,rank,name,s,prob):
    y=ja.y.to_numpy();pred=p>=.5;tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel();pr,re,f1,_=precision_recall_fscore_support(y,pred,average='binary',zero_division=0)
    r=dict(candidate=name,seed=s,probability=prob,n=len(y),positives=int(y.sum()),logloss=log_loss(y,p),brier=brier_score_loss(y,p),AP=average_precision_score(y,p),AUC=roc_auc_score(y,p),mean_probability=float(p.mean()),precision05=pr,recall05=re,F105=f1,TP=int(tp),FP=int(fp),FN=int(fn),TN=int(tn));order=np.lexsort((ja.customer_unique_id.to_numpy(str),-rank));caps=[]
    for policy,k in [('K2937',2937),('capacity5',1469),('capacity10',2937),('capacity20',5874),('long79',79)]:
        ix=order[ja.cluster_id.to_numpy()[order]==1][:79] if policy=='long79' else order[:k];hit=int(y[ix].sum());caps.append(dict(candidate=name,seed=s,probability=prob,ranking='raw_logits',policy=policy,k=k,hits=hit,precision=hit/k,recall=hit/(90 if policy=='long79' else 230)))
    return r,caps

def save_evaluate(m,x,y,ja,name,s,results,capacity,runaudit,history,seconds,extra=None):
    tick=time.time();cal=inference(m,x[1]);raw=inference(m,x[2]);sig=1/(1+np.exp(-np.clip(raw,-50,50)));platt=LogisticRegression(C=1e6,solver='lbfgs',max_iter=2000).fit(cal[:,None],y[1].numpy());p=platt.predict_proba(raw[:,None])[:,1]
    for prob,pp in [('raw',sig),('platt',p)]:r,c=measures(ja,pp,raw,name,s,prob);results.append(r);capacity+=c
    scores=ja[KEY+['y','cluster_id']].copy();scores['raw_logit']=raw;scores['raw_probability']=sig;scores['platt_probability']=p;csv(scores,f'private/{name}-{s}-january-scores.csv')
    csv(pd.DataFrame({'cal_logit':cal,'cal_y':y[1].numpy()}),f'private/{name}-{s}-calibration.csv');torch.save(m.state_dict(),PRIV/f'{name}-{s}.pt');joblib.dump(platt,PRIV/f'{name}-{s}-platt.joblib')
    a=dict(candidate=name,seed=s,parameters=sum(p.numel() for p in m.parameters()),trainable_parameters=sum(p.numel() for p in m.parameters() if p.requires_grad),supervision_seconds=seconds,inference_seconds=time.time()-tick,platt_slope=float(platt.coef_[0,0]),platt_intercept=float(platt.intercept_[0]),negative_platt_slope=bool(platt.coef_[0,0]<0),extra=extra or {})
    runaudit.append(a);csv(pd.DataFrame(history),f'private/{name}-{s}-loss.csv');csv(pd.DataFrame(results),'january-metrics.csv');csv(pd.DataFrame(capacity),'january-capacity.csv');dump(runaudit,'run-audit.json');print('DONE',name,s,'raw',results[-2]['logloss'],results[-2]['AP'],'platt',results[-1]['logloss'],results[-1]['AP'],'sec',seconds,flush=True)

def cluster_input(a,others,k,s):
    km=KMeans(n_clusters=k,n_init=10,random_state=s).fit(a);dist=[km.transform(v)**2 for v in [a]+others];temperature=max(float(np.median(dist[0])),1e-6)
    hard=[np.eye(k,dtype=np.float32)[d.argmin(1)] for d in dist];soft=[]
    for d in dist:
        v=-d/temperature;v-=v.max(1,keepdims=True);v=np.exp(v);soft.append((v/v.sum(1,keepdims=True)).astype(np.float32))
    return hard,soft,km,temperature

def main(pilot=False):
    begun=time.time();x,y,dims,fitrows,calrows,ja,rfm,info=prepare();print('MATRIX',dims,sum(dims),[len(q) for q in x],info['fit_positive'],info['cal_positive'],flush=True)
    if pilot:
        timings=[];seed(2026);pseudo=KMeans(n_clusters=3,n_init=10,random_state=2026).fit_predict(x[0].numpy())
        for kind in SUP:
            seed(2026);m=Model(dims,kind);_,seconds=supervised(m,x[0],y[0],2,2026);timings.append(dict(kind=kind,epochs=2,seconds=seconds,parameters=sum(p.numel() for p in m.parameters())))
        for kind in ['AE','AE-NCE-FN-prototype-centroid']:
            seed(2026);m=Model(dims,decoder=True);_,seconds,_=pretrain(m,x[0],kind,pseudo,2,2026);timings.append(dict(kind=kind,epochs=2,seconds=seconds,parameters=sum(p.numel() for p in m.parameters())))
        dump({'timings':timings,'total_input_prepare_and_pilot_seconds':time.time()-begun,'estimated_supervised27_seconds':max(t['seconds'] for t in timings[:4])*25*27,'estimated_pretrain15_seconds':max(t['seconds'] for t in timings[4:])*10*15,'deep_cluster_heads_and_silhouette_not_estimated':True,'formal_models_trained':False},'pilot-timing.json');print('PILOT',timings,flush=True);return
    results=[];capacity=[];runaudit=[];clusterrows=[];weights=[]
    for s in SEEDS:
        for kind in SUP:
            seed(s);m=Model(dims,kind);hist,seconds=supervised(m,x[0],y[0],50,s)
            with torch.no_grad():
                _,_,ww=m.encode(x[0],True)
                for i,v in enumerate(info['view_order']):weights.append(dict(candidate=kind,seed=s,view=v,weight_mean=float(ww[:,i].mean()),weight_std=float(ww[:,i].std()),weight_q05=float(torch.quantile(ww[:,i],.05)),weight_q95=float(torch.quantile(ww[:,i],.95))))
            save_evaluate(m,x,y,ja,kind,s,results,capacity,runaudit,hist,seconds)
        pseudo=KMeans(n_clusters=3,n_init=10,random_state=s).fit_predict(x[0].numpy());np.save(PRIV/f'pseudo-labels-{s}.npy',pseudo)
        final_unsup=None
        for kind in PRE:
            seed(s);m=Model(dims,decoder=True);hist,seconds,diag=pretrain(m,x[0],kind,pseudo,20,s);csv(pd.DataFrame(hist),f'private/{kind}-{s}-pretrain-loss.csv');torch.save(m.state_dict(),PRIV/f'{kind}-{s}-pretrained.pt')
            z=[inference(m,v,latent=True) for v in x]
            if kind==PRE[-1]:final_unsup=z
            # Decoder no longer participates in supervised computation. Drop it so parameter count equals mean baseline.
            m.dec=None;hist2,seconds2=supervised(m,x[0],y[0],50,s)
            save_evaluate(m,x,y,ja,kind,s,results,capacity,runaudit,hist2,seconds2,{'pretrain_seconds':seconds,'pretrain_diagnostic':diag,'pretrain_epochs':20,'finetuned_encoder':True})
        for part,zz in zip(['fit','cal','january'],final_unsup):np.save(PRIV/f'final-unsupervised-{s}-{part}-latent.npy',zz)
        choices=[]
        for k in range(2,9):
            km=KMeans(n_clusters=k,n_init=10,random_state=s).fit(final_unsup[0]);sil=silhouette_score(final_unsup[0],km.labels_,sample_size=min(2000,len(x[0])),random_state=20261111);choices.append((k,sil));clusterrows.append(dict(seed=s,K=k,silhouette=sil,population='fit_only_unsupervised_final_pretraining_latent'))
        best=sorted(choices,key=lambda q:(-q[1],q[0]))[0][0];print('CHOSEN_K',s,best,choices,flush=True)
        for representation,zz,k in [('deep',final_unsup,best),('rfm',rfm,3)]:
            hard,soft,km,temp=cluster_input(zz[0],zz[1:],k,s);joblib.dump(km,PRIV/f'{representation}-kmeans-{s}.joblib')
            for membership,data in [('hard',hard),('soft',soft)]:
                name=f'{representation}-{membership}';seed(s);head=nn.Linear(k,1)
                class Flat(nn.Module):
                    def __init__(self,h):super().__init__();self.head=h
                    def forward(self,q):return self.head(q).squeeze(1)
                m=Flat(head);tx=[torch.from_numpy(v) for v in data];hist,seconds=supervised(m,tx[0],y[0],50,s)
                for part,v in zip(['fit','cal','january'],data):np.save(PRIV/f'{name}-{s}-{part}-memberships.npy',v)
                save_evaluate(m,tx,y,ja,name,s,results,capacity,runaudit,hist,seconds,{'K':k,'temperature':temp,'fit_cluster_counts':np.bincount(km.labels_).tolist(),'latent':'unsupervised pretrain before BCE' if representation=='deep' else 'RFM logscale fit only'})
        csv(pd.DataFrame(clusterrows),'deep-k-selection.csv');csv(pd.DataFrame(weights),'fusion-weight-distribution.csv')
    result=pd.DataFrame(results);aggregate=result.groupby(['candidate','probability'])[['logloss','brier','AP','AUC']].agg(['mean','std','min','max']);aggregate.to_csv(OUT/'seed-summary.csv')
    dump({'status':'models_complete_pending_artifact_verification','trained_models':len(runaudit),'supervised_epochs':50,'pretrain_epochs':20,'seeds':SEEDS,'elapsed_seconds':time.time()-begun,'april_snapshot_rows_read':0,'plan_sha256':sha(OUT/'plan.md'),'input_sha256':info['feature_sha256']},'verification.json');print('COMPLETE',len(runaudit),time.time()-begun,flush=True)

if __name__=='__main__':
    arg=argparse.ArgumentParser();arg.add_argument('--pilot',action='store_true');args=arg.parse_args()
    with threadpool_limits(limits=2):main(args.pilot)
