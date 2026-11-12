from pathlib import Path
import hashlib
import json
import platform
import zipfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd


OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
H02 = ROOT / 'outputs/H02_candidate_v2'
RAW = ROOT / 'data/raw'
VERSION = 'H02-v2-candidate-reviewed'
EXTENSION = 'round3-role01-time-v1'
KEY = ['customer_unique_id', 'snapshot_date']
TRAIN, JAN, APR = map(pd.Timestamp, ['2017-10-01', '2018-01-01', '2018-04-01'])
DAYS = pd.Timedelta(days=90)
EXPECTED = {
    'snapshot_features.csv': 'ce62dedacb5af0e08c419586ff55e45043de56771553620ef3f08100e12712b9',
    'snapshot_labels.csv': '5e75eae468449bb9810e8ac0b796bea588762dd6c3335f2923da91a46220888f',
    'coverage-and-cohorts.csv': 'a1003f7847e194281307f6c9f7ceb9a8a5ada1673bbd9e361875f04fa815c242',
}
D_FIELDS = ['delivered_known_n', 'delivery_days_mean', 'delivery_promise_known_n', 'late_delivery_share']
R_FIELDS = ['review_known_n', 'review_score_mean', 'low_review_share']
EXTRA = D_FIELDS + R_FIELDS


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(frame, name):
    frame.to_csv(OUT / name, index=False, encoding='utf-8-sig')


def between(series, start, end):
    return (series >= start) & (series < end)


def overlap(start, end, other):
    return max(0, (min(end, other + DAYS) - max(start, other)).days)


def check_equal(left, right):
    result = left.merge(right, on=KEY, how='outer', validate='one_to_one', indicator=True)
    assert result['_merge'].eq('both').all(), 'Snapshot keys differ'
    return result


def load_inputs():
    source = json.loads((ROOT / 'data/source-manifest.json').read_text(encoding='utf-8'))
    paths = {
        'orders': RAW / 'olist_orders_dataset.csv',
        'customers': RAW / 'olist_customers_dataset.csv',
        'items': RAW / 'olist_order_items_dataset.csv',
        'reviews': RAW / 'olist_order_reviews_dataset.csv',
    }
    manifest = {f['name']: f['sha256'] for f in source['files']}
    hashes = {}
    for path in paths.values():
        actual = sha(path)
        assert actual == manifest[path.name], path.name
        hashes[path.name] = actual
    for name, expected in EXPECTED.items():
        actual = sha(H02 / name)
        assert actual == expected, name
        hashes[name] = actual
    dates = ['order_purchase_timestamp', 'order_approved_at', 'order_delivered_customer_date',
             'order_estimated_delivery_date', 'order_delivered_carrier_date']
    orders = pd.read_csv(paths['orders'], parse_dates=dates)
    customers = pd.read_csv(paths['customers'], usecols=['customer_id', 'customer_unique_id'])
    items = pd.read_csv(paths['items'], usecols=['order_id', 'order_item_id', 'price'])
    reviews = pd.read_csv(paths['reviews'], usecols=['order_id', 'review_id', 'review_score',
                          'review_creation_date', 'review_answer_timestamp'],
                          parse_dates=['review_creation_date', 'review_answer_timestamp'])
    return orders, customers, items, reviews, hashes


def order_fact(orders, customers, items, reviews):
    assert orders.order_id.is_unique and customers.customer_id.is_unique
    assert not items.duplicated(['order_id', 'order_item_id']).any()
    assert items.order_id.isin(orders.order_id).all()
    assert reviews.order_id.isin(orders.order_id).all()
    item_orders = items.groupby('order_id').price.sum(min_count=1).rename('amount').reset_index()
    fact = orders.merge(item_orders, on='order_id', how='left', validate='one_to_one')
    assert len(fact) == len(orders)
    fact = fact.merge(customers, on='customer_id', how='left', validate='one_to_one', indicator=True)
    assert fact['_merge'].eq('both').all() and fact.customer_unique_id.notna().all()
    fact = fact.drop(columns='_merge')
    qualified = fact.loc[fact.order_approved_at.notna() & fact.amount.gt(0)].copy()
    audit = pd.DataFrame([
        ['orders raw', len(orders), len(orders), orders.order_id.nunique(), 0],
        ['customers raw', len(customers), len(customers), customers.customer_id.nunique(), 0],
        ['items to order', len(items), len(item_orders), item_orders.order_id.nunique(), 0],
        ['orders left join items by order_id', len(orders), len(fact), fact.order_id.nunique(), fact.amount.isna().sum()],
        ['orders left join customers by customer_id', len(orders), len(fact), fact.order_id.nunique(), fact.customer_unique_id.isna().sum()],
        ['H02 qualified orders', len(fact), len(qualified), qualified.order_id.nunique(), 0],
        ['reviews raw; order_id can repeat', len(reviews), len(reviews), reviews.order_id.nunique(), 0],
    ], columns=['stage', 'input_rows', 'output_rows', 'distinct_stage_key', 'unmatched_left'])
    return fact, qualified, audit


