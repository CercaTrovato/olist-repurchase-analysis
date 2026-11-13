import os
import pandas as pd

# ===== 路径 =====
PATH_H02 = "../input/snapshot_labels.csv"
PATH_F1  = "../input/snapshot-asof-features.csv"
KEY = ["customer_unique_id", "snapshot_date"]

# ===== 读表 =====
h02 = pd.read_csv(PATH_H02)
f1  = pd.read_csv(PATH_F1)

# ---------- A. 标签表本身 ----------
print("===== A. 标签表 =====")
print("行数:", len(h02))
print("列:", list(h02.columns))
print("split:", h02["split"].unique())
print("快照:", h02["snapshot_date"].unique())
jan_h02 = h02[h02["snapshot_date"] == "2018-01-01"]
print("一月人数:", len(jan_h02), "正例:", int(jan_h02["y"].sum()))

# ---------- B. 特征表本身 ----------
print("\n===== B. 特征表 =====")
print("【1】特征表行数:", len(f1))
print("【1】键重复:", int(f1.duplicated(subset=KEY).sum()))
print("【1】快照分布:\n", f1["snapshot_date"].value_counts().sort_index())
print("【1】data_version:", f1["data_version"].unique())
print("【1】feature_version:", f1["feature_version"].unique())

# ---------- C. 一对一左接 ----------
print("\n===== C. 拼表 =====")
df = h02.merge(f1, on=KEY, how="left", validate="one_to_one")
print("【2】H02行数:", len(h02), "拼后行数:", len(df))
print("【2】特征漏配(delivered_known_n空):", int(df["delivered_known_n"].isna().sum()))

dv_cols = [c for c in df.columns if c.startswith("data_version")]
print("【2】data_version相关列:", dv_cols)
dv_feat = dv_cols[-1]
print("【2】特征漏配(更准):", int(df[dv_feat].isna().sum()))

# ---------- D. 一月 ----------
print("\n===== D. 一月 =====")
jan = df[df["split"] == "development_validation"].copy()
print("【3】一月人数:", len(jan), "正例:", int(jan["y"].sum()))

# ---------- E. 缺失（订单笔数参考）----------
print("\n===== E. 缺失 =====")
print("【4】配送时长缺失:", int(jan["delivery_days_mean"].isna().sum()), "(应3013)")
print("【4】评分缺失:", int(jan["review_score_mean"].isna().sum()), "(应3018)")
print("【4】有送达订单笔数加总:", int(jan["delivered_known_n"].sum()), "(1号订单笔数参考27032)")
print("【4】有评分订单笔数加总:", int(jan["review_known_n"].sum()), "(1号订单笔数参考27030)")

# ---------- F. 无事件 ----------
print("\n===== F. 无事件 =====")
z = jan[jan["delivered_known_n"] == 0]
print("【5】无送达人数:", len(z))
print("【5】计数全0:", bool((z["delivered_known_n"] == 0).all()))
print("【5】均值全空:", bool(z["delivery_days_mean"].isna().all()))

# ---------- G. 疑似未来字段 ----------
print("\n===== G. 未来字段 =====")
future_kw = ["future", "after_snapshot", "target_", "label_"]
bad = [c for c in f1.columns if any(k in c.lower() for k in future_kw)]
print("【附】疑似未来字段:", bad if bad else "无")

# ---------- H. 人数口径同口径校验（与2号对齐）----------
print("\n===== H. 人数口径校验 =====")
n_people_delivered = int(jan["delivered_known_n"].gt(0).sum())
n_missing_delivery = int(jan["delivery_days_mean"].isna().sum())
print("有送达订单人数:", n_people_delivered, "(2号: 26355)")
print("平均时长缺失人数:", n_missing_delivery, "(1号/2号: 3013)")
print("两者相加:", n_people_delivered + n_missing_delivery, "(应=29368)")

n_people_review = int(jan["review_known_n"].gt(0).sum())
n_missing_review = int(jan["review_score_mean"].isna().sum())
print("有评分订单人数:", n_people_review, "(2号: 26350)")
print("平均评分缺失人数:", n_missing_review, "(1号/2号: 3018)")
print("两者相加:", n_people_review + n_missing_review, "(应=29368)")

print("\n----- 同口径判断 -----")
print("送达人数一致(26355):", n_people_delivered == 26355)
print("评分人数一致(26350):", n_people_review == 26350)
print("送达缺失一致(3013):", n_missing_delivery == 3013)
print("评分缺失一致(3018):", n_missing_review == 3018)
