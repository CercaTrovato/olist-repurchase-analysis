import sys
sys.dont_write_bytecode=True
import json,hashlib,runpy
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import sparse
import joblib
from sklearn.metrics import log_loss,brier_score_loss,average_precision_score,roc_auc_score
OUT=Path(__file__).resolve().parent
LONG_CLUSTER=1
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(x,n):(OUT/n).write_text(json.dumps(x,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
def main():
    spec=json.loads((OUT/'feature-views.json').read_text(encoding='utf-8'))
    train=pd.read_csv(OUT/'private/october-features.csv',dtype={**{k:'string' for k in spec['keys']},**{c:'string' for c in spec['categorical_columns']}})
    jan=pd.read_csv(OUT/'private/january-features.csv',dtype={**{k:'string' for k in spec['keys']},**{c:'string' for c in spec['categorical_columns']}})
    fields=spec['views']['full-structure'];groups={k:[] for k in ['behavior','geography','products','commerce','service','seller_context']};definitions={}
    for c in fields:
        if c in spec['views']['lr8'] or c in ['average_order_value','max_order_value','observed_history_days']:g='behavior';s='H02-v2-candidate-reviewed historical feature'
        elif c in spec['views']['lr8-geo']:g='geography';s='Customer/seller static locality; deduplicated postcode median lat/lng; 6371.0088-km Haversine, item-weighted history and last-order item mean'
        elif c.startswith('seller_other_'):g='seller_context';s='Snapshot-history seller context excluding focal customer; smoothed repeat is (other repeats+1)/(other buyers+20)'
        elif any(c.startswith(k) for k in ['review_','known_','latest_known_','last_order_late','delivery_','carrier_','in_transit']):g='service';s='Only actual event/valid answered review earlier than snapshot; missing is not treated as on-time/good review'
        elif any(c.startswith(k) for k in ['product_','historical_category','categories_']):g='products';s='Purchased-item product attributes or as-of raw product-ID order frequency; static attribute assumption'
        else:g='commerce';s='Approved-order historical basket/payment/date/price/freight summaries; payments/deadlines have no change log'
        groups[g].append(c);typ='categorical' if c in spec['categorical_columns'] else 'numeric'
        definitions[c]={'view':g,'dtype':typ,'meaning':s,'aggregation':('mean/max/sample-std suffix over historical records (items for product/price/freight/shipping; orders for payment/date; valid reviews for review)' if c.endswith(('_mean','_max','_std')) else 'See run_features.py named-column construction; last_* uses last approved order, locality first item by item ID'),'eligibility':'6-month window: approval>=t-6months and approval<t and item-price-sum>0; all H02 customer rows retained','missing_policy':'Train median + fixed indicator (LR), train median (CatBoost); categorical __MISSING__; unknown categories train-only rare OHE'}
    assert sum(map(len,groups.values()))==141 and len(set(sum(groups.values(),[])))==141
    spec['logical_views']=groups;spec['column_definitions']=definitions
    spec['numeric_transform']='LR: median fit October; nonnegative log1p, negative values unchanged; latitude/longitude unchanged; train StandardScaler; fixed missing flag for every numeric field'
    spec['encoded_handoff']='private/*-october-matrix.npz / *-january-matrix.npz are train-fitted matching column order; do not concatenate y/cluster to them'
    dump(spec,'feature-views.json')
    scores=pd.read_csv(OUT/'private/january-scores.csv',dtype={'customer_unique_id':'string'});metrics=pd.read_csv(OUT/'january-metrics.csv');caps=pd.read_csv(OUT/'january-capacity.csv');runs=json.loads((OUT/'run-audit.json').read_text())
    assert not train.duplicated(spec['keys']).any() and not jan.duplicated(spec['keys']).any()
    assert (len(train),int(train.y.sum()),len(jan),int(jan.y.sum()))==(21160,211,29368,230)
    assert all(c not in fields for c in ['y','cluster_id','cluster_version','split','data_version','past_review_text'])
    checks=[]
    for row in metrics.itertuples():
        p=scores[row.candidate+'_score'].to_numpy();y=scores.y.to_numpy();expected=[log_loss(y,p),brier_score_loss(y,p),average_precision_score(y,p),roc_auc_score(y,p)]
        assert np.allclose(expected,[row.logloss,row.brier,row.AP,row.AUC],rtol=1e-10,atol=1e-12)
        if row.candidate!='structure-catboost':
            model=joblib.load(OUT/'private'/(row.candidate+'-lr.joblib'));mat=sparse.load_npz(OUT/'private'/(row.candidate+'-january-matrix.npz'));pred=model.predict_proba(mat)[:,1];assert np.max(np.abs(pred-p))<1e-12
        order=np.lexsort((scores.customer_unique_id.to_numpy(str),-p))
        for c in caps.loc[caps.candidate.eq(row.candidate)].itertuples():
            ix=order[scores.cluster_id.to_numpy()[order]==LONG_CLUSTER][:79] if c.policy=='long_fixed79' else order[:c.k]
            assert len(ix)==c.k and int(y[ix].sum())==c.hits
        checks.append({'candidate':row.candidate,'metrics_and_capacities_recomputed':True,'serialized_lr_matrix_scores_reproduced':row.candidate!='structure-catboost'})
    catalog=pd.read_csv(OUT/'field-catalog-52.csv');assert len(catalog)==52 and len(catalog[['table','position']].drop_duplicates())==52
    missing=pd.read_csv(OUT/'missing-schema-audit.csv');source=json.loads((OUT/'source-audit.json').read_text());audit=json.loads((OUT/'feature-audit.json').read_text());status=catalog.status.value_counts().to_dict()
    # Independently rerun previously audited cache builders, matching only their allowlisted X fields.
    ns=runpy.run_path(str(OUT/'run_features.py'));orders,items,pay,reviews,_=ns['load']()
    service=runpy.run_path(str(OUT.parent.parent/'is6400-round3-20261111/features/run_features.py'))
    context=runpy.run_path(str(OUT.parent.parent/'is6400-round3-extension-20261111/context/run_context.py'))
    cachechecks=[]
    for date,df in zip(ns['DATES'],[train,jan]):
        order2=orders.rename(columns={'price_sum':'amount'})
        ser=service['make_new'](order2,reviews,date)[0]
        ctx=context['build_context'](orders,items,pay,date)[0]
        for actual,cols in [(ser,ns['SERVICE']),(ctx,ns['CTX'])]:
            check=df[ns['KEY']+cols].merge(actual[ns['KEY']+cols],on=ns['KEY'],validate='one_to_one',suffixes=('_saved','_new'))
            for c in cols:assert np.allclose(check[c+'_saved'],check[c+'_new'],equal_nan=True,atol=1e-10),c
        cachechecks.append({'snapshot_date':date,'all_15_allowlisted_cache_columns_rebuilt_equal':True})
    dump({'status':'PASS','metric_checks':checks,'cached_X_rebuilt_from_hash_verified_raw':cachechecks,'all_H02_keys_retained':True,'excluded_metadata_absent_from_X':True,'field_positions':52,'field_status_counts':status,'all_missing_numeric_fields_by_period':missing.loc[missing.all_missing,['snapshot_date','field']].to_dict('records'),'graph_visual_review':'feature-comparison.png viewed; capacity-comparison.png pending final inspection','April_snapshot_rows_read':0},'artifact-verification.json')
    lines=['# P2 全字段、地区与距离对照结果','', '本轮五个预先固定候选均完成。January 已见，只能作为开发比较；没有自动采用任何模型。所有模型自然分布、未加权，Oct 21160 人 / 211 正例，Jan 29368 人 / 230 正例。','', '| 候选 | Log loss | Brier | AP | AUC | K2937 Hits | 久单79 Hits |','|---|---:|---:|---:|---:|---:|---:|']
    for row in metrics.itertuples():
        cc=caps.loc[caps.candidate.eq(row.candidate)].set_index('policy');lines.append(f'| {row.candidate} | {row.logloss:.6f} | {row.brier:.6f} | {row.AP:.6f} | {row.AUC:.6f} | {cc.loc["global_K2937","hits"]} | {cc.loc["long_fixed79","hits"]} |')
    lines+=['','本次加入地理后 LR 的 AUC、全局 K2937 捕获增加，但 Log loss / Brier / AP 变差；不能把更高 AUC 当作全面改善。全结构 LR 和结构+文本 LR 均未优于原八字段基线；全结构 CatBoost 此次 Log loss、Brier、AP 和 K2937 读数较好，AUC 并非最高；共同久单 cluster_id=1 的固定79捕获以本页表格为准，不能沿用旧 cluster2 的解释。只比较这一时间切片，尚无真正未见期验证与区间支持，不能声称稳定胜出或证明全特征永远无效。','', '## 字段、时点和信息边界','',f'9 表 52 个字段位置全部登记于 `field-catalog-52.csv`：{status}。类别是每个原字段的主要处置，不表示 52 列全部进入 X。完整结构是 141 个历史摘要原始列，8 个类别；LR 编码后 913 维；文本词表训练拟合 1317 项，合计 2230 维。大量列是均值/最大/标准差、缺失标志、稀有类别或其他冗余，不能把维度解释为独立信息量。','', '保留 H02 冗余 AOV、max、observed days。客户和订单标识只连接；商品/卖家 ID 转为截止日前历史频率和去重数。原订单最终状态无状态日志，排除；英文分类翻译和 geo 城市/州重复标签排除。买卖家邮编类别、城市、州保留，geo 先 exact 去重再按邮编 median lat/lng，Haversine 6371.0088 km；均值是历史 item 加权，末单距离为末单各 item 均值，不是准确门牌路线。','', '静态商品/买家/卖家/geo 维度没有变化日志；支付、预计送达和发货截止没有回写日志。相关摘要明确依赖“审批时已知、后续未改写”的假设，不能认证严格生产时点可恢复。所有实际承运、实际送达和评价答复严格 `<t`，负时长不纳入。Oct / Jan 分别排除截止后评价 2063 / 2863 条、未来实际送达 1543 / 2439 单；评价文本仅合法已答历史，词表只 fit Oct。','', '原 F 全部逐键相同；M 最大误差 1.14e-13。两期所有 H02 客户键保留。Geo 原 1000163 行，经 exact 去重和经纬度合法过滤后 738332 行，聚合 19015 邮编；Oct / Jan item 距离缺失 141 / 199 条，缺失未当作零公里。','', '## 文件与复用','', '`private/october-features.csv` 和 `private/january-features.csv` 是可复用、逐键对齐原始表，包含标签 y 和独立文本。`feature-views.json` 给 141 列名单、六个逻辑视图、每列定义、类型、时点和预处理；仅使用 views 中列名构建 X。y、cluster_id、cluster_version、keys 和 past_review_text 不进入结构 X。邮编必须按 categorical_columns 读取为字符串。Oct / Jan 的 sparse NPZ 使用同一个 Oct 拟合变换，可供固定预算下游对照；原始表供折内重新拟合，不能先全量编码后做交叉验证。','', '`january-metrics.csv` 含自然概率质量、0.5 混淆/precision/recall/F1；`january-capacity.csv` 含 K2937、5%（1469）、20%（5874）、久单79。`calibration-bins.csv` 保存固定十分箱概率校准分布。私有模型、文本词表、填补/缩放/OHE 参数、矩阵和逐人分数均保留。源码 `run_features.py` 同时生成 PNG/SVG；`finalize_features.py` 独立核读逐人指标和导出矩阵模型分数、回源重建旧缓存15字段。','', '## 执行纠正与限制','', '首轮实现误将坐标等全部数值 signed-log，与事先冻结的坐标原值缩放不符。该轮全部指标/容量/分数与运行回执保留于 `private/preprocess-mismatch/`，不作为正式结果。修正为冻结协议后重新运行全部五个候选；本页表格只对应修正轮，不依据一月结果选择预处理。LR 均无收敛警告，参数未调优。CatBoost 是预先列出的附加候选，仅一个固定种子。','', 'raw 源文件只读，9 文件 SHA 与 manifest 全部一致；April 快照/标签解析 0。未修改 Git/看板、未安装依赖、未对外发送。未跑无法穷尽的所有变换；结构列是预先定义的历史摘要，仍存在压缩和静态表假设。']
    (OUT/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    files=[]
    for p in OUT.rglob('*'):
        if p.is_file() and p.name!='manifest.json':files.append({'path':p.relative_to(OUT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p),'private':'private' in p.relative_to(OUT).parts})
    dump({'files':files,'scope':'Only features directory; private raw rows/models/matrices are not public artifacts'},'manifest.json')
    print('FINALIZED',len(files),status,checks,cachechecks)
if __name__=='__main__':main()
