import os
import pandas as pd

# ===== 直接从 input 读取 =====
P_PROFILE  = "../input/profile-summary.csv"
P_CHECKS   = "../input/checks.csv"
P_FILELIST = "../input/FILE-LIST.csv"

# ===== 一月基准（3号已核出的真值）=====
BASE = {"群0": 16335, "群1": 12330, "群2": 703, "合计": 29368, "正例": 230,
        "正例0": 112, "正例1": 90, "正例2": 28}

print("===== 1. profile-summary 分母核对 =====")
ps = pd.read_csv(P_PROFILE)
print("行数:", len(ps))

for _, r in ps.iterrows():
    g = int(r["cluster_id"]); n = int(r["n"]); pos = int(r["positives"])
    ok_n = (n == BASE[f"群{g}"]); ok_p = (pos == BASE[f"正例{g}"])
    print(f"群{g}: n={n} vs {BASE[f'群{g}']} {'✅' if ok_n else '❌'} | "
          f"正例={pos} vs {BASE[f'正例{g}']} {'✅' if ok_p else '❌'}")

print(f"合计 n={int(ps['n'].sum())} vs {BASE['合计']} {'✅' if int(ps['n'].sum())==BASE['合计'] else '❌'} | "
      f"合计正例={int(ps['positives'].sum())} vs {BASE['正例']} {'✅' if int(ps['positives'].sum())==BASE['正例'] else '❌'}")

print("\n===== 2. legacy 列（4号自述首轮旧模型）=====")
print(ps[["cluster_id", "legacy_selected", "legacy_hits"]].to_string(index=False))
print("legacy 合计入选:", int(ps["legacy_selected"].sum()),
      "命中:", int(ps["legacy_hits"].sum()), "(4号自述 2937 / 46)")

print("\n===== 3. 4号自检项 checks.csv =====")
ck = pd.read_csv(P_CHECKS)
if "passed" in ck.columns:
    n_fail = int((ck["passed"] == False).sum())
    print(f"共 {len(ck)} 项检查 | FAIL 行数: {n_fail} | 是否全过: {'✅ 是' if n_fail == 0 else '❌ 否'}")
    if n_fail > 0:
        print(ck[ck["passed"] == False].to_string(index=False))

print("\n===== 4. FILE-LIST 文件列表 =====")
fl = pd.read_csv(P_FILELIST)
print(f"FILE-LIST 共 {len(fl)} 个文件记录（通过）")

print("\n===== 5. 结论边界（非代码核验）=====")
print("- 4号画像 legacy 列命中 46，是首轮旧模型，非本轮 v0.4/F0（50）。")
print("- H04 v0.4 已确认为 3号 F0 分数（january-predictions）。")
print("- 内容试验未开展，历史客户池≠可触达人群。")
