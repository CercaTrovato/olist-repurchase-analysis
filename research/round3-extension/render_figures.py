"""Static figures for the pre-specified third-round extension."""
from pathlib import Path
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
FIGURES = OUT / "figures"
FIGURES.mkdir(exist_ok=True)
DATA = OUT / "chart-data"
ALL = pd.read_csv(DATA / "all-methods.csv")
INTERVALS = pd.read_csv(DATA / "paired-intervals.csv")
BLUE, GREEN, ORANGE, GRAY, PURPLE = "#3967A6", "#16806A", "#D7783D", "#7B8794", "#8B65A8"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":12,"axes.titlesize":14,
                     "axes.spines.top":False,"axes.spines.right":False,"svg.fonttype":"none"})
INDEX = []


def save(fig, stem, title, caption, bottom=.24):
    fig.subplots_adjust(bottom=bottom, top=.82)
    fig.suptitle(title, x=.055, y=.96, ha="left", fontsize=19, fontweight="bold")
    fig.text(.055,.028,"Oct 2017 training; Jan 2018 development | Global K=2,937; long group separately ranked K=79",
             fontsize=9,color="#536171")
    for extension in ("png","svg"):
        fig.savefig(FIGURES/f"{stem}.{extension}",dpi=240,facecolor="white")
    path=FIGURES/f"{stem}.svg"
    path.write_bytes(("\n".join(line.rstrip() for line in path.read_text(encoding="utf-8").splitlines())+"\n").encode("utf-8"))
    plt.close(fig)
    INDEX.append({"id":stem,"title":title,"caption_zh":caption,
                  "png":f"figures/{stem}.png","svg":f"figures/{stem}.svg"})


def compare_bars(ax, values, labels, title, colors):
    bars=ax.bar(np.arange(len(values)),values,color=colors,width=.6)
    ax.bar_label(bars,padding=5,fontsize=12)
    ax.set_xticks(np.arange(len(values)),labels,rotation=20,ha="right")
    ax.set_ylim(0,max(values)*1.28+.9)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_title(title)
    ax.set_ylabel("Repurchasers found")


table=ALL.loc[ALL.family.eq("nonlinear")].set_index("label")
fig,axes=plt.subplots(1,2,figsize=(12.8,6.8))
for ax,field,title,reference in [(axes[0],"global_hits","Global list",50),
                                (axes[1],"long_fixed79_hits","Long group, fixed 79",2)]:
    for shift,weight,color in [(-.18,"U",BLUE),(.18,"B",ORANGE)]:
        values=[int(table.loc[f"CB{count}-{weight}",field]) for count in (8,14)]
        bars=ax.bar(np.arange(2)+shift,values,width=.32,color=color,
                    label="Unweighted" if weight=="U" else "Balanced")
        ax.bar_label(bars,padding=5)
    ax.axhline(reference,color=GRAY,ls="--",label="Original weighted LR8")
    ax.set_xticks([0,1],["Original 8 fields","8 + delivery / review"])
    ax.set_ylim(0,62 if field=="global_hits" else 4.2)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_ylabel("Repurchasers found")
    ax.set_title(title)
axes[0].legend(frameon=False,fontsize=10,loc="lower left")
save(fig,"14-shallow-tree-inputs","A shallow learner uses the same extra information differently",
     "四版CatBoost固定300轮、深度3和种子。主容量命中48/49/50/41，久单固定79命中0/0/3/1。14字段未加权版在全局实际未选久单，固定群内多1人的条件区间[-2,4]，两项诊断分开读。")

table=pd.concat([ALL.loc[ALL.label.eq("weightedLR")],ALL.loc[ALL.family.eq("context")]],ignore_index=True)
fig,axes=plt.subplots(1,3,figsize=(15,6.8))
names=["Weighted LR","Seller context","Basket / payment","Both"]
for ax,field,title in [(axes[0],"global_hits","Global list"),
                       (axes[1],"long_global_seats","Long-group seats in global list"),
                       (axes[2],"long_fixed79_hits","Long group, fixed 79")]:
    compare_bars(ax,table[field].tolist(),names,title,[BLUE,GREEN,ORANGE,PURPLE])
    if field=="long_global_seats": ax.set_ylabel("Customers selected")
save(fig,"15-seller-commerce-context","Seller context increases total hits while retaining two fixed-group hits",
     "卖家组54/2、交易组51/1、组合56/1，依次为全局命中/固定久单79命中，原版50/2。卖家统计排除当前买家且只用历史。正向差异的条件区间仍跨0，支付及产品静态时点假设保留。")