def history_at(qualified, snapshot):
    return qualified.loc[between(qualified.order_approved_at, snapshot - pd.DateOffset(months=6), snapshot)].copy()


def add_asof_fields(history, reviews, snapshot):
    # Cut off reviews before selecting the latest row, so a later answer cannot hide an earlier one.
    candidates = reviews.loc[reviews.order_id.isin(history.order_id)].drop_duplicates()
    candidates = candidates.merge(history[['order_id', 'order_purchase_timestamp']], on='order_id',
                                  how='left', validate='many_to_one')
    answered = candidates.review_answer_timestamp
    created = candidates.review_creation_date
    valid = (answered.notna() & answered.ge(candidates.order_purchase_timestamp)
             & (created.isna() | answered.ge(created)) & candidates.review_score.isin([1, 2, 3, 4, 5]))
    eligible = candidates.loc[valid & answered.lt(snapshot)].copy()
    latest = eligible.sort_values(['review_answer_timestamp', 'review_creation_date', 'review_id', 'review_score'],
                                  na_position='first').drop_duplicates('order_id', keep='last')
    assert latest.order_id.is_unique and latest.review_answer_timestamp.lt(snapshot).all()
    orders = history.merge(latest[['order_id', 'review_score', 'review_answer_timestamp']],
                           on='order_id', how='left', validate='one_to_one')
    assert len(orders) == len(history)
    actual = orders.order_delivered_customer_date
    approved = orders.order_approved_at
    purchased = orders.order_purchase_timestamp
    promised = orders.order_estimated_delivery_date
    coherent = actual.notna() & actual.ge(approved) & actual.ge(purchased)
    delivered = coherent & actual.lt(snapshot)
    comparable = delivered & promised.notna() & promised.dt.normalize().ge(purchased.dt.normalize())
    orders['delivery_days'] = ((actual - approved).dt.total_seconds() / 86400).where(delivered)
    orders['late'] = actual.dt.normalize().gt(promised.dt.normalize()).astype(float).where(comparable)
    orders['low_score'] = orders.review_score.le(2).astype(float).where(orders.review_score.notna())
    assert orders.loc[delivered, 'order_delivered_customer_date'].lt(snapshot).all()
    summary = orders.groupby('customer_unique_id').agg(
        delivered_known_n=('delivery_days', 'count'),
        delivery_days_mean=('delivery_days', 'mean'),
        delivery_promise_known_n=('late', 'count'),
        late_delivery_share=('late', 'mean'),
        review_known_n=('review_score', 'count'),
        review_score_mean=('review_score', 'mean'),
        low_review_share=('low_score', 'mean'),
    ).reset_index()
    summary['snapshot_date'] = snapshot.date().isoformat()
    reasons = {
        'delivery_known_orders': int(delivered.sum()),
        'delivery_raw_missing_orders': int(actual.isna().sum()),
        'delivery_invalid_sequence_orders': int((actual.notna() & ~coherent).sum()),
        'delivery_valid_but_at_or_after_cutoff_orders': int((coherent & actual.ge(snapshot)).sum()),
        'delivered_but_promise_unusable_orders': int((delivered & ~comparable).sum()),
        'review_rows_after_exact_dedup': len(candidates),
        'review_rows_invalid_answer_score_or_sequence': int((~valid).sum()),
        'review_rows_valid_at_or_after_cutoff': int((valid & answered.ge(snapshot)).sum()),
        'review_rows_valid_before_cutoff': len(eligible),
        'review_known_orders': len(latest),
        'review_no_source_record_orders': int((~orders.order_id.isin(candidates.order_id)).sum()),
        'review_with_source_but_no_valid_answer_orders': int((orders.order_id.isin(candidates.order_id) &
                                                               ~orders.order_id.isin(candidates.loc[valid, 'order_id'])).sum()),
        'review_only_valid_answers_at_or_after_cutoff_orders': int((orders.order_id.isin(candidates.loc[valid, 'order_id']) &
                                                                     orders.review_score.isna()).sum()),
        'join_input_orders': len(history),
        'join_output_orders': len(orders),
        'review_multiple_eligible_orders': int(eligible.order_id.value_counts().gt(1).sum()),
    }
    assert sum(reasons[k] for k in ('delivery_known_orders','delivery_raw_missing_orders','delivery_invalid_sequence_orders',
                                     'delivery_valid_but_at_or_after_cutoff_orders')) == len(history)
    assert sum(reasons[k] for k in ('review_known_orders','review_no_source_record_orders','review_with_source_but_no_valid_answer_orders',
                                     'review_only_valid_answers_at_or_after_cutoff_orders')) == len(history)
    return summary, reasons


