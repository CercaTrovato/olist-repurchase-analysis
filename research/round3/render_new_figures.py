"""Render new-field and proposed content-trial figures."""
from pathlib import Path
import json
import runpy
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
common = runpy.run_path(str(OUT / "render_figures.py"))
finish, INDEX = common["finish"], common["INDEX"]
BLUE, GREEN, ORANGE, GRAY = [common[k] for k in ("BLUE", "GREEN", "ORANGE", "GRAY")]
prior = [row for row in json.loads((OUT / "figure-index.json").read_text(encoding="utf-8"))
         if row["id"][:2] not in ("11", "12", "13")]
metrics = pd.read_csv(OUT / "data/features/january-metrics.csv")
groups = pd.read_csv(OUT / "data/features/january-groups.csv")
global_rows = metrics.loc[metrics.scope.eq("global") & metrics.capacity.eq("10pct")]
long_rows = metrics.loc[metrics.scope.eq("long_fixed")]
seats = groups.loc[groups.scope.eq("global") & groups.capacity.eq("10pct") & groups.cluster_id.eq(1)]
assert list(global_rows.model) == list(long_rows.model) == list(seats.model)
metrics.to_csv(OUT / "chart-data/11-new-field-results.csv", index=False)
labels = ["Original weighted", "+ delivery", "+ review", "+ both"]
fig, axes = plt.subplots(1, 3, figsize=(15.2, 6.8))
for ax, values, title, ylabel in [
    (axes[0], global_rows.hits, "All customers: K=2,937", "Repurchasers found"),
    (axes[1], seats.selected, "Long-single seats in global list", "Selected long-single customers"),
    (axes[2], long_rows.hits, "Long-single only: K=79", "Repurchasers found")]:
    bars = ax.bar(np.arange(4), list(values), width=0.6, color=[BLUE, GREEN, ORANGE, GRAY])
    ax.bar_label(bars, padding=4, fontsize=12)
    ax.set_xticks(np.arange(4), labels, rotation=20, ha="right")
    ax.set_ylim(0, max(values) * 1.28 + 0.8)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=12)
finish(fig, "11-new-information-ablation", "New delivery and review fields do not improve the main comparison",
       "冻结两个新字段组后，一月全局原版50，配送46、评价45、组合46；久单固定79人分别2、2、1、1。组合版在全局给久单281个名额、命中4，与固定名额结果同时报告。",
       "Oct training; Jan development | Four pre-specified weighted LR input sets | Timestamp-safe features")

table = pd.read_csv(OUT / "data/time-and-profiles/trial-theme-support.csv")
table = table.loc[table.snapshot_date.eq("2018-01-01")].sort_values("cluster_id")
table.to_csv(OUT / "chart-data/12-theme-support.csv", index=False)
fig, ax = plt.subplots(figsize=(11.8, 6.8))
bars = ax.bar(np.arange(3), table.group_share * 100, width=0.56, color=[BLUE, ORANGE, GREEN])
ax.bar_label(bars, labels=[f"{p*100:.2f}%\n{n:,}/{d:,}" for p,n,d in
                          zip(table.group_share, table.group_support_customers, table.group_denominator)],
             padding=6, fontsize=12)
all_share = table.all_share.iloc[0] * 100
ax.axhline(all_share, color=GRAY, linewidth=1.5, linestyle="--",
           label=f"All January customers: {all_share:.2f}%")
ax.set_xticks(np.arange(3), ["Recent single", "Long single", "Multiple orders"])
ax.set_ylim(0, 30)
ax.set_ylabel("Customers with bed / bath / table purchases (%)")
ax.legend(frameon=False, loc="upper left", fontsize=11)
finish(fig, "12-content-theme-support", "Historical category support can motivate a content hypothesis",
       "床品/卫浴/餐桌用品主题按十月全体历史支持人数选择。一月三群买过的客户为1558/16335、1355/12330、165/703，整体3078/29368。客户按类别去重，比例为历史支持。",
       "Jan historical purchases, t-6 months to t | Theme selected using October support counts")

table = pd.read_csv(OUT / "data/time-and-profiles/trial-sample-size-planning.csv")
table.to_csv(OUT / "chart-data/13-trial-power-planning.csv", index=False)
fig, ax = plt.subplots(figsize=(11.8, 6.8))
bars = ax.barh(np.arange(3), table.required_per_arm, height=0.55,
               color=[BLUE, BLUE, GREEN])
ax.bar_label(bars, labels=[f"{n:,} per arm" for n in table.required_per_arm], padding=6)
available = int(table.balanced_available_per_arm.iloc[0])
ax.axvline(available, color=ORANGE, linewidth=2, linestyle="--",
           label=f"Historical upper bound: {available:,} per arm")
ax.set_yticks(np.arange(3), [f"+{100*x:.1f} percentage points" for x in table.absolute_effect])
ax.invert_yaxis()
ax.set_xlim(0, max(table.required_per_arm) * 1.23)
ax.set_xlabel("Required customers per randomized arm (planning approximation)")
ax.legend(frameon=False, loc="lower right")
fig.subplots_adjust(left=0.25)
finish(fig, "13-content-trial-feasibility", "Illustrative sample-size planning for a future content trial",
       "假设控制率0.783%、双侧5%、80%功效，识别绝对+0.5个百分点约需每组6420人。历史主题支持池3078人只是联系资格损失前的上限。最小效应需由真实业务价值确定。",
       "Proposed trial, not an observed effect | Two-arm normal approximation | No treatment records in Olist")
(OUT / "figure-index.json").write_text(json.dumps(prior + INDEX, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("Rendered", len(INDEX), "new-field and content figures")
