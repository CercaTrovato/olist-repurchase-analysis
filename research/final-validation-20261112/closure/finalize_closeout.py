"""Finalize existing question closure, with read-only aggregate value checks."""
import collections,hashlib,json
from pathlib import Path
import numpy as np,pandas as pd
OUT=Path(__file__).resolve().parent;ROOT=OUT.parent;VALUE=ROOT/'value'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def evidence(p):return dict(path=str(p).replace('\\','/'),sha256=sha(p))
def main():
    d=json.loads((OUT/'question-closeout-draft.json').read_text())
    original=json.loads(Path(d['original_question_register_path']).read_text())
    vm=json.loads((VALUE/'value-manifest.json').read_text());verify=json.loads((VALUE/'independent-readback.json').read_text());am=json.loads((VALUE/'amount-stage-manifest.json').read_text())
    assert vm['status']==am['status']=='READY' and verify['status']=='PASS'
    assert am['new_amount_fits']==6 and verify['checks']['manager_tables']==18
    assert verify['checks']['capacity_rows']==1296 and verify['checks']['amount_metric_rows']==36 and verify['bootstrap_rows']==840
    c=pd.read_csv(VALUE/'capacity-results.csv');b=pd.read_csv(VALUE/'jan-paired-bootstrap.csv');errors=pd.read_csv(VALUE/'amount-prediction-metrics.csv');z=pd.read_csv(VALUE/'original-formula-zero-analysis.csv')
    assert len(c)==1296 and len(b)==840 and len(errors)==36
    top=c.loc[c.scope.eq('global')&pd.to_numeric(c.capacity,errors='coerce').eq(.1)]
    pivot=top.pivot(index=['evaluation_date','strategy','family'],columns='rule',values='captured_G')
    assert len(pivot)==18
    counts=dict(pFM_gt_p=int(pivot.purchase_F_M.gt(pivot.p).sum()),EV_gt_p=int(pivot.expected_G.gt(pivot.p).sum()),EV_gt_pFM=int(pivot.expected_G.gt(pivot.purchase_F_M).sum()))
    assert counts==dict(pFM_gt_p=15,EV_gt_p=15,EV_gt_pFM=11)
    full=c.loc[c.scope.eq('global')&pd.to_numeric(c.capacity,errors='coerce').eq(1.)]
    tail=pd.read_csv(VALUE/'amount-tail-concentration.csv').drop_duplicates(['evaluation_date','strategy'])
    for _,r in full.iterrows():
        t=tail.loc[tail.evaluation_date.eq(r.evaluation_date)&tail.strategy.eq(r.strategy)].iloc[0]
        assert r.K==r.pool_N
        assert np.isclose(r.G_share,1) and np.isclose(r.recall,1)
        assert np.isclose(r.precision,t.positives/t.N)
    jan=z.loc[z.evaluation_date.eq('2018-01-01')]
    assert jan.original_zero_N.eq(28665).all() and jan.original_zero_long_N.eq(12330).all()
    crossing=int((b.ci025.le(0)&b.ci975.ge(0)).sum())
    assert crossing>len(b)/2
    issues={x['id']:x for x in d['issues']}
    q=issues['Q11']
    q['actually_completed']='已对全体客户计算 LL/Brier/AP/AUC、校准和 sum(p)；最后批实际完成 6 个 Gamma 正支、18 套全体经理私表、1,296 行容量、36 行金额误差和 840 行 Jan 固定分数条件区间。'
    q['conclusion']='概率误差验收覆盖全体客户，排序是下游策略。固定10%下 pFM 和预计金额各在15/18组合捕获商品额高于p，预计金额11/18高于pFM；概率、命中、商品额与金额误差存在取舍，没有统一赢家。'
    q['boundary']='18组合不是18个独立时期；大多条件区间含0。概率/价值执行已收完，正式采用和预算属于现实决策。100%覆盖不证明概率准、利润高或触达增量。'
    q.pop('root_integration_only',None)
    q=issues['Q19']
    q['actually_completed']='6 cell 全体三种概率与6个Gamma正支已完成，全部fallback=false；18套全量经理私表、144个分数列、1,296行容量和36行金额误差由独立脚本回算；840行Jan条件区间已保存并独立核表结构与数量，没有第二次重跑bootstrap。'
    q['conclusion']='全体概率→价值分数→经理名单闭环已执行。主参考 p×F×M、字面敏感性 p×max(F−1,0)×M 与 p×发生购买条件下未来90天商品总额预测并列。固定10%时，pFM和预计金额各15/18组合捕获额高于p，预计金额11/18高于pFM；不能据此选唯一赢家。'
    q['boundary']='F/M均为历史六自然月，非终身；pFM重复强调频次，不是金额预测。Jan的F−1敏感性使28,665位单单客户零分，久单12,330位全部零分。18组合来自3个重叠已见窗口；大多固定分数条件区间含0，不含重训、搜索和漂移不确定性。预计商品额不含运费、利润或增量。'
    q.pop('root_integration_only',None)
    q['numerical_execution_state']='COMPLETED_BOUNDED_VALIDATION'
    q['fixed_global10_descriptive_comparisons']=counts|{'combinations':18,'independent_periods':False}
    q['verification_scope']='6模型、18经理表、144分数列、1296容量、36金额误差独立回算；840条件区间仅schema/count独立核验，不冒称第二次区间复算。'
    q=issues['Q20']
    q['actually_completed']='Nov/Dec/Jan全部23,260/26,848/29,368位合格客户均获三种概率和全部冻结价值分；base8/full141输入维度有明确allowlist；1/2/5/10/20/50/100%容量均执行。全部100%容量的名单人数、复购召回、金额份额与群基率精确率守恒通过。'
    q['conclusion']='全量客户是行维度，全可用字段是列维度，名单百分比是输出容量。100%选择全部合格客户，覆盖全部已观察复购与商品额，precision等于群体复购率，排序不改变该端点。10%用于资源有限场景及旧项目可比，从未限制概率模型输入。'
    q['boundary']='141不含身份键、时间与未来y/G/N；所有全体概率和价值已实际输出，没有待跑容量计算。100%覆盖不能证明更准、利润更大、触达增量或经理能处理全部客户。'
    q['numerical_execution_state']='COMPLETED_BOUNDED_VALIDATION'
    extra=[VALUE/'value-report.md',VALUE/'independent-readback.json',VALUE/'value-manifest.json',VALUE/'capacity-results.csv',VALUE/'amount-prediction-metrics.csv',VALUE/'jan-paired-bootstrap.csv',VALUE/'original-formula-zero-analysis.csv']
    for name in ['Q11','Q13','Q19','Q20']:
        q=issues[name];paths={e['path'] for e in q['evidence']}
        for p in extra:
            e=evidence(p)
            if e['path'] not in paths:q['evidence'].append(e);paths.add(e['path'])
        # Refresh hashes for final evidence bytes; older drafts retain their own historical bindings.
        q['evidence']=[evidence(Path(x['path'])) for x in q['evidence']]
    def normalize(x):
        if isinstance(x,str):return x.replace('pE[G|G>0,X]','p×发生购买条件下未来90天商品总额预测').replace('pE[G/G>0,X]','p×发生购买条件下未来90天商品总额预测')
        if isinstance(x,list):return [normalize(v) for v in x]
        if isinstance(x,dict):return {k:(v if k=='user_statement' else normalize(v)) for k,v in x.items()}
        return x
    d=normalize(d)
    d['schema_version']='question-closeout-v1';d['status']='CLOSED_WITH_BOUNDED_EVIDENCE';d['draft_history_path']='question-closeout-draft.json';d['draft_history_sha256']=sha(OUT/'question-closeout-draft.json')
    d['value_numerical_results_integrated']=True
    d['final_execution_summary']=dict(new_Gamma_fits=6,manager_tables=18,score_columns=144,capacity_rows=1296,amount_metric_rows=36,Jan_conditional_interval_rows=840,conditional_interval_rows_containing_zero=crossing,interval_independent_verification='schema/count only; no second bootstrap',global10_comparisons=counts,global100_conservation_rows_checked=len(full))
    d['final_value_evidence']=[evidence(p) for p in extra]
    d['scope']='只读整合已有结果；没有新训练、Git、看板、原数据修改或四月评价。冻结范围无待跑计算；不强行证明增益或代选正式模型。'
    d['remaining_external_identification_limits']=['没有真正未见未来样本，不能认证独立未来泛化','缺毛利、退款、触达/人力成本，不能识别利润最优','缺随机触达或合适干预对照，不能识别营销uplift/增量订单','静态属性、入库/回写变更日志缺失，无法认证生产as-of完整可恢复性']
    assert all(x['user_statement']==o['user_statement'] for x,o in zip(d['issues'][:18],original['issues']))
    assert len(d['issues'])==20 and all(not x['computational_debt_in_frozen_scope'] for x in d['issues'])
    assert sha(ROOT/'data/data-manifest.json')==d['frozen_data_manifest_sha256']
    (OUT/'question-closeout.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    md=['# 二十项质疑最终结案','', '原18项原文保留，新增Q19/Q20。冻结范围的计算已完成；有限证据、资料缺失和现实采用决定分别结案，不留“待用户开测”的实验欠账，也不以训练数量强行证明赢家。','', '全体概率→价值→经理名单已实际闭环：6个Gamma正支、18套全体经理私表、1,296容量行、36金额误差行及840条件区间已交付。独立回算覆盖6模型/18私表/144分数列/全部容量和金额误差；840区间仅独立核结构与数量，没有第二次重跑bootstrap。','', '固定10%下，原pFM与预计金额各15/18组合捕获商品额高于p，预计金额11/18高于pFM。组合来自3个重叠已见窗口，不能当18次独立验证；大多条件区间含0，没有统一赢家。','', '|编号|问题|结案分类|可支持结论|','|---|---|---|---|']
    for x in d['issues']:md.append('|'+x['id']+'|'+x['title']+'|'+x['closeout_class']+'|'+x['conclusion'].replace('|','｜')+'|')
    for x in d['issues']:
        md+=['',f"## {x['id']} {x['title']}",'','> '+x['user_statement'],'','**实际完成：** '+x['actually_completed'],'','**结论：** '+x['conclusion'],'','**边界：** '+x['boundary'],'','**现实决策：** '+x['human_decision'],'','**缺外部资料：** '+x['missing_external_data_or_material'],'','**证据：**']
        for e in x['evidence']:md+=['- ['+Path(e['path']).name+']('+e['path']+')']
    md+=['','## 可证明范围与现实决定','', '本人/小组仍决定正式采用版本，经理仍决定人数、商品额、工作量与成本目标；这些是现实选择，不是未完成计算。没有真正未见未来、毛利/成本/退款或触达干预数据，无法认证独立未来泛化、利润最优和营销uplift。','', 'GAT未训练，完整MVSIB未严格复现，生存模型未执行；已完成的合适性分析、GCN、注意力/门控、明确MVSIB-inspired简化和固定90天预测已按真实范围交付，不能冒认，也不把所有算法列为穷尽义务。','', '概率有界源审见 [报告](probability-source-audit.md)。审查者写过数据构造，没有写概率实现；独立于概率作者，不是数据构造未参与作者独审。此源审新增fit0。GitHub/本地/线上操作仍以根代理真实回执为准，本结案不预先宣布同步成功。']
    (OUT/'question-closeout.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps({'md':sha(OUT/'question-closeout.md'),'json':sha(OUT/'question-closeout.json'),'data_sha_unchanged':d['frozen_data_manifest_sha256'],'summary':d['final_execution_summary']},ensure_ascii=False))
if __name__=='__main__':main()