def coverage(fact, qualified, candidates):
    dates = pd.date_range(candidates[0] - pd.DateOffset(months=6), '2018-10-31')
    daily = pd.DataFrame(index=dates)
    for column, frame, time in [
        ('purchase_orders', fact, 'order_purchase_timestamp'),
        ('approved_orders', fact, 'order_approved_at'),
        ('qualified_orders', qualified, 'order_approved_at'),
    ]:
        daily[column] = frame.groupby(frame[time].dt.normalize()).size().reindex(dates, fill_value=0)
    daily.index.name = 'date'
    h02_manifest = json.loads((H02 / 'data-manifest.json').read_text(encoding='utf-8'))
    obs_start = pd.Timestamp(h02_manifest['observation_start'])
    obs_end = pd.Timestamp(h02_manifest['observation_end_exclusive'])
    daily['within_H02_working_bounds'] = between(daily.index, obs_start, obs_end)
    last_event = qualified.order_approved_at.max()
    daily['after_last_qualified_event_day'] = daily.index > last_event.normalize()
    rows, gaps = [], []
    for snapshot in candidates:
        start, end = snapshot - pd.DateOffset(months=6), snapshot + DAYS
        hist = daily.loc[between(daily.index, start, snapshot)]
        target = daily.loc[between(daily.index, snapshot, end)]
        cohort = history_at(qualified, snapshot).customer_unique_id.unique()
        assert len(target) == 90
        supported = start >= obs_start and end <= obs_end
        target_buyers = qualified.loc[between(qualified.order_approved_at, snapshot, end), 'customer_unique_id']
        january, april = overlap(snapshot, end, JAN), overlap(snapshot, end, APR)
        purpose = {
            TRAIN: '共同训练', JAN: '已见开发验证', APR: '已见窗口回测',
        }.get(snapshot, '补充回测候选，存在日历重叠' if supported else '尾部覆盖不足，标签不发布')
        rows.append({
            'snapshot_date': snapshot.date(), 'purpose': purpose,
            'history_start_inclusive': start.date(), 'history_end_exclusive': snapshot.date(),
            'history_days': len(hist), 'history_zero_qualified_days': int(hist.qualified_orders.eq(0).sum()),
            'history_qualified_orders': int(hist.qualified_orders.sum()), 'customers': len(cohort),
            'target_start_inclusive': snapshot.date(), 'target_end_exclusive': end.date(),
            'target_calendar_mature_at': end.date(), 'target_days': len(target),
            'target_purchase_orders': int(target.purchase_orders.sum()),
            'target_approved_orders': int(target.approved_orders.sum()),
            'target_qualified_orders': int(target.qualified_orders.sum()),
            'target_zero_qualified_days': int(target.qualified_orders.eq(0).sum()),
            'target_zero_days_inside_working_bounds': int((target.qualified_orders.eq(0) & target.within_H02_working_bounds).sum()),
            'target_days_beyond_H02_bound': int((target.index >= obs_end).sum()),
            'target_days_after_last_qualified_event_date': int(target.after_last_qualified_event_day.sum()),
            'H02_working_observation_end_exclusive': obs_end.date(),
            'last_raw_purchase_time': fact.order_purchase_timestamp.max(),
            'last_raw_approved_time': fact.order_approved_at.max(),
            'last_qualified_approval_time': last_event,
            'fixed_train_snapshot': TRAIN.date(),
            'fixed_train_labels_calendar_mature_at': (TRAIN + DAYS).date(),
            'fixed_train_mature_by_snapshot': TRAIN + DAYS <= snapshot,
            'january_development_labels_mature_at': (JAN + DAYS).date(),
            'january_development_labels_mature_by_snapshot': JAN + DAYS <= snapshot,
            'target_overlap_seen_january_days': january, 'target_overlap_seen_april_days': april,
            'target_overlap_seen_union_days': january + april,
            'within_H02_working_bounds': supported,
            'positives_if_within_working_bounds': int(pd.Index(cohort).isin(target_buyers).sum()) if supported else None,
            'exposure_note': '团队已见' if snapshot in {TRAIN, JAN, APR} else '检查已见窗口日历重叠；个人/团队其他查看历史需另登记',
        })
        zero_dates = target.index[target.qualified_orders.eq(0) & target.within_H02_working_bounds]
        for day in zero_dates:
            bought = fact.loc[between(fact.order_purchase_timestamp, day, day + pd.Timedelta(days=1))]
            next_approval = bought.order_approved_at
            inside = between(next_approval, snapshot, end)
            gaps.append({
                'snapshot_date': snapshot.date(), 'zero_qualified_date': day.date(),
                'purchase_orders_that_day': len(bought),
                'approvals_that_day': int(daily.loc[day, 'approved_orders']),
                'purchased_then_approved_inside_target': int(inside.sum()),
                'purchased_then_qualified_inside_target': int((inside & bought.amount.gt(0)).sum()),
                'purchased_with_missing_approval': int(next_approval.isna().sum()),
                'purchased_approved_outside_target': int((~inside & next_approval.notna()).sum()),
                'trace_approval_dates': json.dumps(next_approval.dt.strftime('%Y-%m-%d').fillna('missing').value_counts().to_dict()),
                'interpretation': '追查购买队列后续批准；源时间戳原因和漏采无法由导出证明',
            })
    return pd.DataFrame(rows), daily.reset_index(), pd.DataFrame(gaps)


