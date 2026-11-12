"""Replay saved six amount models, with no fitting or probability dependency."""
from pathlib import Path
import json, hashlib
import numpy as np
import pandas as pd
import joblib

ROOT=Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return pd.read_csv(p,dtype={'customer_unique_id':str,'snapshot_date':str},float_precision='round_trip')
def main():
    stage=json.loads((ROOT/'amount-stage-manifest.json').read_text(encoding='utf-8'))
    assert stage['status']=='READY' and stage['new_amount_fits']==6
    records=[]
    for cell,item in stage['cells'].items():
        for entry in item['inputs'].values(): assert sha(ROOT.parent/'data'/entry['path'])==entry['sha256']
        train=read(ROOT.parent/'data'/item['inputs']['fit']['path']); ev=read(ROOT.parent/'data'/item['inputs']['eval']['path'])
        cal=read(ROOT.parent/'data'/item['inputs']['cal']['path']); pos=train[train.future_gmv>0]
        assert set(train.customer_unique_id).isdisjoint(cal.customer_unique_id)
        assert pd.to_datetime(train.label_end).max()<=pd.Timestamp(cell.split('__')[0])
        assert pd.to_datetime(cal.label_end).max()<=pd.Timestamp(cell.split('__')[0])
        private=ROOT/'private/cells'/cell; info=item['amount_fit']; saved=read(item['eval_prediction_path'])
        assert sha(item['eval_prediction_path'])==item['eval_prediction_sha256']
        assert saved[['customer_unique_id','snapshot_date']].equals(ev[['customer_unique_id','snapshot_date']])
        assert np.isclose(info['positive_G_mean'],pos.future_gmv.mean()) and info['positive_rows']==len(pos)
        if info['fallback']: raw=np.full(len(ev),pos.future_gmv.mean())
        else:
            assert sha(private/'amount-model.joblib')==item['model_sha256']
            obj=joblib.load(private/'amount-model.joblib'); features=['F','M','average_order_value','max_order_value']
            assert np.allclose(obj['scaler'].mean_,np.log1p(pos[features].to_numpy()).mean(axis=0),rtol=1e-13)
            assert obj['model'].alpha==1 and obj['model'].max_iter==2000 and obj['model'].tol==1e-8
            assert obj['target_scale']==pos.future_gmv.mean() and obj['cap']==pos.future_gmv.max()
            raw=obj['model'].predict(obj['scaler'].transform(np.log1p(ev[features].to_numpy())))*obj['target_scale']
        expected=np.clip(raw,0,pos.future_gmv.max())
        assert np.allclose(raw,saved.Ghat_conditional_uncapped,rtol=1e-13)
        assert np.allclose(expected,saved.Ghat_conditional,rtol=1e-13)
        records.append({'cell':cell,'prediction_rows':len(ev),'positive_fit_rows':len(pos),
            'fallback':info['fallback'],'clip_count':int(((raw<0)|(raw>pos.future_gmv.max())).sum()),
            'max_abs_replay_error':float(np.abs(expected-saved.Ghat_conditional.to_numpy()).max())})
    result={'status':'PASS','new_fits':0,'models_replayed':6,'data_manifest_sha256':stage['data_manifest_sha256'],'cells':records}
    (ROOT/'amount-independent-readback.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))

if __name__=='__main__': main()
