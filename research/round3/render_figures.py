"""Render reusable static research figures from aggregate evidence."""
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent / "data"
OUT = Path(__file__).resolve().parent
FIGURES = OUT / "figures"
DATA = OUT / "chart-data"
DATA.mkdir(exist_ok=True)
FIGURES.mkdir(exist_ok=True)
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 12,
    "axes.titlesize": 16, "axes.labelsize": 12,
    "axes.spines.top": False, "axes.spines.right": False,
    "svg.fonttype": "none", "figure.facecolor": "white",
})
BLUE, GREEN, ORANGE, GRAY = "#3967A6", "#16806A", "#D7783D", "#7B8794"
INDEX = []


def finish(fig, stem, title, caption, source):
    fig.text(0.06, 0.018, source, ha="left", va="bottom", fontsize=9, color="#536171")
    fig.subplots_adjust(bottom=0.31 if stem == "10-time-window-validity" else 0.20, top=0.82)
    fig.suptitle(title, x=0.06, ha="left", y=0.96, fontsize=19, fontweight="bold")
    for ext in ("png", "svg"):
        fig.savefig(FIGURES / f"{stem}.{ext}", dpi=240, facecolor="white")
    svg = FIGURES / f"{stem}.svg"
    svg.write_bytes(("\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines()) + "\n").encode("utf-8"))
    plt.close(fig)
    INDEX.append({"id": stem, "title": title, "caption_zh": caption,
                  "png": f"figures/{stem}.png", "svg": f"figures/{stem}.svg",
                  "source": source})


def bar_labels(ax, bars, labels=None):
    ax.bar_label(bars, labels=labels, padding=4, fontsize=12)


def sample_groups():
    table = pd.DataFrame({
        "group": ["Recent single", "Long single", "Multiple orders"],
        "customers": [16335, 12330, 703], "repurchasers": [112, 90, 28]})
    table["repurchase_rate_pct"] = 100 * table.repurchasers / table.customers
    table.to_csv(DATA / "01-groups.csv", index=False)
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.5))
    x = np.arange(3)
    bars = axes[0].bar(x, table.customers, color=[BLUE, ORANGE, GREEN], width=0.6)
    bar_labels(axes[0], bars, [f"{n:,}" for n in table.customers])
    axes[0].set_ylim(0, 19000)
    axes[0].set_ylabel("Customers")
    axes[0].set_xticks(x, table.group)
    bars = axes[1].bar(x, table.repurchase_rate_pct, color=[BLUE, ORANGE, GREEN], width=0.6)
    bar_labels(axes[1], bars, [f"{p:.2f}%\n{a}/{b:,}" for p, a, b in
                             zip(table.repurchase_rate_pct, table.repurchasers, table.customers)])
    axes[1].set_ylim(0, 5.2)
    axes[1].set_ylabel("Observed 90-day repurchase rate (%)")
    axes[1].set_xticks(x, table.group)
    axes[0].set_title("Group size")
    axes[1].set_title("Future repurchase rate")
    finish(fig, "01-group-size-and-rates", "The customer pool is mostly single-order buyers",
           "一月分群规模与复购率。近期单单16,335人、久单12,330人、多单703人。多单群复购率较高。单单指历史半年内只买一次。",
           "Jan 2018 | N=29,368; positives=230 | H02 + H05-km3-v1 | Observed historical repurchases")