def make_chart(windows):
    font = Path('C:/Windows/Fonts/msyh.ttc')
    chinese = font.exists()
    if chinese:
        font_manager.fontManager.addfont(str(font))
        plt.rcParams['font.family'] = font_manager.FontProperties(fname=font).get_name()
    plt.rcParams['svg.fonttype'] = 'path'
    fig, ax = plt.subplots(figsize=(15, 7.1))
    fig.patch.set_facecolor('#f6f8fc')
    ax.set_facecolor('#f6f8fc')
    ax.axvspan(JAN, JAN + DAYS, color='#ede1fb', zorder=0)
    ax.axvspan(APR, APR + DAYS, color='#ede1fb', zorder=0)
    for y, row in enumerate(windows.itertuples()):
        start, point, end = map(pd.Timestamp, [row.history_start_inclusive, row.snapshot_date, row.target_end_exclusive])
        ax.barh(y, (point-start).days, left=start, color='#8aa7c6', height=.39, zorder=2)
        color = '#7850a6' if point in {JAN, APR} else '#117f76'
        cap = min(end, pd.Timestamp(row.H02_working_observation_end_exclusive))
        ax.barh(y, (cap-point).days, left=point, color=color, height=.39, zorder=3)
        if end > cap:
            ax.barh(y, (end-cap).days, left=cap, color='#dd9a61', height=.39, zorder=3)
        ax.scatter(point, y, color='#102b46', s=24, zorder=4)
        ax.text(end+pd.Timedelta(days=4), y,
                f'{end:%m-%d}  |  {row.target_overlap_seen_union_days}'+(' 天重叠' if chinese else ' overlap days'),
                va='center', fontsize=9, color='#233349')
    ax.axvline(TRAIN + DAYS, ls='--', lw=1.4, color='#526b86')
    ax.axvline(pd.Timestamp('2018-09-01'), ls='--', lw=1.4, color='#b66b35')
    ax.set_yticks(range(len(windows)), [str(d) for d in windows.snapshot_date])
    ax.invert_yaxis()
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.set_xlim(pd.Timestamp('2017-03-15'), pd.Timestamp('2018-11-25'))
    ax.spines[['top','right','left']].set_visible(False)
    ax.tick_params(axis='y', length=0)
    ax.grid(axis='x', color='#dce3eb', zorder=1)
    title = '复购预测的时间边界与已见评价窗口' if chinese else 'Repurchase prediction timeline and previously seen evaluation windows'
    note = ('蓝色 历史6个月   |   绿色 90天目标   |   紫色 已见一月/四月目标   |   橙色 超出H02工作观察上界'
            if chinese else 'Blue: six-month history  |  Green: 90-day outcome  |  Purple: seen Jan/Apr  |  Orange: beyond H02 working bound')
    footer = ('虚线：2017-12-30 训练标签成熟、2018-09-01 工作观察上界。条形按左闭右开绘制；覆盖不保证源系统完整。'
              if chinese else 'Dashed: 2017-12-30 training label maturity and 2018-09-01 working bound. All bars use half-open intervals.')
    fig.text(.085,.951,title,fontsize=22,weight='bold',color='#102b46')
    fig.text(.085,.90,note,fontsize=11,color='#40556d')
    fig.text(.085,.045,footer,fontsize=10,color='#40556d')
    fig.subplots_adjust(left=.115,right=.98,top=.84,bottom=.13)
    for extension in ['png','svg']:
        fig.savefig(OUT / f'time-boundaries.{extension}', dpi=180)
    plt.close(fig)


