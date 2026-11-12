"""Shared loaders, fit-only calibration and identical Jan metrics for all candidates."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
from functools import lru_cache
import json,hashlib,time
import numpy as np,pandas as pd
from scipy import sparse
from scipy.special import expit
from scipy.optimize import minimize
from sklearn.metrics import log_loss,brier_score_loss,average_precision_score,roc_auc_score,confusion_matrix

ROOT=Path(__file__).resolve().parent;SH=ROOT/'shared';KEY=['customer_unique_id','snapshot_date'];A_MIN=1e-6
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def jsonable(x):
 if isinstance(x,dict):return {str(k):jsonable(v) for k,v in x.items()}
 if isinstance(x,(tuple,list)):return [jsonable(v) for v in x]
 if isinstance(x,np.ndarray):return jsonable(x.tolist())
 if isinstance(x,np.generic):return jsonable(x.item())
 if isinstance(x,Path):return str(x)
 if isinstance(x,float) and not np.isfinite(x):return None
 return x
def dump(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(jsonable(x),ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
@lru_cache(None)
def manifest():
 m=json.loads((SH/'data-manifest.json').read_text());assert m['status']=='frozen_shared_data_ready';return m
@lru_cache(None)
def raw_tables():
 m=manifest();cats=m['categorical_fields'];out={}
 for tag in ['oct','jan']:
  p=SH/f'private/{tag}-raw.csv';assert sha(p)==m['raw_data_sha256'][tag]
  out[tag]=pd.read_csv(p,dtype={c:'string' for c in cats+KEY},float_precision='round_trip')
 return out
def load_raw(split_id):
 d=SH/f'private/split-{split_id}';idx=np.load(d/'indices.npz');t=raw_tables()
 return {'fit':t['oct'].iloc[idx['fit']].reset_index(drop=True).copy(),'cal':t['oct'].iloc[idx['cal']].reset_index(drop=True).copy(),'jan':t['jan'].copy(),
         'fields':manifest()['raw_fields'],'categorical_fields':manifest()['categorical_fields']}
@lru_cache(None)
def load_frames(split_id):
 d=SH/f'private/split-{split_id}';idx=np.load(d/'indices.npz');t=raw_tables();cols=KEY+['y','cluster_id','F']
 return {'fit':t['oct'][cols].iloc[idx['fit']].reset_index(drop=True),'cal':t['oct'][cols].iloc[idx['cal']].reset_index(drop=True),'jan':t['jan'][cols].reset_index(drop=True)}
def load_split(split_id,information,dense=False,dtype=np.float64):
 m=manifest();assert split_id in m['split_ids'] and information in m['information'];d=SH/f'private/split-{split_id}'
 desc=m['splits'][str(split_id)];mask=np.load(d/'base8-mask.npy');frames=load_frames(split_id);out={'dims':desc['dims'],'base8_mask':mask,'frames':frames,'split_id':split_id,'information':information,'description':desc}
 for part in ['fit','cal','jan']:
  x=sparse.load_npz(d/f'{part}.npz')
  if information=='base8':x=x.multiply(mask).tocsr();x.eliminate_zeros()
  x=x.astype(dtype)
  out['X_'+part]=x.toarray() if dense else x
  out['y_'+part]=frames[part].y.to_numpy(int)
 assert sum(out['dims'])==out['X_fit'].shape[1] and len(out['y_jan'])==29368
 return out

def fit_monotone_platt(z,y):
 z=np.asarray(z,dtype=np.float64);y=np.asarray(y,dtype=np.float64);assert np.isfinite(z).all() and set(y)=={0,1}
 prior=float(y.mean());initial=np.array([1.,np.log(prior/(1-prior))-float(z.mean())])
 def fun(theta):
  a,b=theta;t=a*z+b;p=expit(t);e=p-y
  return float(np.sum(np.logaddexp(0,t)-y*t)+.5*a*a/1e6),np.array([np.dot(e,z)+a/1e6,e.sum()])
 begin=time.perf_counter();res=minimize(fun,initial,jac=True,method='L-BFGS-B',bounds=[(A_MIN,None),(None,None)],options={'maxiter':1000,'gtol':1e-10,'ftol':1e-14,'maxls':50})
 a,b=map(float,res.x);objective,gradient=fun(res.x);projected=gradient.copy();active=a<=A_MIN+1e-9
 projected[0]=a-max(A_MIN,a-gradient[0])
 assert a>=A_MIN-1e-12 and np.isfinite([a,b,objective]).all()
 return dict(a=a,b=b,objective=objective,gradient=gradient.tolist(),projected_gradient_inf=float(np.max(np.abs(projected))),active_lower_bound=active,success=bool(res.success),message=str(res.message),iterations=int(res.nit),seconds=time.perf_counter()-begin,fit_n=len(y),fit_positives=int(y.sum()),slope_min=A_MIN,penalty_C=1e6)
def apply_calibration(z,cal):return expit(cal['a']*np.asarray(z,dtype=np.float64)+cal['b'])
def order(frame,score):
 return np.lexsort((frame.snapshot_date.to_numpy(str),frame.customer_unique_id.to_numpy(str),-np.asarray(score,dtype=float)))
def metric_rows(frame,p,variant,period):
 rows=[];y=frame.y.to_numpy(int);groups=frame.cluster_id.to_numpy(int)
 masks=[('all',np.ones(len(frame),bool))]+[(f'group{g}',groups==g) for g in [0,1,2]]+[('F1',frame.F.to_numpy()==1)]
 for scope,mask in masks:
  yy=y[mask];pp=np.asarray(p,dtype=float)[mask];pred=pp>=.5;tn,fp,fn,tp=confusion_matrix(yy,pred,labels=[0,1]).ravel()
  rows.append(dict(period=period,variant=variant,scope=scope,n=len(yy),positives=int(yy.sum()),mean_probability=float(pp.mean()),logloss=float(log_loss(yy,pp,labels=[0,1])),brier=float(brier_score_loss(yy,pp)),AP=float(average_precision_score(yy,pp)),AUC=float(roc_auc_score(yy,pp)) if 0<yy.sum()<len(yy) else None,TP=int(tp),FP=int(fp),FN=int(fn),TN=int(tn),F1=float(2*tp/(2*tp+fp+fn)) if 2*tp+fp+fn else 0.,accuracy=float((tp+tn)/len(yy))))
 return rows
def capacity_rows(frame,score,variant,period='jan'):
 rank=order(frame,score);y=frame.y.to_numpy(int);g=frame.cluster_id.to_numpy(int);rows=[]
 for policy,k in [('global2937',2937),('global5',1469),('global20',5874),('long79',79)]:
  ix=rank[g[rank]==1][:k] if policy=='long79' else rank[:k];assert len(ix)==k
  row=dict(period=period,variant=variant,policy=policy,k=k,hits=int(y[ix].sum()),precision=float(y[ix].mean()),recall=float(y[ix].sum()/(90 if policy=='long79' else 230)))
  for group in [0,1,2]:row[f'group{group}_selected']=int((g[ix]==group).sum());row[f'group{group}_hits']=int(y[ix][g[ix]==group].sum())
  rows.append(row)
 return rows

def write_run(output_dir,run_id,family,information,split_id,seed,fit_logits,cal_logits,jan_logits,metadata=None):
 """No fit of a predictive model here; only Octcal calibration and identical diagnostics."""
 out=Path(output_dir);pr=out/'private';pr.mkdir(parents=True,exist_ok=True);frames=load_frames(split_id)
 logits={part:np.asarray(z,dtype=np.float64).reshape(-1) for part,z in [('fit',fit_logits),('cal',cal_logits),('jan',jan_logits)]}
 for part,z in logits.items():assert len(z)==len(frames[part]) and np.isfinite(z).all(),(run_id,part)
 calibration=fit_monotone_platt(logits['cal'],frames['cal'].y.to_numpy())
 probabilities={part:apply_calibration(z,calibration) for part,z in logits.items()}
 raw={part:expit(z) for part,z in logits.items()};fit_y=frames['fit'].y.to_numpy();prior_offset=float(np.log((len(fit_y)-fit_y.sum())/fit_y.sum()))
 arrays={**{part+'_logit':z for part,z in logits.items()},**{part+'_raw':p for part,p in raw.items()},**{part+'_calibrated':p for part,p in probabilities.items()}}
 if family=='weightedLR':arrays.update({part+'_prior':expit(z-prior_offset) for part,z in logits.items()})
 np.savez_compressed(pr/f'{run_id}-scores.npz',**arrays);dump(pr/f'{run_id}-calibration.json',calibration)
 tags=dict(run_id=run_id,family=family,information=information,split_id=int(split_id),seed=None if seed is None else int(seed));metrics=[];capacities=[]
 for period in ['cal','jan']:
  for variant,values in [('raw',raw[period]),('calibrated',probabilities[period])]+([('prior',arrays[period+'_prior'])] if family=='weightedLR' else []):
   metrics.extend(tags|r for r in metric_rows(frames[period],values,variant,period))
   if period=='jan':capacities.extend(tags|r for r in capacity_rows(frames[period],values,variant))
 raw_top=set(order(frames['jan'],logits['jan'])[:2937]);cal_top=set(order(frames['jan'],probabilities['jan'])[:2937])
 record={**tags,'calibration':calibration,'metadata':metadata or {},'shared_manifest_sha256':sha(SH/'data-manifest.json'),'root_plan_sha256':sha(ROOT/'task_plan.md'),'eval_harness_sha256':sha(Path(__file__)),'score_file':str((pr/f'{run_id}-scores.npz').relative_to(ROOT)).replace('\\','/'),'score_sha256':sha(pr/f'{run_id}-scores.npz'),'Jan_raw_vs_calibrated_selected_symmetric_difference':len(raw_top^cal_top),'calibrated_cal_readout':'resubstitution: calibrator fitted on same Octcal labels','raw_weighted_probability_status':'distorted training-prior scale; diagnostic only' if family=='weightedLR' else 'uncalibrated model output','metrics':metrics,'capacities':capacities}
 dump(out/f'{run_id}-record.json',record)
 return record