def weighting():
    source = DATA / "02-weighting.csv"
    table = pd.read_csv(source)
    table.to_csv(DATA / "02-weighting.csv", index=False)
    fig, ax = plt.subplots(figsize=(11.5, 6.5))
    x = np.arange(2)
    for shift, weighted, color in [(-0.19, False, BLUE), (0.19, True, GREEN)]:
        vals = [int(table.loc[table.inputs.eq(name) & table.weighted.eq(weighted), "hits"].iloc[0])
                for name in ("rfm", "lr8")]
        bars = ax.bar(x + shift, vals, width=0.34, color=color,
                      label="Class-weighted" if weighted else "Unweighted")
        bar_labels(ax, bars)
    ax.set_xticks(x, ["R / F / M only", "Original eight fields"])
    ax.set_ylabel("Repurchasers found in the list")
    ax.set_ylim(0, 62)
    ax.legend(loc="upper right", frameon=False)
    finish(fig, "02-fields-by-weighting", "Class weighting helps one input set and hurts another",
           "一月相同2,937个名额，三字段加权51→48，八字段加权46→50。加权收益取决于输入组合。",
           "Oct 2017 training; Jan 2018 development | K=2,937 | Four controlled fits")


def group_interactions():
    source = DATA
    totals = pd.read_csv(source / "03-h05-totals.csv")
    groups = pd.read_csv(source / "03-h05-groups.csv")
    totals.to_csv(DATA / "03-h05-totals.csv", index=False)
    groups.to_csv(DATA / "03-h05-groups.csv", index=False)
    names = ["Weighted LR", "+ group", "+ group x 2 fields", "+ group x amount"]
    fig, axes = plt.subplots(1, 3, figsize=(15.2, 6.8))
    x = np.arange(4)
    for ax, values, title, ylabel in [
        (axes[0], totals.hits, "All customers: K=2,937", "Repurchasers found"),
        (axes[1], groups.loc[groups.group.eq(1), "selected"], "Long-single seats in global list", "Selected long-single customers"),
        (axes[2], totals.long_fixed_hits, "Long-single only: K=79", "Repurchasers found")]:
        bars = ax.bar(x, list(values), color=[BLUE, GREEN, ORANGE, GRAY], width=0.65)
        bar_labels(ax, bars)
        ax.set_xticks(x, names, rotation=25, ha="right")
        ax.set_title(title, fontsize=12)
        ax.set_ylabel(ylabel)
        ax.set_ylim(0, max(values) * 1.3 + 0.8)
    finish(fig, "03-global-versus-fixed-group", "Global coverage and fixed-group ranking answer different questions",
           "加入群号全局50→52，但固定久单79名额仍命中2人。两项交互和金额单项交互都降为全局42、固定久单0。",
           "Oct training; Jan development | Same H05 groups | Fixed-group evaluation is a diagnostic")


def graph_grid():
    table = pd.read_csv(DATA / "04-graph-grid.csv")
    table = table.loc[table.method.eq("gcn")].copy()
    table.to_csv(DATA / "04-graph-grid.csv", index=False)
    specs = [(1, 0), (2, 8), (2, 16), (3, 8), (3, 16)]
    order = ["rfm", "category", "seller"]
    medians, ranges = [], []
    for depth, hidden in specs:
        values = [table.loc[table.graph.eq(name) & table.depth.eq(depth) & table.hidden.eq(hidden), "hits"]
                  for name in order]
        assert all(len(v) == 3 for v in values)
        medians.append([v.median() for v in values])
        ranges.append([(int(v.min()), int(v.max())) for v in values])
    fig, ax = plt.subplots(figsize=(11.5, 7.2))
    ax.imshow(medians, cmap="Blues", vmin=20, vmax=55, aspect="auto")
    fig.subplots_adjust(left=0.25)
    ax.set_xticks(np.arange(3), ["R/F/M neighbors", "Historical same category", "Historical same seller"])
    ax.set_yticks(np.arange(5), ["1 layer", "2 layers / 8 units", "2 layers / 16 units",
                               "3 layers / 8 units", "3 layers / 16 units"])
    for i in range(5):
        for j in range(3):
            lo, hi = ranges[i][j]
            ax.text(j, i, f"{medians[i][j]:.0f}\n({lo}-{hi})", ha="center", va="center",
                    color="white" if medians[i][j] > 41 else "#162D48", fontsize=13)
    finish(fig, "04-graph-design-grid", "Graph construction and depth change the result",
           "格内为三种子命中中位数，括号为最小—最大。所有结果来自同一已见一月，不是三期验证。",
           "Jan 2018 development | K=2,937 | Median (min-max), seeds 2026/2027/2028 | Seed ranges within one development period")