def definitions():
    delivery = '历史合格订单；实际送达 >= 批准时间及购买时间，且实际送达 < 快照'
    review = '历史合格订单；答复 < 快照，答复不早于购买及已知评价创建时间；评分1–5'
    rows = [
        ['delivered_known_n','可用',delivery,'每个合格订单至多计一次；按客户计数','0表示无可用历史送达，原因见 order-availability.csv'],
        ['delivery_days_mean','可用',delivery,'平均 (实际送达 - 批准) 秒数 / 86400','无已送达合格订单时留空'],
        ['delivery_promise_known_n','有条件可用',delivery+'；预计送达日有效','按客户计可比较预计日期的已送达订单','0表示无可比较订单'],
        ['late_delivery_share','有条件可用',delivery+'；预计日期假设在批准时已知且未被事后回写','实际送达日 > 预计送达日的笔数 / 可比较订单数；同日不算迟','无可比较订单留空；预计字段可知性无版本日志证明'],
        ['review_known_n','可用',review,'每单取截断后最新有效答复；同时间按创建时间、review_id、评分排序取最后；按客户计有评分订单','0表示无可用评分，不能视为无评价或差评'],
        ['review_score_mean','可用',review,'每单最新已答评分等权平均','无已知评分留空，0不是评分'],
        ['low_review_share','可用',review,'已知评分订单中评分<=2的比例','无已知评分留空'],
        ['order_approved_at / price / customer_unique_id','H02既有','批准在历史区间；商品金额>0','商品先按order_id求和；订单以customer_id接客户；以customer_unique_id聚合','缺批准或正额不可核算不进入合格事件；金额采用既有H02可知性假设'],
        ['order_delivered_carrier_date','未发布','可另按实际交运时间审计','如需采用需核验时序和业务记录时点','原始空值不代表未发货'],
        ['order_estimated_delivery_date（单独使用）','假设待核','预计日期可在未来；是否事前已知取决于承诺生成和回写规则','需历史承诺版本，当前仅用于条件迟到指标','预计为空时不纳入迟到分母'],
        ['review_creation_date / text','未发布','创建时间不足以证明评分或文字已答复；文本编辑史未提供','评分以答复截断；文本可用性和变更记录另核','空文本可以有评分'],
        ['order_status（导出最终状态）','禁止作当时输入','无状态快照或状态变更日志','排除，资格按批准时间与金额','不使用最终 delivered/canceled 做资格回筛'],
        ['未来送达 / 答复','禁止作当时输入','等于或晚于快照零点','截断后再取单级最新答复和客户聚合','保留历史客户，未来事件不给当期特征赋值'],
    ]
    return pd.DataFrame(rows, columns=['field','availability','as_of_rule','order_to_customer_formula','missing_and_limits'])


