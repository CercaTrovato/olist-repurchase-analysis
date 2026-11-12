"""Deterministic aggregate report; all frozen rules remain in public CSVs."""
from pathlib import Path
import json
import pandas as pd

ROOT=Path(__file__).resolve().parent
def table(df):
    def fmt(x):
        if pd.isna(x): return '—'
        if isinstance(x,float): return f'{x:,.3f}'
        return str(x)
    rows=['| '+' | '.join(map(str,df.columns))+' |','| '+' | '.join(['---']*len(df.columns))+' |']
    rows+=['| '+' | '.join(fmt(v) for v in row)+' |' for row in df.itertuples(index=False,name=None)]
    return '\n'.join(rows)

def main():
    cap=pd.read_csv(ROOT/'capacity-results.csv'); boot=pd.read_csv(ROOT/'jan-paired-bootstrap.csv')
    am=pd.read_csv(ROOT/'amount-prediction-metrics.csv'); tail=pd.read_csv(ROOT/'amount-tail-concentration.csv')
    zero=pd.read_csv(ROOT/'original-formula-zero-analysis.csv')
    positive_tail=pd.read_csv(ROOT/'amount-tail-positive-concentration.csv')
    manifest=json.loads((ROOT/'value-manifest.json').read_text(encoding='utf-8'))
    lines=['# 全体概率 → 客户价值 → 经理名单：冻结回测结果','',
        '本层补齐“先为所有合资格客户给复购概率，再按价值和名额选择经理关注对象”。六个金额模型、十八套全体经理私表和所有冻结分数均保留；未根据结果改参数、规则或容量。数据是已见历史窗口，三个窗口客户与目标日历重叠，不能叫三次独立盲测。',
        '', '## 同名额 10% 的完整主对照','',
        '每行是相同窗口/训练策略/概率家族，经理人数相同。以下并列概率 p、主原式 p×F×M、字面次数敏感性 p×max(F−1,0)×M、学习期望金额；另外两种冻结代理及 1/2/5/20/50/100% 均完整保留于 capacity-results.csv。金额为实际未来 90 天商品额捕获量，不是利润或触达增量。F/M 均为此前六个自然月，非终身累计。','']
    rows=[]
    z=cap[(cap.scope=='global')&(cap.capacity==.1)]
    for keys,g in z.groupby(['evaluation_date','strategy','family'],sort=True):
        r={'window':keys[0],'strategy':keys[1],'p-family':keys[2],'K':int(g.K.iloc[0])}
        for rule,short in [('p','p'),('purchase_F_M','pFM'),('repeat_Fminus1_M','p(F−1)M'),('expected_G','EV')]:
            q=g[g.rule==rule].iloc[0]; r['G_'+short]=q.captured_G; r['hits_'+short]=int(q.hits)
        rows.append(r)
    lines += [table(pd.DataFrame(rows)),'','完整比较以共同分母的 G_share、hits、precision/recall、订单数、long 席位/命中/金额及边界同分列为准，不能只挑金额或命中一项宣布统一赢家。100% 各规则覆盖所有实际事件与金额，precision 等于群基率；random_expectation 为解析期望，无随机名单重复实验。','','## 金额模型的训练支持与重尾','']
    support=[]
    for cell,e in manifest['cells'].items():
        f=e['amount_fit']; src=f['source_target_support']
        support.append({'cell':cell,'positive_rows':f['positive_rows'],'positive_customers':f['positive_unique_customers'],
            'mean_positive_G':f['positive_G_mean'],'max_positive_G':f['positive_G_max'],
            'target_order_opportunities':src['target_order_rows'],'unique_target_orders':src['unique_target_orders'],
            'repeated_target_order_rows':src['repeated_target_order_rows'],'fallback':f['fallback'],'clipped_rows':f['clip_high_count']+f['clip_low_count']})
    lines += [table(pd.DataFrame(support)),'','正支只用该 cell 的 fit 中 G>0 行，固定四个历史输入、log1p+正支 scaler、Gamma(alpha=1, max_iter=2000, tol=1e-8)，目标除训练正支 G 均值，预测回乘并限 [0,训练正支最大 G]。未用 cal/eval 金额拟合或调参；失败保留并退回训练正支均值。重复目标订单按预测机会等权，不能当作新增独立交易。首个模型的物理 CPU 核数探测警告已记录，实际模型和保存预测回算成功。','',
        table(tail[['evaluation_date','strategy','N','positives','G','max_customer_G_share','top1pct_G_share','long_N','long_positives','long_G']]),'',
        '全体客户 Top1% 是按真实未来 G 排序后的尾部集中度诊断，未给经理排序使用。三期购买客户率均不足 1%，所以全体 Top1% 当然包含全部真实商品额；另列“实际购买客户内部 Top1%”避免将这个机械结果误当金额分布证据。真实未来信息不会进入模型输入或经理私表。','',
        table(positive_tail[['evaluation_date','strategy','positive_customer_N','positive_top1pct_K','positive_top1pct_G_share','max_customer_G_share']]),'',
        '## 字面 F−1 原式的零分影响','',
        table(zero[['evaluation_date','strategy','family','F1_N','F1_long_N','original_zero_N','original_zero_actual_hits','original_zero_actual_G','original_zero_long_N','original_zero_long_hits','original_zero_long_G']]),'',
        '主原式 p×F×M 也完整比较，未把 F−1 人为设为唯一参照。F×M=F²×历史单均金额，频次重复强调反映偏好；不是未来金额恒等式。零分客户在名额越过零分边界时按双键破平，具体边界 tied/selected/unselected 均记录在容量表。','','## 金额预测误差','',
        '只有学习的 p×条件金额和 p×训练正支均值基线拥有明确未来金额预测含义，才报告 MAE/RMSE 和预测/实际总额比。其余分数只排序，不将任意分数单位冒充货币。','',
        table(am[['evaluation_date','strategy','family','prediction','MAE','RMSE','predicted_G_total','actual_G_total','predicted_actual_total_ratio']]),'',
        '## Jan 固定分数的配对不确定性','',
        '每个 single/pooled × 概率家族：全体客户共同 2000 次配对重抽样，重复客户按次数重排，固定全局 10% K2937；long 群另 2000 次、K79。所有规则与七个主要指标共用同次 counts。仅预定此两容量作区间，不挑最好 K、不重训。主对照为各非 p 规则 vs p，及各不同规则 vs p×F×M；全部 840 行在 jan-paired-bootstrap.csv。零实际总金额的抽样没有定义 G_share，明确计数并从该比率区间排除；金额绝对差与命中仍保留。','']
    b=boot[(boot.rule=='expected_G')&(boot.metric=='captured_G')]
    lines += ['下表每行均为预计金额规则 expected_G 减 baseline 的实际商品额捕获差（captured_G）；正数代表 EV 捕额较高。','',
        table(b[['strategy','family','scope','baseline','point_delta','ci025','ci975','valid_reps']]),'',
        '区间只反映固定 Jan 分数下的评价客户抽样，不包括训练、选模、标签日历重叠或未来漂移。金额高偏态，区间跨零或三期方向不一致时，不能宣称可靠统一胜者。样本有限不是留待无限加模型的借口，本批规则和六金额模型到此结案。','','## 经理产物与验证边界','',
        'value/private/cells/{window}__{strategy}/manager-p_*.csv 共 18 表，为每位 eval 客户保留双键、历史字段、p、条件金额、预计商品额、六规则及历史 M/最近购买的分数与排名。未来 y/G/N 独立保存在 evaluation-truth.csv，经理表列检查排除所有真实未来答案。全部逐客户、模型与旁表私有；公共只发布聚合 CSV、SVG/PNG、代码、说明。详见 manager-guide.md。','',
        '全量 p 的概率指标由 probability 层独立评价；名单容量不是概率模型输入人数。新独立未来样本、真实触达试验、毛利和成本均无，不能证明利润、触达增量或现实部署效果。未生成或评分四月新快照/标签。']
    (ROOT/'value-report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

if __name__=='__main__': main()
