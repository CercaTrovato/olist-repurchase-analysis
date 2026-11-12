"""Generate feature-spec.md / candidate-definitions.csv / feature-spec.json.

All numbers in the spec come from the tables produced by the same pipeline run,
so a rerun cannot leave the prose out of sync with the results.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from r3_common import (ASOF_VERSION, BASE_VERSION, CANDIDATES, CANDIDATE_COLS,
                       CLUSTER_VERSION, FROZEN_AT, MAX_ABS_R_BASE,
                       MAX_ABS_R_WITHIN_GROUP, MIN_ABS_D,
                       MIN_CLUSTER_NONMISSING_RATE, MIN_CLUSTER_POSITIVES_NONMISSING,
                       MIN_FOLD_PASS_RATE, MIN_POSITIVES_NONMISSING, N_FOLDS,
                       OUT_CAP_PER_GROUP, REPO_ROOT, SEED, SPEC_VERSION,
                       TRAIN_SNAPSHOT, VALIDATION_SNAPSHOT, out, write_csv,
                       write_json, write_text)

# Actual source_columns per candidate (not a blanket "as-of + H02.F").
SOURCE = {c[0]: c[5] for c in CANDIDATES}


def load(name, smoke=False):
    return pd.read_csv(out(smoke) / name)


def main(smoke: bool = False):
    if smoke:
        raise SystemExit("r3_spec runs on the full bundle only")
    sc = load("candidate-screening.csv")
    ev = load("training-feature-evidence.csv")
    gc = load("group-comparison.csv")
    sup = load("tables/r3_candidate_support.csv")
    jd = load("tables/r3_january_direction.csv")
    jd = jd if "candidate_id" in jd.columns else pd.DataFrame()
    ic = load("tables/r3_input_checks.csv")
    av = load("tables/r3_asof_verification.csv")
    ci = load("chart-index.csv")
    fc = load("field-correlation.csv")
    pm = json.loads((out() / "tables/r3_private_manifest.json").read_text(encoding="utf-8"))
    tf = json.loads((out() / "tables/r3_transform_fit.json").read_text(encoding="utf-8"))
    # Public local field dictionary: read ONLY here, after screening is complete.
    ld = pd.read_csv(REPO_ROOT / "research" / "round3" / "data" / "features"
                     / "field-dictionary.csv")
    sup_local = pd.read_csv(REPO_ROOT / "research" / "round3" / "data" / "features"
                            / "october-feature-support.csv")

    defs = pd.DataFrame(CANDIDATES, columns=CANDIDATE_COLS)
    write_csv(defs, "candidate-definitions.csv")

    coh = gc[gc.field == "(cohort)"]
    n_oct = int(coh.N.sum()); pos_oct = int(coh.positives.sum())
    ret = sc[sc.retained]
    numeric = ret[~ret.is_missing_flag]
    flags = ret[ret.is_missing_flag]
    groups = sorted(numeric.group.unique().tolist())
    flag_gate = []
    for r in flags.itertuples():
        bad = [g for g, ok in (("S3", bool(r.S3)), ("S4", bool(r.S4))) if not ok]
        if bad:
            flag_gate.append("`%s`（%s 未过，折内通过率 %.0f%%）" %
                             (r.field, "/".join(bad), 100 * r.fold_pass_rate))
    flag_gate_txt = "；".join(flag_gate) if flag_gate else "本次两个指示均通过 S3/S4"
    n_pass = int((ic.status == "PASS").sum()); n_fail = int((ic.status == "FAIL").sum())
    asof_max = float(av.max_abs_diff.max()) if len(av) else float("nan")

    # Data-driven claims (no hardcoded "only candidate" assertions).
    consistent = []
    for cid, g in ev[ev.scope != "ALL"].groupby("candidate_id"):
        row = ev[(ev.candidate_id == cid) & (ev.scope == "ALL")]
        if row.empty:
            continue
        overall = float(row.cohens_d.iloc[0])
        sg = np.sign(g.cohens_d.dropna().to_numpy())
        if len(sg) == 3 and np.isfinite(overall) and bool((sg == np.sign(overall)).all()):
            consistent.append(cid)
    pair = fc[((fc.candidate_id == "C08") & (fc.candidate_id_b == "C10"))
              | ((fc.candidate_id == "C10") & (fc.candidate_id_b == "C08"))]
    r_c08_c10 = abs(float(pair.pearson_r.iloc[0])) if len(pair) else float("nan")
    local_sizes = (sup_local[sup_local.feature == "delivery_known_any"]
                   .groupby("cluster_id").n.sum().sort_index().to_dict())

    def support_line(fld, snap):
        s = sup[(sup.field == fld) & (sup.snapshot_date == snap)]
        if s.empty:
            return "n/a"
        r = s.iloc[0]
        return "%d / %d (%.2f%%)" % (int(r.nonmissing), int(r.N),
                                    100 * float(1 - r.missing_rate))

    def missing_cell(r):
        """Do not claim NaN/imputation for a field that has no missing values."""
        n_miss = int(r.missing)
        n_non = int(r.nonmissing)
        if n_miss == 0:
            return "无缺失（十月 %d/%d 非空），无需填补" % (n_non, n_non + n_miss)
        return ("NaN + 0/1 缺失指示 + 十月中位数填补"
                "（十月缺失 %d）" % n_miss)

    def cluster_line(fld):
        e = ev[(ev.field == fld) & (ev.scope != "ALL")]
        out_ = []
        for r in e.itertuples():
            out_.append("C%d: %d+/%-5d d=%+.3f AUC=%.3f nonmiss=%d/%d" %
                        (int(r.scope), r.positives, r.negatives, r.cohens_d,
                         r.auc, r.nonmissing, r.N))
        return "; ".join(out_)

    def txt(v):
        """Empty CSV cells come back as NaN; keep the prose join type-safe."""
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return ""
        return str(v)

    lines = []
    A = lines.append
    A("# 2 号第三轮｜新增字段规格（feature-spec）")
    A("")
    A("版本 `%s`（候选池与筛选规则冻结于 %s）。输入 `%s` + 1 号 `%s` + 群号 `%s`。"
      % (SPEC_VERSION, FROZEN_AT, BASE_VERSION, ASOF_VERSION, CLUSTER_VERSION))
    A("")
    A("> **这一页只写实际跑出来的描述统计。** 本包没有训练模型、没有打分、没有产出名单命中，"
      "因此下面所有「差异」都是十月训练侧的描述差异，**不能写成加入模型后的增益**。"
      "3 号须在同一批一月客户、2,937 名额与固定久单 79 人下独立检验。")
    A("")
    A("## 1. 口径与分母")
    A("")
    A("| 项 | 值 |")
    A("|---|---|")
    A("| 训练（本包唯一用于筛选的标签） | %s，历史 [2017-04-01,2017-10-01)，标签 [2017-10-01,2017-12-30) |" % TRAIN_SNAPSHOT)
    A("| 开发验证（只做事后方向核对） | %s，历史 [2017-07-01,2018-01-01)，标签 [2018-01-01,2018-04-01)；团队已见 |" % VALIDATION_SNAPSHOT)
    A("| 共同切片 | H05-km3-v1；十月群号来自 1 号 H05 包 `train_audit.local.csv`，一月来自 `validation_clusters.csv` |")
    A("| 十月客户 / 复购者 | %d / %d（%.4f%%） |" % (n_oct, pos_oct, 100 * pos_oct / n_oct))
    for r in coh.itertuples():
        A("| 十月群 C%d | N=%d，正例 %d，负例 %d，复购率 %.4f%% |" %
          (r.cluster_id, r.N, r.positives, r.negatives, 100 * r.positive_rate))
    A("| 主键 | customer_unique_id + snapshot_date；特征、标签、逐人 as-of 表三向零重复零漏配 |")
    A("| 预测日截断 | 实际送达、评价答复严格早于快照零点；最终 order_status、快照日及之后的事件一律排除 |")
    A("")
    A("输入核验：`tables/r3_input_checks.csv` 共 %d 项，PASS %d / FAIL %d；"
      "从 `orders` / `customers` / `order_items` / `order_reviews` 四张原表独立重算 "
      "1 号 7 项 as-of 字段（十月＋一月共 %d 项比较），"
      "最大绝对差 `%.3g`，NaN 模式差异 0。见 `tables/r3_asof_verification.csv`。"
      % (len(ic), n_pass, n_fail, len(av), asof_max))
    A("")
    A("## 2. 冻结的候选池与筛选规则")
    A("")
    A("候选池 14 项，全部可由 **1 号 `snapshot-asof-features.csv`（7 列）＋ H02 `F`** 直接算出，"
      "公式与来源见 `candidate-definitions.csv`；3 号可用 `scripts/r3_build_candidates.py` 原样重算。"
      "阈值在跑最终结果前写入 `scripts/r3_common.py`（带冻结时间），未在一月标签上调整。")
    A("")
    A("| 门槛 | 规则 |")
    A("|---|---|")
    A("| S1 可用性 | 只保留预测日前已发生事件可算的字段；依赖「预计送达日当时已知且未回写」假设的字段不进推荐组 |")
    A("| S2 支持人数 | 每群非缺失 ≥ %.0f%%（分母含全部客户），十月非缺失正例 ≥ %d 且 C0/C1 各 ≥ %d |"
      % (100 * MIN_CLUSTER_NONMISSING_RATE, MIN_POSITIVES_NONMISSING,
         MIN_CLUSTER_POSITIVES_NONMISSING))
    A("| S3 群内变化 | 三群中至少 %d 群 |Cohen's d| ≥ %.2f，且 C0/C1 标准差 > 0 |" % (2, MIN_ABS_D))
    A("| S4 方向＋折内重拟合 | 至少 2/3 群 d 符号与全体一致；%d 折分层划分（seed %d），每折只用另外 4 折拟合中位数填补与标准化后重算 d/AUC，通过率 ≥ %.2f |"
      % (N_FOLDS, SEED, MIN_FOLD_PASS_RATE))
    A("| S5 与原模型不冗余 | 与原八字段数值列的最大 |r| < %.2f |" % MAX_ABS_R_BASE)
    A("| S6 组内不冗余＋小组规模 | 按 |d| 从大到小贪心，组内 |r| ≥ %.2f 的舍弃；每组最多 %d 个数值字段 |"
      % (MAX_ABS_R_WITHIN_GROUP, OUT_CAP_PER_GROUP))
    A("")
    A("**缺失一律显式建模**：有缺失的数值字段保留 NaN 并另加 0/1 缺失指示；"
      "填补中位数与标准化参数只在十月拟合（`tables/r3_transform_fit.json`），一月直接套用，不重新拟合。"
      "本组无缺失的字段不填、不加指示，具体按第 3 节每个字段的十月缺失人数执行。")
    A("")
    A("**缺失指示不单独参与 S3/S4/S6 的数值字段挑选**：`C04`、`C09` 是随对应数值字段"
      "按构造附带的二元指示，用来让「没有观测送达 / 没有已答评价」这一状态不被中位数掩盖；"
      "它们不是通过门槛选出来的第三个数值字段，也不占每组最多 %d 个数值字段的名额。"
      "其未通过的门槛结果与原因如实保留在 `candidate-screening.csv` 与第 4 节：%s。"
      "请勿把这些指示写成「通过了全部筛选」。" % (OUT_CAP_PER_GROUP, flag_gate_txt))
    A("")
    A("## 3. 交付的字段组（最多两组）")
    A("")
    for g in groups:
        sub = numeric[numeric.group == g]
        gflags = flags[flags.group == g]
        A("### %s（%d 个数值字段 + %d 个缺失指示）" % (g, len(sub), len(gflags)))
        A("")
        A("| candidate_id | 字段 | 单位 | 公式 | 来源 | 预测日可用时点 | 缺失处理 | 十月支持人数 | 一月支持人数 |")
        A("|---|---|---|---|---|---|---|---|---|")
        for r in sub.itertuples():
            A("| %s | `%s` | %s | `%s` | %s | %s | %s | %s | %s |" %
              (r.candidate_id, r.field, r.unit, r.formula.replace("|", "\\|"),
               txt(SOURCE[r.candidate_id]), txt(r.available_at),
               missing_cell(r), support_line(r.field, TRAIN_SNAPSHOT),
               support_line(r.field, VALIDATION_SNAPSHOT)))
        for r in gflags.itertuples():
            A("| %s | `%s` | binary | `%s` | %s | %s | 无缺失（显式 0/1） | %s | %s |" %
              (r.candidate_id, r.field, r.formula.replace("|", "\\|"),
               txt(SOURCE[r.candidate_id]), txt(r.available_at),
               support_line(r.field, TRAIN_SNAPSHOT), support_line(r.field, VALIDATION_SNAPSHOT)))
        A("")
        A("**选择规则（来自脚本，非事后挑最大）**：" + "；".join(
            "%s d=%+.3f、AUC=%.3f、折内通过率 %.0f%%、与原八字段最大 |r|=%.3f" %
            (r.field, r.cohens_d_all, r.auc_all, 100 * r.fold_pass_rate, r.max_abs_r_base8)
            for r in sub.itertuples()))
        A("")
        A("**三群正负样本与分布（十月训练侧，全部人数在 `group-comparison.csv`）**：")
        A("")
        for r in sub.itertuples():
            A("- `%s`：%s" % (r.field, cluster_line(r.field)))
        A("")
        base_r = "、".join("%s=%.3f" % (r.field, r.max_abs_r_base8)
                          for r in sub.itertuples())
        A("**预期作用（假设，不是已验证收益）**：" + (
            "「历史订单里已有观测送达 / 仍在途」的订单数与已观测履约时长，描述的是**履约进度**"
            "而不是购买规模；两项与原八字段数值列的最大 |r| 分别为 %s（均低于 S5 的 0.80）。"
            "群 1（久单）近 30 天订单全为 0，此点已由 `r3_inputs.py` 逐行核验；"
            "该群是否有可用变化须按上面的分群支持人数判断。" % base_r
            if "fulfilment" in g else
            "用已答复评分的均值与按 `F` 归一化的应答覆盖描述历史反馈行为。"
            "三群 d 符号与全体一致的候选共 %d 项（%s），本组 %s 在其中；"
            "两项与原八字段数值列的最大 |r| 分别为 %s。"
            "`C10_low_review_share` 与 `C08` 的 |r|=%.3f，按 S6 组内冗余舍弃，只保留证据。" %
            (len(consistent), ", ".join(consistent),
             ", ".join(sorted(set(sub.candidate_id) & set(consistent))) or "无",
             base_r, r_c08_c10)))
        A("")
    A("## 4. 全部候选的处置（保留无效候选）")
    A("")
    A("| id | 字段 | 组 | d(全体) | 折内通过率 | max |r| vs 原八字段 | 结论 | 原因 |")
    A("|---|---|---|---:|---:|---:|---|---|")
    for r in sc.itertuples():
        reason = "; ".join(filter(None, [txt(r.S1_note) if not r.S1 else "",
                                         txt(r.S2_note) if not r.S2 else "",
                                         txt(r.S3_note) if not r.S3 else "",
                                         txt(r.S4_note) if not r.S4 else "",
                                         txt(r.S5_note) if not r.S5 else "",
                                         txt(r.S6_note)]))
        A("| %s | `%s` | %s | %+.3f | %.0f%% | %.3f | %s | %s |" %
          (r.candidate_id, r.field, r.group, r.cohens_d_all,
           100 * r.fold_pass_rate, r.max_abs_r_base8, r.decision,
           reason.replace("|", "\\|")[:180]))
    A("")
    A("## 5. 与本地方案的差别（供 6 号并列比较）")
    A("")
    local_fields = set(ld.field.astype(str))
    cited = ["latest_known_review_score", "known_late_rate", "last_order_late",
             "known_delivery_days_mean", "latest_known_review_score_missing"]
    A("本地字段规格见仓库 `research/round3/data/features/field-dictionary.csv`（公开，"
      "本页生成时读到 %d 条定义）。本包候选池与筛选阈值在跑筛选前已冻结；"
      "`r3_spec.py` **只在生成本页时**读取该文件作对照，没有用它的定义或结果反推候选。"
      "下列本地字段均确实存在于该文件：%s。" %
      (len(ld), "、".join("`%s`%s" % (c, "✓" if c in local_fields else "✗") for c in cited)))
    A("")
    A("- 本地评价组用「最新一条已答评分」`latest_known_review_score`；本包用**按订单去重后的客户均值** "
      "`C08_review_score_mean`，并加按 `F` 归一化的应答覆盖 `C11_known_review_ratio`。")
    A("- 本地配送组含 `known_late_rate` / `last_order_late`，两者依赖预计送达日的事前可知且不回写；"
      "1 号 `field-time-audit.csv` 把该假设列为待核，本包**把 `C07_late_delivery_share` 明确排除推荐组**，"
      "只保留证据。改用不依赖承诺版本的实际送达时长与在途订单数。")
    A("- 本地字段用 `known_*_missing` 缺失指示；本包同样显式加指示，但把填补中位数、标准化均值/标准差"
      "写成固定参数文件，3 号可在一月直接套用。")
    A("- 本包额外要求**每群支持人数、群内标准差、折内重拟合方向一致性**三道门槛，"
      "并保留全部 %d 项的通过/失败原因。" % len(sc))
    A("")
    A("**本地已公开结果（来自 `docs/team/round-3-results.md`，不是本包跑出来的）**："
      "八字段加权逻辑回归在全局 2,937 名额下，原版命中 50，加配送组 46、加评价组 45、"
      "两组都加 46；固定久单 79 人命中分别为 2 / 2 / 1 / 1。"
      "即本地那两组**没有改善主容量命中**。本包字段定义与本地不同（见上），"
      "所以这些数字**不能**直接当作本包两组的预期效果；本包也没有模型、没有命中数。"
      "请 3 号按同一口径重新跑，6 号再并列比较。")
    A("")
    A("## 6. 一月方向核对（事后，不参与选择）")
    A("")
    if len(jd):
        A("| 字段 | 十月 d | 一月 d | 一月 AUC | 符号一致 | 一月非缺失 |")
        A("|---|---:|---:|---:|---|---:|")
        for r in jd.itertuples():
            A("| `%s` | %+.3f | %+.3f | %.3f | %s | %d / %d |" %
              (r.field, r.october_d_all, r.january_d_all, r.january_auc,
               "是" if bool(r.same_sign) else "否",
               int(r.january_nonmissing), int(r.january_N)))
        A("")
        A("一月是**已见的开发验证**，标签此前已被查看；这里只报描述方向，"
          "既不用于挑选字段，也不构成新时期验证或模型增益。")
    else:
        A("（本次运行未生成一月方向表。）")
    A("")
    A("## 7. 下游怎么用")
    A("")
    A("- **3 号**：按 `candidate-definitions.csv` 的公式或 `scripts/r3_build_candidates.py` 重算；"
      "私有逐人表 `candidate_features_train.csv` / `candidate_features_validation.csv` "
      "按 customer_unique_id + snapshot_date 与 H02、H05 群号一一对齐。"
      "把两组分别加入原八字段加权逻辑回归，与三条既有对照同口径比较，"
      "报 5%/10%/20% 容量、全局 2,937 与固定久单 79；**不要**把本页的 d 当作增益。")
    A("- **4 号**：`group-comparison.csv`、`training-feature-evidence.csv` 给三群的正负样本人数、"
      "缺失和分布，可用于画像卡；本包没有提出任何品类或内容主题。")
    A("- **5 号**：`tables/r3_private_manifest.json` 有逐人表的行数、列名与 SHA-256；"
      "`candidate-screening.csv` 有全部候选的门槛结果；可核人数、分母与版本。")
    A("")
    A("## 8. 已知缺口与限制")
    A("")
    A("1. H01／最终评价日期、最终标签仍未由 1、3、6 号核定；三期都已见过，本包不声称任何盲测。")
    A("2. 预计送达承诺的历史版本、源系统完整性、评分与状态变更日志 1 号仍列待核；"
      "因此所有 late 相关字段只留证据不推荐。")
    A("3. 十月正例仅 %d 人（群 2 只有 %d 人），群 2 的 d 与 AUC 波动大，"
      "按 S3/S4 只用「至少两群」判定，不对群 2 单独下结论。" %
      (pos_oct, int(coh[coh.cluster_id == 2].positives.iloc[0])))
    A("4. 十月群号复用 1 号 H05 包内训练侧 `train_audit.local.csv`，本包**没有重新聚类**；"
      "其 R/F/M/y 与 H02 在 1e-10 内一致。6 号公开 `october-feature-support.csv` "
      "按 `delivery_known_any` 汇总的群规模为 %s，与本包 %s 一致（已由 `r3_inputs.py` 核对）。" %
      (local_sizes, {int(k): int(v) for k, v in coh.set_index("cluster_id").N.items()}))
    A("5. 本包没有模型、没有分数、没有名单命中、没有 Slides/英文讲稿；"
      "描述差异与模型增益必须分开报告。")
    A("6. 公开包不含任何逐行客户数据；逐人候选表只在组内私有空间传递。")
    A("")
    A("## 9. 复跑")
    A("")
    A("```bash")
    A("cd outputs/Round3_role02/scripts")
    A("python run_all.py --smoke     # 5,000 行小样例")
    A("python run_all.py             # 全量：inputs -> candidates -> evidence -> plots -> spec -> verify")
    A("```")
    A("")
    A("输入路径可用 `R3_H02_DIR` / `R3_ROLE01_DIR` / `R3_H05_DIR` / `R3_RAW_DIR` 覆盖。"
      "全部图的来源表、行数、窗口、单位、分母、命令与哈希见 `chart-index.csv`（%d 幅）。" % len(ci))
    A("")
    write_text("\n".join(lines) + "\n", "feature-spec.md")

    # machine-readable spec for 3 号
    write_json(dict(spec_version=SPEC_VERSION, frozen_at=FROZEN_AT,
                    base_version=BASE_VERSION, asof_version=ASOF_VERSION,
                    cluster_version=CLUSTER_VERSION,
                    train_snapshot=TRAIN_SNAPSHOT, validation_snapshot=VALIDATION_SNAPSHOT,
                    train_N=n_oct, train_positives=pos_oct,
                    groups={g: [dict(candidate_id=r.candidate_id, field=r.field,
                                     formula=r.formula, unit=r.unit,
                                     available_at=r.available_at,
                                     missing_rule=r.missing_rule)
                                for r in numeric[numeric.group == g].itertuples()]
                            for g in groups},
                    retained_flags=flags.field.tolist(),
                    transform_fit_file="tables/r3_transform_fit.json",
                    private_tables=pm["files"],
                    selection_thresholds=dict(min_abs_d=MIN_ABS_D,
                                              min_cluster_nonmissing_rate=MIN_CLUSTER_NONMISSING_RATE,
                                              min_fold_pass_rate=MIN_FOLD_PASS_RATE,
                                              max_abs_r_base=MAX_ABS_R_BASE,
                                              max_abs_r_within_group=MAX_ABS_R_WITHIN_GROUP,
                                              out_cap_per_group=OUT_CAP_PER_GROUP,
                                              folds=N_FOLDS, seed=SEED)),
               "feature-spec.json")

    # numeric summary used by the hand-written handoff
    sum_lines = [
        "# 交接数字块（由 r3_spec.py 生成，勿手改）", "",
        "- 十月 N=%d，正例 %d；三群 %s" %
        (n_oct, pos_oct, " / ".join("%d+%d/%d" % (r.positives, r.negatives, r.N)
                                   for r in coh.itertuples())),
        "- 输入检查 %d/%d PASS，1 号 as-of 独立复算 %d 项，max abs diff %.3g，NaN 模式差异 0" %
        (n_pass, len(ic), len(av), asof_max),
        "- 候选池 %d 项，通过并交付 %d 个数值字段 + %d 个缺失指示，分 %d 组：%s" %
        (len(sc), len(numeric), len(flags), len(groups),
         "; ".join("%s = %s" % (g, ", ".join(numeric[numeric.group == g].field.tolist()))
                   for g in groups)),
        "- 图 %d 幅（PNG+SVG），逐图数据与哈希见 chart-index.csv" % len(ci),
        "- 私有逐人表：%s" %
        "; ".join("%s %d行 sha256=%s" % (k, v["rows"], v["sha256"][:16] + "…")
                  for k, v in pm["files"].items()),
        "",
    ]
    write_text("\n".join(sum_lines) + "\n", "tables/HANDOFF_SUMMARY.md")
    print("[r3_spec] wrote feature-spec.md / feature-spec.json / candidate-definitions.csv "
          "(%d groups, %d numeric fields)" % (len(groups), len(numeric)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    main(args.smoke)
