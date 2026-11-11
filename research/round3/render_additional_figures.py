"""Additional January baseline and time-validity research figures."""
from pathlib import Path
import json
import runpy
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
common = runpy.run_path(str(OUT / "render_figures.py"))
finish = common["finish"]
INDEX = common["INDEX"]
prior_index = [row for row in json.loads((OUT / "figure-index.json").read_text(encoding="utf-8")) if row["id"][:2] not in ("07","08","09","10")]
BLUE, GREEN, ORANGE, GRAY = [common[k] for k in ("BLUE", "GREEN", "ORANGE", "GRAY")]
metrics = pd.read_csv(OUT / "data/baselines/january-metrics.csv")
intervals = pd.read_csv(OUT / "data/baselines/bootstrap-intervals.csv")
names = {
    "recency": "Recent purchase first", "simpleMulti": "Multiple orders, then recent",
    "LR3": "Three-field LR", "LR8": "Eight-field LR",
    "weightedLR": "Eight-field weighted LR", "groupOnly": "Weighted LR + group",
}
order = list(names)

table = metrics.loc[metrics.scope.eq("global") & metrics.capacity_fraction.eq(0.1)].copy()
table["method"] = pd.Categorical(table.method, order, ordered=True)
table = table.sort_values("method")
table.to_csv(OUT / "chart-data/07-baseline-10pct.csv", index=False)
fig, ax = plt.subplots(figsize=(12, 6.8))
ys = np.arange(len(table))
bars = ax.barh(ys, table.hits, color=[GREEN if x == "weightedLR" else BLUE for x in table.method], height=0.62)
ax.bar_label(bars, padding=6, fontsize=13)
ax.set_yticks(ys, [names[x] for x in table.method])
ax.invert_yaxis()
ax.set_xlim(0, 61)
ax.set_xlabel("Repurchasers found among 2,937 selected customers")
fig.subplots_adjust(left=0.28)
finish(fig, "07-six-method-comparison", "Simple history-based rules are strong competitors",
       "一月同取2,937人，最近购买30，多单优先48，三字段51，原八字段46，加权50，加群号52。较高的单期分数仍需结合差异区间判断。",
       "Oct training; Jan development | N=29,368; positives=230 | Six fixed methods")

fig, ax = plt.subplots(figsize=(12, 6.8))
colors = [GRAY, ORANGE, "#8B65A8", "#65A1B8", GREEN, BLUE]
styles = ["--", "-.", ":", "--", "-", "-."]
for method, color, style in zip(order, colors, styles):
    part = metrics.loc[metrics.scope.eq("global") & metrics.method.eq(method)]
    ax.plot(part.capacity_fraction * 100, part.hits, marker="o", linewidth=2, linestyle=style,
            color=color, label=names[method])
ax.set_ylim(0, 85)
ax.set_xticks([5, 10, 20], ["5% (1,469)", "10% (2,937)", "20% (5,874)"])
ax.set_xlabel("List capacity")
ax.set_ylabel("Repurchasers found")
ax.legend(frameon=False, ncol=2, fontsize=10, loc="upper left")
finish(fig, "08-capacity-sensitivity", "Method rankings depend on list capacity",
       "统一比较5%、10%、20%容量，候选排序随名额改变。连线辅助读取三个已计算容量点。",
       "Jan 2018 development | Same customers and score tie-breaking rule | Computed capacities: 5%, 10%, 20%")

table = intervals.loc[intervals.scope.eq("global")].copy()
table.to_csv(OUT / "chart-data/09-bootstrap-differences.csv", index=False)
fig, ax = plt.subplots(figsize=(12, 6.8))
ys = np.arange(len(table))
for y, row in zip(ys, table.itertuples()):
    lo, hi, point = row.percentile_2_5, row.percentile_97_5, row.observed_difference
    color = GREEN if lo > 0 else BLUE
    ax.plot([lo, hi], [y, y], color=color, linewidth=3, solid_capstyle="round")
    ax.plot(point, y, "o", color=color, markersize=9)
    ax.text(hi + 0.8, y, f"{point:+.0f} [{lo:+.0f}, {hi:+.0f}]", va="center", fontsize=12)
