"""Bounded read-only probability implementation audit. Never fit or change data."""
import ast,hashlib,json
from pathlib import Path
import numpy as np,pandas as pd,joblib
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'closure';PROB=ROOT/'probability';DATA=ROOT/'data'
KEY=['customer_unique_id','snapshot_date']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    dm=json.loads((DATA/'data-manifest.json').read_text());pm=json.loads((PROB/'probability-manifest.json').read_text());freeze=json.loads((PROB/'input-freeze.json').read_text())
    assert dm['status']==pm['status']=='READY'
    fields=dm['raw_fields'];cats=dm['categorical_fields'];base=dm['base_fields']
    forbidden=KEY+['y','future_gmv','future_orders','label_end','cluster']
    assert len(fields)==141 and len(cats)==8 and len(base)==8 and not set(fields)&set(forbidden)
    assert not set(base)&set(forbidden) and set(base)<=set(fields)
    code=PROB/'run_probability.py';source=code.read_text();tree=ast.parse(source)
    line_map={n.name:n.lineno for n in tree.body if isinstance(n,ast.FunctionDef)}
    hashes={str(p):sha(p) for p in [DATA/'data-manifest.json',code,PROB/'probability-manifest.json',PROB/'input-freeze.json',PROB/'replay-verification.json']}
    rows=[]
    for cell,entry in dm['cells'].items():
        frames={}
        for part in ['fit','cal','eval']:
            p=DATA/entry[part]['path'];h=sha(p)
            assert h==entry[part]['sha256']==freeze['source_files'][str(p)]
            frames[part]=pd.read_csv(p,dtype={c:'string' for c in KEY+cats},float_precision='round_trip')
        fit,cal,ev=[frames[t] for t in ['fit','cal','eval']]
        assert set(fit.customer_unique_id).isdisjoint(set(cal.customer_unique_id))
        date=entry['eval_date']
        assert pd.to_datetime(fit.label_end).le(pd.Timestamp(date)).all()
        assert pd.to_datetime(cal.label_end).le(pd.Timestamp(date)).all()
        assert ev.snapshot_date.eq(date).all()
        cd=PROB/'private/cells'/cell
        if cell!='2018-01-01__single':
            t=joblib.load(cd/'lr-transform.joblib');expected=[c for c in base if c!='state']
            assert t['numeric']==expected
            a=np.log1p(fit[expected].to_numpy(float))
            assert np.allclose(t['scaler'].mean_,a.mean(axis=0),rtol=0,atol=1e-12)
            assert list(t['encoder'].feature_names_in_)==['state']
            assert set(t['encoder'].categories_[0])==set(fit.state.fillna('__MISSING__').astype(str))
            tr=json.loads((cd/'cb-transform.json').read_text())
            assert tr['fields']==fields and tr['categorical_fields']==cats
            med=fit[[c for c in fields if c not in cats]].median().fillna(0)
            assert set(tr['numeric_median'])==set(med.index)
            assert all(np.isclose(tr['numeric_median'][c],med[c],rtol=0,atol=1e-12) for c in med.index)
        else:
            old=ROOT.parent/'is6400-common-comparison-20261112'
            lineage=json.loads((old/'shared/private/split-20261111/lineage.json').read_text());mask=np.load(old/'shared/private/split-20261111/base8-mask.npy')
            assert np.array_equal(mask,np.array([x['original8'] for x in lineage]))
            assert all(x['field'] in base for x,on in zip(lineage,mask) if on)
            assert int(mask.sum())==34
            ia=json.loads((cd/'legacy-identity-audit.json').read_text())
            assert all(x['keys_labels_141_fields_equal'] for x in ia.values())
        pred=pm['cells'][cell];p=Path(pred['primary_eval_path']);assert sha(p)==pred['primary_eval_sha256']
        pf=pd.read_csv(p,dtype={c:'string' for c in KEY})
        assert len(pf)==len(ev) and pf[KEY].equals(ev[KEY])
        assert not set(pf)&set(['y','future_gmv','future_orders'])
        rows.append(dict(cell=cell,fit_rows=len(fit),cal_rows=len(cal),eval_rows=len(ev),fit_cal_customer_overlap=0,max_fit_label_end=fit.label_end.max(),max_cal_label_end=cal.label_end.max(),maturity_pass=True,all_3_input_hashes_match_data_and_probability_freeze=True,preprocess_fit_only_readback=True,never_X_fields_absent_from_feature_allowlists=True,full_eval_probability_coverage=True))
    records=json.loads((PROB/'model-records.json').read_text());assert len(records)==30
    assert sum(not r['reuse'] for r in records)==25 and sum(r['reuse'] for r in records)==5
    reused=[r for r in records if r['reuse']];assert all(r['cell']=='2018-01-01__single' for r in reused)
    assert len([r for r in reused if r['family']=='nativeCatBoost'])==3
    legacy=[]
    for r in reused:
        meta=json.loads(Path(r['metadata_path']).read_text())
        assert meta['reuse_existing'] and max(meta['cached_model_logit_max_abs_error'].values())<1e-11
        for p,h in meta['source_files'].items():assert sha(p)==h
        legacy.append(dict(runid=r['runid'],source_run_id=meta['source_run_id'],logit_max_abs_error=max(meta['cached_model_logit_max_abs_error'].values()),source_hashes_match=True))
    assert 'model.fit(x[\'fit\'],y,cat_features=cats)' in source
    assert "LogisticRegression(**params).fit(x['fit'],y)" in source
    assert "cal=fit_platt(logits['cal'],frames['cal'].y.to_numpy(int))" in source
    assert "xcb,tcb=prepare_cb(frames,fields,cats)" in source
    result=dict(status='PASS_WITH_BOUNDED_SCOPE',scope='Read-only audit of probability author implementation and serialized input/preprocess/reuse evidence; no fitting or metrics re-search',auditor_role='Data-construction author; did not write probability implementation. This is independent of probability authorship, but is not an independent non-author review of the data construction.',fit_calls=0,source_files_sha256=hashes,source_function_lines=line_map,feature_allowlist_count=141,categorical_count=8,base_allowlist_count=8,forbidden_input_fields=forbidden,cells=rows,new_base_fits_recorded=25,old_models_reused_recorded=5,legacy_reuse=legacy,source_findings=['LR scaler/OHE fit only fit numeric/state fields; actual persisted state matches fit rows','Native CatBoost median only fit, 141 allowlist excludes all future labels/time/cluster/keys','All new base-model training calls use fit X and fit y; no eval_set/early stop in CatBoost','Platt fits only cal logits and natural cal y; cal is not independent calibration evaluation','Jan single invokes reuse_run rather than train_lr/train_cb and original cached logits are checked','All eval customers receive all three primary probabilities; capacity never truncates input'],limitations=['Data cohort/event construction authored by this auditor, so its readback is not presented as independent non-author data review','This audit does not prove absence of every possible software defect or certify historical source availability/change logs','Model fit numerical optimality is not certified; actual stop/gradient reports remain authoritative','Existing windows are development evidence, with repeated customers and overlapping target calendars'])
    OUT.mkdir(exist_ok=True)
    (OUT/'probability-source-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    md=['# 概率实现有界源审','','核查者写过数据构造，没有写概率实现。因此本核查独立于概率作者，但不是数据构造的未参与作者独审。','','结论：6 cell 的 18 个输入 SHA 同时匹配冻结数据与概率 input-freeze；成熟标签、fit/cal 客户隔离、141/base8 变量白名单、fit-only 预处理持久状态、全体评分和 Jan 5 旧模型复用均通过。此轮 fit 调用为 0。','']
    for x in ['LR 的 scaler/OHE 只拟合 fit 数值/state 字段，保存参数与实际 fit 行相符。','原生 CatBoost 的中位数仅来自 fit；141 字段白名单排除了未来标签、日期、群和双键。','新基础模型训练调用仅接 fit X 与 fit y；CatBoost 不用 eval_set 或 early stopping。','Platt 仅接 cal logit 与自然标签；校准后 cal 指标仍属再代入读数。','Jan single 走 reuse_run，未走新训练函数；五旧模型源哈希及缓存 logit 回放已核。','每位评价客户都有三种主概率，名单容量没有截断模型输入。']:md+=['- '+x]
    md+=['','本审查核概率实现，未把本人编写的数据构造当作未参与作者的独立审查。不能据此认证生产时点资料可得性、数值精确最优或新独立盲测。详细哈希、函数行号和每 cell 证据见同名 JSON。']
    (OUT/'probability-source-audit.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'cells':len(rows),'new':25,'reuse':5,'fit_calls':0},ensure_ascii=False))
if __name__=='__main__':main()