def report(windows, quality, availability, rows, matches):
    w = windows.set_index(windows.snapshot_date.astype(str))
    v = availability.set_index('snapshot_date').loc['2018-01-01']
    jan_quality = quality.loc[quality.snapshot_date.eq('2018-01-01')].set_index('field')
    display_cols = ['snapshot_date','customers','target_end_exclusive','target_zero_qualified_days',
                    'target_overlap_seen_union_days','target_days_beyond_H02_bound']
    lines = ['| 快照 | 客户 | 90天结束（不含） | 目标零记录日 | 与已见目标重叠天数 | 超H02工作上界天数 |',
             '|---|---:|---|---:|---:|---:|']
    for row in windows[display_cols].itertuples(index=False, name=None):
        lines.append('| ' + ' | '.join(map(str, row)) + ' |')
    table = '\n'.join(lines)
    return f"""# 第三轮 1 号交接｜字段时点与时间有效性

发方 1 号，接收方 2、3、4、5 号。基础版本 {VERSION}，本次扩展 {EXTENSION}。输入指纹见 data-version.json。版本与[第三轮共同规则](https://github.com/CercaTrovato/olist-repurchase-analysis/blob/main/docs/team/round-3/README.md)公布的 H02 成员文件 SHA-256 一致。

## 可直接接入

- 私有 snapshot-asof-features.csv 有 {rows:,} 行，以 customer_unique_id + snapshot_date 一对一左接 H02。十月、一月、四月各期名单均完整。模型开发沿用十月训练、一月验证；四月已有曝光。2、3 号按字段表挑选，填补与缩放只拟合十月。4 号可做历史画像，5 号用同键验收。逐人表仅在组内传递。
- 配送以实际送达严格早于快照零点为准。配送时长从批准时间起算，剔除送达早于购买或批准的时序异常。迟到按日历日期比较，依赖预计送达日期在批准时可知且未被回写的假设。默认优先使用有送达订单数和平均时长；需采用迟到比例时，请在实验说明中保留假设。
- 评价以答复时间截断，再按订单取最新有效评分。答复时间相同的行有固定排序规则，重复和多评都只给每单一票。之后才聚合到客户。原始评价创建时间只用于检查答复时序。
- 一月共有 29,368 位客户；有可用送达订单 {int(v.delivery_known_orders):,} 笔，平均时长缺失 {int(jan_quality.loc['delivery_days_mean','missing_customers']):,} 人；有可用答复评分订单 {int(v.review_known_orders):,} 笔，平均评分缺失 {int(jan_quality.loc['review_score_mean','missing_customers']):,} 人。无可用事件时计数为 0，均值和比率留空。缺失分项及其他快照见 field-missingness.csv 与 order-availability.csv。

## 原始行数与连接

- 原始 orders 99,441 行、customers 99,441 行、items 112,650 行、reviews 见 join-audit.csv。商品先汇总到订单，左接原订单后保持 99,441 行。客户连接零漏配。订单评价先截断、去重、每单取一条再连接。各快照评价格式连接前后行数一致。
- 从原表重构三个快照的客户名单与复购标签。各期组合键无重复，特征与标签双向对齐，标签差异 {matches}。四月复用已验收口径，核得 {int(w.loc['2018-04-01','customers']):,} 位客户、{int(w.loc['2018-04-01','positives_if_within_working_bounds']):,} 位正例，目标 {int(w.loc['2018-04-01','target_qualified_orders']):,} 笔合格订单。

## 时间验证

历史为 [快照减6自然月, 快照)，标签为 [快照, 快照加90天)，以源记录日期为准。结束日00:00是日历成熟时点，实际可用性仍依赖源记录的及时性和完整性。十月训练标签在 2017-12-30 日历成熟，早于一月验证。一月标签到 2018-04-01 日历成熟；用一月结果选定的方法可以事后锁定再做四月回测。四月已有结果公开，报告用“已见窗口回测”。

{table}

- 一月目标 [2018-01-01, 2018-04-01)，四月目标 [2018-04-01, 2018-06-30)。二月与三月目标合计重叠90天。五月和六月可作锁定方法后的补充时间敏感性检查，分别与已见四月重叠60天和29天。日历重叠不能代替逐客户标签或模型独立性检查；同一买家可能跨期重复，逐期报告。
- 从 2018-06-30 才能避开两个已见目标区间，其90天终点为 2018-09-28，超过 H02 的 2018-09-01 工作上界。七月快照同样超过上界。工作上界、实际最后合格批准事件以及其后的日期数均在 time-window-audit.csv。尾部快照保留可核的历史人数，不发布不完整标签。当前候选中没有同时满足工作覆盖和零已见目标重叠的新增评价窗口。
- 四月 21—23 日无合格批准。追查当日下单的641笔，其批准日均为24、25、27日，均落在四月目标内。7月4日和8月19日无合格批准，当日分别下单256、204笔，后续批准均在六月快照目标内。8月30—31日共5笔下单均无批准时间，尾部已出现稀疏迹象。各候选按自己的边界追查，见 zero-day-investigation.csv。daily-coverage.csv 包含下单、批准和合格批准三种事件。

## 待核与交接

预计送达承诺的历史版本、源系统完整性、评分或状态历史变更日志仍未获得。最终订单状态及预测日以后才发生的实际送达或评价答复不得作为当时输入。若改用其他延迟口径、其他评价去重规则或回填方式，另记定义并在同一客户池比较。团队可记录实际采用的方法与锁定日期，使用十月／一月开展选择，附四月与其他时间敏感性结果。窗口扫描只检查时间与数据，未评分。

将本包解压到仓库的 outputs 目录，确保脚本位于 outputs/Round3_role01_time_v1/。原表位于 data/raw，H02 位于 outputs/H02_candidate_v2。使用项目的 Python 环境从仓库根目录复跑。

{chr(96) * 3}powershell
.\\.venv312\\Scripts\\python.exe outputs/Round3_role01_time_v1/build_audit.py
{chr(96) * 3}

发给 2、3、4、5 号的资料包括字段定义、缺失统计、逐人特征、窗口与日覆盖、连接验收、PNG/SVG 和重算入口。接收方按 data-version.json 核对输入指纹，按 CHECKSUMS.sha256 核附件文件。
"""