table=pd.concat([ALL.loc[ALL.label.eq("weightedLR")],ALL.loc[ALL.family.eq("strategies")]],ignore_index=True)
fig,axes=plt.subplots(1,2,figsize=(13.8,6.8))
names=["Weighted LR","Rank W+LR3","Rank W+group","Rank W+experience","Group shrink"]
for ax,field,title in [(axes[0],"global_hits","Global list"),(axes[1],"long_fixed79_hits","Long group, fixed 79")]:
    compare_bars(ax,table[field].tolist(),names,title,[BLUE,GREEN,ORANGE,PURPLE,GRAY])
save(fig,"16-fusion-and-group-shrink","Fixed fusion and group shrinkage yield limited changes",
     "三种等权全体排名融合与一个训练支持量收缩群模型，未扫描融合权重。全局50/51/46/47，久单2/2/1/1；相对原版的主指标区间均跨0。")

table=INTERVALS.loc[INTERVALS.scope.eq("global")].copy()
assert len(table)==11
fig,ax=plt.subplots(figsize=(13,9))
colors={"nonlinear":BLUE,"context":GREEN,"strategies":PURPLE}
for y,row in enumerate(table.itertuples()):
    ax.plot([row.lower,row.upper],[y,y],color=colors[row.family],lw=2.5)
    ax.scatter(row.observed_difference,y,color=colors[row.family],s=42)
    ax.text(max(table.upper)+.8,y,f"{row.observed_difference:+.0f} [{row.lower:+.0f}, {row.upper:+.0f}]",
            va="center",fontsize=10)
ax.axvline(0,color=GRAY,ls="--",lw=1)
ax.set_yticks(np.arange(len(table)),table.label)
ax.invert_yaxis()
ax.set_xlim(min(table.lower)-2,max(table.upper)+10)
ax.set_xlabel("Global hit difference relative to original weighted LR8")
fig.subplots_adjust(left=.25)
save(fig,"17-extension-conditional-intervals","Candidate gains remain uncertain in the reused development sample",
     "11个新候选全部列出。点为观察差，线为2,000次配对客户重采样95%百分位区间，条件于已拟合分数；不包含重训、模型搜索和新时期不确定性。",
     bottom=.17)

fig,ax=plt.subplots(figsize=(12.8,7.4))
markers={"reference":"o","nonlinear":"s","context":"^","strategies":"D"}
colors={"reference":GRAY,"nonlinear":BLUE,"context":GREEN,"strategies":PURPLE}
for family,part in ALL.groupby("family",sort=False):
    ax.scatter(part.global_hits-50,part.long_fixed79_hits-2,s=74,marker=markers[family],
               color=colors[family],alpha=.7,label=family)
ax.axhline(0,color="#8F9AA6",lw=1)
ax.axvline(0,color="#8F9AA6",lw=1)
ax.scatter([0],[0],s=180,marker="*",color="black",label="Weighted LR reference")
for label,text,xytext in [
    ("Seller","Seller: 54 global / 2 long",(4.5,.9)),
    ("Seller+commerce","Both: 56 global / 1 long",(-1,-2.6)),
    ("CB14-U","CB14-U: 50 global / 3 long",(-10,1.7))]:
    row=ALL.loc[ALL.label.eq(label)].iloc[0]
    point=(row.global_hits-50,row.long_fixed79_hits-2)
    ax.annotate(text,point,xytext=xytext,textcoords="data",fontsize=11,
                arrowprops={"arrowstyle":"-","color":colors[row.family]})
ax.set_xlim(-24,11)
ax.set_ylim(-3.1,2.2)
ax.xaxis.set_major_locator(MaxNLocator(integer=True))
ax.yaxis.set_major_locator(MaxNLocator(integer=True))
ax.set_xlabel("Change in global hits vs weighted LR (K=2,937)")
ax.set_ylabel("Change in long-group hits vs weighted LR (fixed K=79)")
ax.legend(frameon=False,fontsize=10,ncol=3,loc="lower left")
save(fig,"18-global-and-within-group-diagnostics","Global coverage and within-group ranking show different trade-offs",
     "包含6个既有对照和11个新候选。横轴是全局命中变化，纵轴是独立固定久单79的命中变化，均相对50/2。点重叠时表示同一组诊断值，候选方法的完整结果见CSV；本图不表示统计显著性。")
(OUT/"figure-index.json").write_text(json.dumps(INDEX,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Rendered",len(INDEX),"extension figures")