ax.axvline(0, color=GRAY, linestyle="--", linewidth=1)
ax.set_yticks(ys, [names[x] for x in table.comparator])
ax.invert_yaxis()
ax.set_xlim(-13, 45)
ax.set_xlabel("Extra hits from weighted LR relative to the comparison method")
fig.subplots_adjust(left=0.28)
finish(fig, "09-conditional-uncertainty", "Small differences remain uncertain on the January sample",
       "点为观察到的命中差，线为2,000次配对客户重采样95%百分位区间。加权相对最近购买+20[7,34]，与另外三种强对照的区间均跨0。已拟合分数条件下的区间不包含重训或新时期的不确定性。",
       "Jan development, K=2,937 | 2,000 paired customer resamples | Conditional on fitted scores")

table = pd.read_csv(OUT / "data/time-and-profiles/candidate-seen-target-overlap.csv")
table.to_csv(OUT / "chart-data/10-time-windows.csv", index=False)
fig, ax = plt.subplots(figsize=(12.5, 6.8))
seen_start, seen_end = pd.Timestamp("2018-01-01"), pd.Timestamp("2018-06-30")
last_day_end = pd.Timestamp("2018-09-04")
ax.axvspan(seen_start, seen_end, color=ORANGE, alpha=0.13)
for y, row in enumerate(table.itertuples()):
    start, end = pd.Timestamp(row.snapshot_date), pd.Timestamp(row.target_end_exclusive)
    covered_end = min(end, last_day_end)
    ax.plot([start, covered_end], [y, y], color=BLUE, linewidth=9, solid_capstyle="butt")
    overlap_end = min(end, seen_end)
    if start < overlap_end:
        ax.plot([start, overlap_end], [y, y], color=ORANGE, linewidth=9, solid_capstyle="butt")
    if covered_end < end:
        ax.plot([covered_end, end], [y, y], color=GRAY, linewidth=3, linestyle=":")
    text = f"{row.overlap_seen_union_days}/90 days overlap"
    if row.target_outside_observed_event_date_envelope_days:
        text = f"{row.target_outside_observed_event_date_envelope_days} days beyond observed dates"
    ax.text(end + pd.Timedelta(days=3), y, text, va="center", fontsize=10)
ax.set_yticks(np.arange(len(table)), table.snapshot_date)
ax.invert_yaxis()
ax.xaxis.set_major_locator(mdates.MonthLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
ax.set_xlim(pd.Timestamp("2017-12-27"), pd.Timestamp("2018-12-01"))
ax.set_xlabel("2018 outcome-calendar dates")
ax.set_ylabel("Candidate snapshot")
fig.legend(handles=[Line2D([0],[0],color=ORANGE,lw=7,label="Overlap with previously seen target calendars"),
                   Line2D([0],[0],color=BLUE,lw=7,label="Within observed event-date envelope"),
                   Line2D([0],[0],color=GRAY,lw=2,ls=":",label="Beyond observed event dates")],
          loc="lower left", bbox_to_anchor=(0.145,0.06), frameon=False, fontsize=9)
fig.subplots_adjust(left=0.15)
finish(fig, "10-time-window-validity", "New snapshot dates still need exposure and coverage checks",
       "候选日期的90天目标与已见一月/四月目标日历重叠。7月目标虽不重叠，但有25天超出源合格事件日期上界。日历重叠不是逐客户标签完全相同的证明，数据日期覆盖也不证明无漏采。",
       "Calendar audit of 90-day targets | Raw approved positive-value orders | Outcome labels were not regenerated")
(OUT / "figure-index.json").write_text(json.dumps(prior_index + INDEX, ensure_ascii=False, indent=2) + "\n",encoding="utf-8")
print("Rendered", len(INDEX), "additional figures")