def main():
    orders, customers, items, reviews, hashes = load_inputs()
    fact, qualified, joins = order_fact(orders, customers, items, reviews)
    source_features = pd.read_csv(H02 / 'snapshot_features.csv', usecols=KEY + ['data_version'])
    source_labels = pd.read_csv(H02 / 'snapshot_labels.csv', usecols=KEY + ['y', 'data_version'])
    assert source_features.data_version.eq(VERSION).all() and source_labels.data_version.eq(VERSION).all()
    assert not source_features.duplicated(KEY).any() and not source_labels.duplicated(KEY).any()
    # Exercise exact boundaries using one instant before and at each endpoint.
    boundary = pd.Series([APR - pd.Timedelta(nanoseconds=1), APR, APR + DAYS - pd.Timedelta(nanoseconds=1), APR + DAYS])
    assert between(boundary, APR, APR + DAYS).tolist() == [False, True, True, False]
    frames, availability, check_rows = [], [], []
    label_differences = 0
    for snapshot in [TRAIN, JAN, APR]:
        day = snapshot.date().isoformat()
        history = history_at(qualified, snapshot)
        features, reasons = add_asof_fields(history, reviews, snapshot)
        availability.append({'snapshot_date': day, **reasons})
        h02_keys = source_features.loc[source_features.snapshot_date.eq(day), KEY]
        check_equal(features[KEY], h02_keys)
        future = qualified.loc[between(qualified.order_approved_at, snapshot, snapshot + DAYS)]
        computed = features[KEY].assign(y_raw=features.customer_unique_id.isin(future.customer_unique_id).astype(int))
        label_match = check_equal(computed, source_labels.loc[source_labels.snapshot_date.eq(day), KEY + ['y']])
        differences = int(label_match.y_raw.ne(label_match.y).sum())
        assert differences == 0
        label_differences += differences
        check_rows.append({'snapshot_date': day, 'cohort_rows': len(features), 'label_positives': int(label_match.y.sum()),
                           'duplicate_keys': int(features.duplicated(KEY).sum()), 'unmatched_keys': 0,
                           'label_differences': differences, 'before_review_join': reasons['join_input_orders'],
                           'after_review_join': reasons['join_output_orders']})
        frames.append(features)
    extension = pd.concat(frames, ignore_index=True)
    extension.insert(2, 'data_version', VERSION)
    extension.insert(3, 'feature_version', EXTENSION)
    check_equal(extension[KEY], source_features[KEY])
    missing = []
    for day, frame in extension.groupby('snapshot_date'):
        for field in EXTRA:
            missing.append({'snapshot_date':day, 'field':field, 'N':len(frame),
                            'missing_customers':int(frame[field].isna().sum()),
                            'missing_rate':float(frame[field].isna().mean()),
                            'zero_customers':int(frame[field].eq(0).sum()),
                            'nonmissing_customers':int(frame[field].notna().sum())})
    quality = pd.DataFrame(missing)
    availability = pd.DataFrame(availability)
    windows, daily, gaps = coverage(fact, qualified, list(map(pd.Timestamp, [
        '2017-10-01','2018-01-01','2018-02-01','2018-03-01','2018-04-01','2018-05-01','2018-06-01','2018-06-30','2018-07-01'])))
    apr_row = windows.loc[windows.snapshot_date.astype(str).eq('2018-04-01')].iloc[0]
    accepted = pd.read_csv(H02/'coverage-and-cohorts.csv').set_index('snapshot_date').loc['2018-04-01']
    for current, earlier in [('customers','customers'), ('positives_if_within_working_bounds','positives'),
                             ('history_qualified_orders','history_orders'), ('target_zero_qualified_days','label_zero_days')]:
        assert apr_row[current] == accepted[earlier]
    prior_path = ROOT/'outputs/April_90day_check_v1/summary.json'
    if prior_path.is_file():
        prior = json.loads(prior_path.read_text(encoding='utf-8'))
        assert apr_row.target_qualified_orders == prior['future_qualified_orders_all_buyers']
    month = daily.assign(month=daily.date.dt.strftime('%Y-%m')).groupby('month', as_index=False).agg(
        purchase_orders=('purchase_orders','sum'), approved_orders=('approved_orders','sum'), qualified_orders=('qualified_orders','sum'))
    outputs = {
        'field-time-audit.csv': definitions(), 'time-window-audit.csv': windows, 'daily-coverage.csv': daily,
        'zero-day-investigation.csv': gaps, 'field-missingness.csv': quality, 'order-availability.csv': availability,
        'join-audit.csv': joins, 'key-and-label-checks.csv': pd.DataFrame(check_rows),
        'source-tail-monthly.csv': month, 'snapshot-asof-features.csv': extension,
    }
    for name, table in outputs.items():
        save(table, name)
    metadata = {'base_version': VERSION, 'feature_version': EXTENSION, 'snapshot_rows': len(extension), 'key': KEY,
                'raw_and_H02_sha256': hashes, 'april_prior_summary_sha256': sha(prior_path) if prior_path.is_file() else None,
                'date_bounds': 'left-closed right-open, source timestamps', 'python': platform.python_version(),
                'pandas': pd.__version__, 'matplotlib': matplotlib.__version__, 'label_differences': label_differences,
                'review_tie_break': 'answer, creation, review_id, score; latest',
                'privacy': 'snapshot-asof-features.csv is team-only'}
    (OUT/'data-version.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    make_chart(windows)
    (OUT/'交接说明.md').write_text(report(windows, quality, availability, len(extension), label_differences), encoding='utf-8')
    names = list(outputs) + ['build_audit.py','data-version.json','time-boundaries.png','time-boundaries.svg','交接说明.md']
    (OUT/'CHECKSUMS.sha256').write_text('\n'.join(f'{sha(OUT/name)}  {name}' for name in names)+'\n', encoding='utf-8')
    with zipfile.ZipFile(OUT.with_suffix('.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in names + ['CHECKSUMS.sha256']:
            archive.write(OUT/name, arcname=f'{OUT.name}/{name}')
    print(pd.DataFrame(check_rows).to_string(index=False))
    print(windows[['snapshot_date','target_end_exclusive','target_overlap_seen_union_days',
                   'target_days_beyond_H02_bound','target_zero_qualified_days']].to_string(index=False))
    print('Done', OUT.with_suffix('.zip'))


if __name__ == '__main__':
    main()
