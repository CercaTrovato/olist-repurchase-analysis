# check_role03.py —— 5号核验 3号 F0/B/C
import pandas as pd

KEY = ["customer_unique_id", "snapshot_date"]

f0  = pd.read_csv("../input/january-predictions.csv")
gp  = pd.read_csv("../input/group-model-predictions.csv")
val = pd.read_csv("../input/validation_clusters.csv")
tr  = pd.read_csv("../input/training_clusters.csv")

print("===== 0. 输入概况 =====")
print("F0 表:", len(f0), "正例:", int(f0["y"].sum()), "重复:", int(f0.duplicated(KEY).sum()))
print("群组表:", len(gp), "正例:", int(gp["y"].sum()), "重复:", int(gp.duplicated(KEY).sum()))
print("一月群:", len(val), "分布:", val["cluster_id"].value_counts().sort_index().to_dict(),
      "版本:", val["cluster_version"].unique())
print("十月群:", len(tr), "分布:", tr["cluster_id"].value_counts().sort_index().to_dict(),
      "版本:", tr["cluster_version"].unique())

print("\n===== 1. 群标记核验 =====")
print("一月键重复:", int(val.duplicated(KEY).sum()))
print("十月键重复:", int(tr.duplicated(KEY).sum()))
print("一月快照:", val["snapshot_date"].unique())
print("十月快照:", tr["snapshot_date"].unique())
print("一月群1人数(久单):", int((val["cluster_id"]==1).sum()))

print("\n===== 2. 分数表覆盖 =====")
print("F0 覆盖一月全量:", len(f0)==29368)
print("群组覆盖一月全量:", len(gp)==29368)

print("\n===== 3. 我的分数表与群组表是否同池 =====")
m = f0[KEY+["y","F0_base_weighted_score"]].merge(
    gp[KEY+["cluster_id","y"]], on=KEY, how="outer", suffixes=("_f0","_gp"))
print("合并后:", len(m), "F0缺:", int(m["F0_base_weighted_score"].isna().sum()),
      "群组缺:", int(m["cluster_id"].isna().sum()))
print("y一致:", bool((m["y_f0"].fillna(-1)==m["y_gp"].fillna(-1)).all()))

def topk(d, col, k):
    x = d.sort_values([col,"customer_unique_id"], ascending=[False,True]).head(k)
    return len(x), int(x["y_f0"].sum())

print("\n===== 4. F0 加权（主方案）容量 =====")
for cap,tag in [(1469,"5%"),(2937,"10%"),(5874,"20%")]:
    n,h = topk(m, "F0_base_weighted_score", cap)
    print(f"Top {cap} ({tag}): 入选 {n}, 命中 {h}")

print("\n===== 5. F0 未加权（对照）=====")
for cap in [1469,2937,5874]:
    n,h = topk(m, "F0_base_unweighted_score" if "F0_base_unweighted_score" in m else "F0_base_weighted_score", cap)
    # 未加权在 f0 表，单独下面补
for cap in [1469,2937,5874]:
    x = f0.sort_values(["F0_base_unweighted_score","customer_unique_id"], ascending=[False,True]).head(cap)
    print(f"Top {cap}: 入选 {len(x)}, 命中 {int(x['y'].sum())}")

print("\n===== 6. B / C 群组方案容量 =====")
for col in ["F0_global_weighted_score","B_global_with_cluster_score","C_segmented_group2_global_fallback_score"]:
    print(f"-- {col} --")
    for cap in [1469,2937,5874]:
        x = gp.sort_values([col,"customer_unique_id"], ascending=[False,True]).head(cap)
        print(f"   Top {cap}: 命中 {int(x['y'].sum())}")

print("\n===== 7. 逐群指标（F0 全局 2937）=====")
sel = gp.sort_values(["F0_global_weighted_score","customer_unique_id"], ascending=[False,True]).head(2937)
rows=[]
for g in sorted(gp["cluster_id"].unique()):
    pool = gp[gp["cluster_id"]==g]; ch = sel[sel["cluster_id"]==g]
    ns,hit,pos = len(ch), int(ch["y"].sum()), int(pool["y"].sum())
    prec = round(hit/ns,4) if ns>0 else "缺定义"
    rec  = round(hit/pos,4) if pos>0 else "缺定义"
    rows.append({"群":int(g),"群客户":len(pool),"正例":pos,"入选":ns,"命中":hit,"精确率":prec,"召回率":rec})
print(pd.DataFrame(rows).to_string(index=False))

print("\n===== 8. 久单群固定79 =====")
g1 = gp[gp["cluster_id"]==1]
for col,label in [("F0_global_weighted_score","F0"),
                  ("B_global_with_cluster_score","B"),
                  ("C_segmented_group2_global_fallback_score","C")]:
    s = g1.sort_values([col,"customer_unique_id"], ascending=[False,True]).head(79)
    print(f"{label}: 群1客户 {len(g1)}, 正例 {int(g1['y'].sum())}, 入选 {len(s)}, 命中 {int(s['y'].sum())}")

print("\n===== 9. 与3号自带selected标志核对 =====")
for col in ["F0_global_weighted_selected_10","B_global_with_cluster_selected_10",
            "C_segmented_group2_global_fallback_selected_10"]:
    print(col, "选中:", int(gp[col].sum()), "命中:", int(gp.loc[gp[col]==1,"y"].sum()))
