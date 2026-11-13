import pandas as pd
import os

DIR_2 = "../input/"

print("===== 1. 核对十月与一月分母 =====")
lab = pd.read_csv(os.path.join(DIR_2, "snapshot_labels.csv"))
oct_ = lab[lab["split"] == "development_train"]
jan_ = lab[lab["split"] == "development_validation"]
print(f"十月：人数={len(oct_)}, 正例={int(oct_['y'].sum())} (2号: 21160/211)")
print(f"一月：人数={len(jan_)}, 正例={int(jan_['y'].sum())} (2号: 29368/230)")

print("\n===== 2. 核对十月三群人数 =====")
tr = pd.read_csv(os.path.join(DIR_2, "training_clusters.csv"))
oct_merged = oct_.merge(tr, on=["customer_unique_id", "snapshot_date"])
for g in [0, 1, 2]:
    pool = oct_merged[oct_merged["cluster_id"] == g]
    print(f"群{g}：人数={len(pool)}, 正例={int(pool['y'].sum())} (2号: 11489/114, 9121/78, 550/19)")

print("\n===== 3. 核对 1 号特征一月缺失 =====")
f1 = pd.read_csv(os.path.join(DIR_2, "snapshot-asof-features.csv"))
jan_feat = jan_.merge(f1, on=["customer_unique_id", "snapshot_date"], how="left")
print(f"一月有送达：{int(jan_feat['delivered_known_n'].gt(0).sum())} (2号: 26355)")
print(f"一月有评分：{int(jan_feat['review_known_n'].gt(0).sum())} (2号: 26350)")
print(f"一月配送缺失：{int(jan_feat['delivery_days_mean'].isna().sum())} (2号: 3013)")
print(f"一月评分缺失：{int(jan_feat['review_score_mean'].isna().sum())} (2号: 3018)")

print("\n===== 4. 核对 2 号筛选表 (candidate-screening) =====")
sc_path = os.path.join(DIR_2, "candidate-screening.csv")
if os.path.exists(sc_path):
    sc = pd.read_csv(sc_path)
    print(f"candidate-screening.csv 行数: {len(sc)} (2号说 14 项)")

    # 动态寻找代表“候选名”的列（可能是字段名或ID）
    col_id = None
    for c in sc.columns:
        if "candidate" in c.lower() or "field" in c.lower() or "id" in c.lower():
            col_id = c
            break
    if not col_id: col_id = sc.columns[0]  # 保底取第一列

    # 找 C07
    c07 = sc[sc[col_id].astype(str).str.contains("C07", na=False)]
    if not c07.empty:
        print("\n【C07 late_delivery_share 在筛选表中的完整记录】:")
        print(c07.T.to_string(header=False))
else:
    print("找不到 candidate-screening.csv")