def residual():
    table = pd.read_csv(DATA / "05-residual.csv")
    table.to_csv(DATA / "05-residual.csv", index=False)
    names = ["GCN", "GCN + contrast", "GCN + residual", "GCN + both"]
    methods = ["gcn_only", "gcn_with_contrast", "residual_only", "residual_with_contrast"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 6.8))
    colors = [BLUE, ORANGE, GREEN]
    for ax, field, title, top, reference in [
        (axes[0], "hits", "All customers: K=2,937", 56, 50),
        (axes[1], "long_hits", "Long-single hits in the global list", 5.3, 2)]:
        for seed, color, shift in zip((2026, 2027, 2028), colors, (-0.1, 0, 0.1)):
            vals = [float(table.loc[table.method.eq(method) & table.seed.eq(seed), field].iloc[0])
                    for method in methods]
            ax.plot(np.arange(4) + shift, vals, "o-", color=color, linewidth=1, alpha=0.85, label=str(seed))
        ax.axhline(reference, color=GRAY, linestyle="--", linewidth=1.3, label="Weighted LR reference")
        ax.set_ylim(0, top)
        ax.set_xticks(np.arange(4), names, rotation=15, ha="right")
        ax.set_ylabel("Repurchasers found")
        ax.set_title(title, fontsize=13)
    axes[0].legend(frameon=False, fontsize=10, ncol=2, loc="lower left")
    finish(fig, "05-gcn-residual-contrast", "Residual connections restore total hits while long-single hits fall",
           "同卖家图、两层8维。加残差与对比后的全局命中46/48/44，久单0/1/0。点是随机种子，不能解释为时间稳定性。",
           "Oct training; Jan development | Same-seller graph, two layers / 8 units | Three fixed seeds")


def category_shift():
    table = pd.DataFrame({
        "period": ["Oct training", "Jan development"],
        "category_n": [557, 816], "category_hits": [12, 7],
        "other_n": [8564, 11514], "other_hits": [66, 83]})
    table.to_csv(DATA / "06-category-shift.csv", index=False)
    fig, ax = plt.subplots(figsize=(11.5, 6.5))
    for prefix, color, label in [("category", GREEN, "Furniture / decor observed"),
                                ("other", BLUE, "Category not observed")]:
        rate = 100 * table[f"{prefix}_hits"] / table[f"{prefix}_n"]
        ax.plot([0, 1], rate, "o-", color=color, linewidth=2, markersize=9, label=label)
        for x, y, hits, n in zip([0, 1], rate, table[f"{prefix}_hits"], table[f"{prefix}_n"]):
            ax.annotate(f"{y:.2f}% ({hits}/{n:,})", (x, y), xytext=(0, 12 if prefix == "category" else -24),
                        textcoords="offset points", ha="center", fontsize=12)
    ax.set_ylim(0, 2.9)
    ax.set_xlim(-0.3, 1.3)
    ax.set_xticks([0, 1], table.period)
    ax.set_ylabel("Observed 90-day repurchase rate (%)")
    ax.legend(frameon=False, loc="upper right")
    finish(fig, "06-feature-evidence-shift", "A promising training difference shrinks in development",
           "久单群家具装饰候选在十月差异较大，到一月差距收窄。历史比例用于提出特征假设，模型增益另验。",
           "Long-single group | Training-selected category | Repeated buyers may appear across periods")


if __name__ == "__main__":
    sample_groups()
    weighting()
    group_interactions()
    graph_grid()
    residual()
    category_shift()
    (OUT / "figure-index.json").write_text(json.dumps(INDEX, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Rendered", len(INDEX), "figures")
