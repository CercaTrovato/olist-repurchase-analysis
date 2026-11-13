"""October training-side evidence, frozen candidate screening and January direction check.

SELECTION USES ONLY 2017-10-01 LABELS.  January labels are used once, afterwards,
for a descriptive direction check that is explicitly marked not used for selection.
No model is fitted, no scores and no list hits are produced here: descriptive
differences must not be reported as model gains.
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from r3_common import (BASE_NUMERIC, CANDIDATES, CANDIDATE_COL, KEY,
                       MAX_ABS_R_BASE, MAX_ABS_R_WITHIN_GROUP, MIN_ABS_D,
                       MIN_CLUSTER_NONMISSING_RATE, MIN_CLUSTER_POSITIVES_NONMISSING,
                       MIN_D_CLUSTERS, MIN_FOLD_PASS_RATE, MIN_POSITIVES_NONMISSING,
                       MIN_SIGN_CLUSTERS, N_FOLDS, OUT_CAP_PER_GROUP, SEED,
                       TRAIN_SNAPSHOT, VALIDATION_SNAPSHOT, auc, build_candidate_frame,
                       cohens_d, read_inputs, wilson, write_csv)

GROUPS = sorted({c[2] for c in CANDIDATES})
MISSING_FLAGS = {c[0] for c in CANDIDATES if c[1].endswith("_missing")}


def stratified_folds(y: np.ndarray, n_folds: int, seed: int):
    rng = np.random.default_rng(seed)
    folds = [[] for _ in range(n_folds)]
    for cls in (0, 1):
        idx = np.flatnonzero(y == cls)
        rng.shuffle(idx)
        for i, chunk in enumerate(np.array_split(idx, n_folds)):
            folds[i].extend(chunk.tolist())
    return [np.array(sorted(f)) for f in folds]


def d_se(d: float, n1: int, n0: int) -> float:
    if not np.isfinite(d) or n1 < 2 or n0 < 2:
        return float("nan")
    return float(np.sqrt((n1 + n0) / (n1 * n0) + d * d / (2 * (n1 + n0 - 2))))


def main(smoke: bool):
    f, l, a, t, v = read_inputs(smoke)
    # ---------------- October, training side ----------------
    fs, as_ = f[f.snapshot_date == TRAIN_SNAPSHOT], a[a.snapshot_date == TRAIN_SNAPSHOT]
    x = build_candidate_frame(fs, as_)
    x = x.merge(t[KEY + ["cluster_id"]], on=KEY, how="left", validate="one_to_one")
    x = x.merge(l[KEY + ["y"]], on=KEY, how="left", validate="one_to_one")
    assert x.cluster_id.notna().all() and x.y.notna().all()
    y = x.y.to_numpy(int)
    cl = x.cluster_id.to_numpy(int)

    # group comparison: positive / negative sample sizes, missing and distribution, by cluster
    group_rows = []
    for k in [0, 1, 2]:
        sub = x[cl == k]
        n, pos = len(sub), int(sub.y.sum())
        lo, hi = wilson(pos, n)
        group_rows.append(dict(cluster_id=k, y_group="all", N=n, positives=pos,
                               negatives=n - pos, positive_rate=pos / n if n else np.nan,
                               wilson_lo=lo, wilson_hi=hi, field="(cohort)",
                               nonmissing=n, missing=0, missing_rate=0.0, mean=np.nan,
                               median=np.nan, std=np.nan, p25=np.nan, p75=np.nan))
    for c in CANDIDATES:
        col = CANDIDATE_COL[c[0]]
        for k in [0, 1, 2]:
            for lab, sub in [("y=1", x[(cl == k) & (y == 1)]),
                             ("y=0", x[(cl == k) & (y == 0)])]:
                s = sub[col].astype(float)
                group_rows.append(dict(
                    cluster_id=k, y_group=lab, N=len(sub),
                    positives=int((sub.y == 1).sum()), negatives=int((sub.y == 0).sum()),
                    positive_rate=float(sub.y.mean()) if len(sub) else np.nan,
                    wilson_lo=np.nan, wilson_hi=np.nan, field=c[1],
                    nonmissing=int(s.notna().sum()), missing=int(s.isna().sum()),
                    missing_rate=float(s.isna().mean()), mean=float(s.mean()),
                    median=float(s.median()), std=float(s.std()),
                    p25=float(s.quantile(.25)), p75=float(s.quantile(.75))))
    write_csv(pd.DataFrame(group_rows), "group-comparison.csv", smoke)

    # ---------------- per-candidate evidence ----------------
    ev, screen = [], []
    for c in CANDIDATES:
        cid, name, grp = c[0], c[1], c[2]
        col = CANDIDATE_COL[cid]
        s_all = x[col].to_numpy(float)
        d_all = cohens_d(s_all, y)
        a_all = auc(s_all, y)
        for scope, mask in [("ALL", np.ones(len(x), bool))] + \
                           [(str(k), cl == k) for k in [0, 1, 2]]:
            s, yy = s_all[mask], y[mask]
            n1, n0 = int(yy.sum()), int((yy == 0).sum())
            d, a_ = cohens_d(s, yy), auc(s, yy)
            ok = np.isfinite(s)
            # v1.1: cohens_d() drops NaN rows, so the SE of d must use the SAME
            # non-missing positive/negative counts.  v1 used the full-group
            # n1/n0 here, which made the CI too narrow for the 5 candidates
            # that have missing values (20 of 56 evidence rows).
            pn = int((yy[ok] == 1).sum())
            qn = int((yy[ok] == 0).sum())
            se = d_se(d, pn, qn)
            ev.append(dict(candidate_id=cid, field=name, group=grp, scope=scope,
                           N=int(mask.sum()), positives=n1, negatives=n0,
                           positive_rate=float(yy.mean()),
                           nonmissing=int(ok.sum()), missing=int((~ok).sum()),
                           missing_rate=float((~ok).mean()),
                           positives_nonmissing=pn, negatives_nonmissing=qn,
                           mean_pos=float(np.nanmean(s[ok & (yy == 1)])) if (ok & (yy == 1)).any() else np.nan,
                           mean_neg=float(np.nanmean(s[ok & (yy == 0)])) if (ok & (yy == 0)).any() else np.nan,
                           median_pos=float(np.nanmedian(s[ok & (yy == 1)])) if (ok & (yy == 1)).any() else np.nan,
                           median_neg=float(np.nanmedian(s[ok & (yy == 0)])) if (ok & (yy == 0)).any() else np.nan,
                           cohens_d=d, d_se=se, d_ci_lo=d - 1.96 * se, d_ci_hi=d + 1.96 * se,
                           auc=a_, auc_minus_half=(a_ - 0.5) if np.isfinite(a_) else np.nan,
                           std=float(np.nanstd(s)), side="train_only"))

    ev_df = pd.DataFrame(ev)
    write_csv(ev_df, "training-feature-evidence.csv", smoke)

    # Aggregate distribution bins: only counts, never row-level values.
    bin_rows = []
    for c in CANDIDATES:
        col, name = CANDIDATE_COL[c[0]], c[1]
        vals = x[col].to_numpy(float)
        finite = vals[np.isfinite(vals)]
        if finite.size < 10:
            continue
        lo, hi = float(np.nanpercentile(finite, 1)), float(np.nanpercentile(finite, 99))
        if hi <= lo:
            hi = lo + 1.0
        edges = np.linspace(lo, hi, 11)
        for k in [0, 1, 2]:
            for lab in [0, 1]:
                s = vals[(cl == k) & (y == lab)]
                s = s[np.isfinite(s)]
                counts, _ = np.histogram(np.clip(s, lo, hi), bins=edges)
                total = int(counts.sum())
                for b, cnt in enumerate(counts):
                    bin_rows.append(dict(candidate_id=c[0], field=name, group=c[2],
                                         cluster_id=k, y=lab, bin=b + 1,
                                         bin_lo=float(edges[b]), bin_hi=float(edges[b + 1]),
                                         count=int(cnt), group_total=total,
                                         share_within_group=(float(cnt) / total) if total else 0.0))
    write_csv(pd.DataFrame(bin_rows), "tables/r3_distribution_bins.csv", smoke)

    # ---------------- fold-wise re-fitted selection ----------------
    folds = stratified_folds(y, N_FOLDS, SEED)
    fold_rows = []
    for c in CANDIDATES:
        cid, name, grp = c[0], c[1], c[2]
        col = CANDIDATE_COL[cid]
        s_all = x[col].to_numpy(float)
        d_all = cohens_d(s_all, y)
        for i, test_idx in enumerate(folds):
            tr_mask = np.ones(len(x), bool)
            tr_mask[test_idx] = False
            tr = s_all[tr_mask].copy()
            yy = y[tr_mask]
            med = np.nanmedian(tr)
            tr = np.where(np.isnan(tr), med, tr)
            mu, sd = tr.mean(), tr.std(ddof=0)
            if sd > 0:
                tr = (tr - mu) / sd
            d_tr, a_tr = cohens_d(tr, yy), auc(tr, yy)
            ok = (abs(d_tr) >= MIN_ABS_D and np.isfinite(a_tr)
                  and np.sign(a_tr - 0.5) == np.sign(d_all))
            fold_rows.append(dict(candidate_id=cid, field=name, group=grp, fold=i + 1,
                                  train_n=int(tr_mask.sum()),
                                  train_positives=int(yy.sum()),
                                  impute_median_train=float(med),
                                  standard_mean_train=float(mu),
                                  standard_std_train=float(sd),
                                  d_train=d_tr, auc_train=a_tr,
                                  overall_d=d_all, pass_fold=bool(ok),
                                  side="train_only"))
    fold_df = pd.DataFrame(fold_rows)
    write_csv(fold_df, "tables/r3_fold_selection.csv", smoke)

    # ---------------- correlation / added information ----------------
    corr_rows = []
    cols = {c[0]: CANDIDATE_COL[c[0]] for c in CANDIDATES}
    for i, ci in enumerate(CANDIDATES):
        for cj in CANDIDATES[i:]:
            r = float(x[cols[ci[0]]].corr(x[cols[cj[0]]]))
            corr_rows.append(dict(candidate_id=ci[0], field_a=ci[1], candidate_id_b=cj[0],
                                  field_b=cj[1], pearson_r=r))
        rs = [(b, float(abs(x[cols[ci[0]]].corr(x[b])))) for b in BASE_NUMERIC]
        mb, mr = max(rs, key=lambda z: (z[1] if np.isfinite(z[1]) else -1))
        corr_rows.append(dict(candidate_id=ci[0], field_a=ci[1],
                              candidate_id_b="BASE8", field_b=mb,
                              pearson_r=mr))
    write_csv(pd.DataFrame(corr_rows), "field-correlation.csv", smoke)

    # ---------------- screening gates ----------------
    corr_matrix = x[[cols[c[0]] for c in CANDIDATES]].corr()
    corr_matrix.index = [c[0] for c in CANDIDATES]
    corr_matrix.columns = [c[0] for c in CANDIDATES]
    base_max = {}
    for c in CANDIDATES:
        cid = c[0]
        base_max[cid] = max(abs(float(x[cols[cid]].corr(x[b]))) for b in BASE_NUMERIC)
    fold_rate = fold_df.groupby("candidate_id").pass_fold.mean().to_dict()

    rows = []
    for c in CANDIDATES:
        cid, name, grp = c[0], c[1], c[2]
        sub = ev_df[(ev_df.candidate_id == cid) & (ev_df.scope != "ALL")]
        overall = ev_df[(ev_df.candidate_id == cid) & (ev_df.scope == "ALL")].iloc[0]
        d_all = float(overall.cohens_d)
        rates = [float(r) for r in sub.missing_rate]
        nonmiss_rate_min = float(min(1 - r for r in rates))
        pos_nonmiss = int(overall.positives_nonmissing)
        pos_nonmiss_c01 = [int(sub[sub.scope == str(k)].positives_nonmissing.iloc[0]) for k in [0, 1]]
        n_big = int((sub.cohens_d.abs() >= MIN_ABS_D).sum())
        signs = np.sign(sub.cohens_d.dropna().to_numpy())
        n_sign = int((signs == np.sign(d_all)).sum()) if np.isfinite(d_all) else 0
        sd_c01 = [float(x[cols[cid]][cl == k].std()) for k in [0, 1]]
        gates = {
            "S1_availability": (not c[8],
                                "assumption-dependent: " + c[6] if c[8] else "prediction-day only"),
            "S2_support": (nonmiss_rate_min >= MIN_CLUSTER_NONMISSING_RATE
                           and pos_nonmiss >= MIN_POSITIVES_NONMISSING
                           and all(p >= MIN_CLUSTER_POSITIVES_NONMISSING for p in pos_nonmiss_c01),
                           "min cluster nonmissing=%.3f, pos_nonmissing=%d, c0/c1=%s"
                           % (nonmiss_rate_min, pos_nonmiss, pos_nonmiss_c01)),
            "S3_variation": (n_big >= MIN_D_CLUSTERS and all(v > 0 for v in sd_c01),
                             "clusters |d|>=%.2f: %d/3, sd(c0,c1)=%s"
                             % (MIN_ABS_D, n_big, [round(v, 4) for v in sd_c01])),
            "S4_direction_folds": (n_sign >= MIN_SIGN_CLUSTERS
                                   and fold_rate.get(cid, 0) >= MIN_FOLD_PASS_RATE,
                                   "sign match %d/3, fold pass %.2f"
                                   % (n_sign, fold_rate.get(cid, 0))),
            "S5_base_redundancy": (base_max[cid] < MAX_ABS_R_BASE,
                                   "max |r| vs original 8 = %.3f" % base_max[cid]),
        }
        rows.append(dict(candidate_id=cid, field=name, group=grp,
                         unit=c[3], formula=c[4], available_at=c[6],
                         missing_rule=c[7], assumption_dependent=bool(c[8]),
                         is_missing_flag=(cid in MISSING_FLAGS),
                         cohens_d_all=d_all, auc_all=float(overall.auc),
                         abs_d=abs(d_all), nonmissing=int(overall.nonmissing),
                         missing=int(overall.missing),
                         min_cluster_nonmissing_rate=nonmiss_rate_min,
                         positives_nonmissing=pos_nonmiss,
                         n_clusters_abs_d_ge_threshold=n_big,
                         n_clusters_sign_match=n_sign,
                         fold_pass_rate=float(fold_rate.get(cid, 0)),
                         max_abs_r_base8=float(base_max[cid]),
                         S1=gates["S1_availability"][0], S1_note=gates["S1_availability"][1],
                         S2=gates["S2_support"][0], S2_note=gates["S2_support"][1],
                         S3=gates["S3_variation"][0], S3_note=gates["S3_variation"][1],
                         S4=gates["S4_direction_folds"][0], S4_note=gates["S4_direction_folds"][1],
                         S5=gates["S5_base_redundancy"][0], S5_note=gates["S5_base_redundancy"][1]))
    sdf = pd.DataFrame(rows)

    # Greedy within-group de-duplication, keeping the strongest |d| first.
    sdf["S6_not_redundant_in_group"] = True
    sdf["S6_note"] = ""
    sdf["retained"] = False
    sdf["decision"] = "screened_out"
    for grp in GROUPS:
        pool = sdf[(sdf.group == grp) & (~sdf.is_missing_flag)
                   & sdf.S1 & sdf.S2 & sdf.S3 & sdf.S4 & sdf.S5] \
            .sort_values("abs_d", ascending=False)
        kept = []
        for idx, r in pool.iterrows():
            cid = r.candidate_id
            conflict = next((k for k in kept
                             if abs(float(corr_matrix.loc[cid, k])) >= MAX_ABS_R_WITHIN_GROUP), None)
            if conflict is not None:
                sdf.loc[idx, "S6_not_redundant_in_group"] = False
                sdf.loc[idx, "S6_note"] = "|r|=%.3f with %s already retained" % (
                    abs(float(corr_matrix.loc[cid, conflict])), conflict)
                sdf.loc[idx, "decision"] = "rejected_redundant"
            elif len(kept) >= OUT_CAP_PER_GROUP:
                sdf.loc[idx, "decision"] = "rejected_group_cap"
                sdf.loc[idx, "S6_note"] = "group already has %d numeric fields" % OUT_CAP_PER_GROUP
            else:
                kept.append(cid)
                sdf.loc[idx, "retained"] = True
                sdf.loc[idx, "decision"] = "retained"
                sdf.loc[idx, "S6_note"] = "retained as numeric field #%d in %s" % (len(kept), grp)
        for idx, r in sdf[(sdf.group == grp) & (~sdf.retained)].iterrows():
            if r.decision == "screened_out":
                failed = [g for g in ["S1", "S2", "S3", "S4", "S5"] if not r[g]]
                sdf.loc[idx, "decision"] = "rejected_" + "+".join(failed) if failed else "rejected"

    # Attach an explicit missing indicator wherever a retained field has NaNs.
    for idx, r in sdf[sdf.retained].iterrows():
        miss = x[CANDIDATE_COL[r.candidate_id]].isna()
        if not miss.any():
            continue
        for c in CANDIDATES:
            if c[0] in MISSING_FLAGS:
                flag = x[CANDIDATE_COL[c[0]]]
                if bool(((flag == 1) == miss).all()):
                    fi = sdf.index[sdf.candidate_id == c[0]][0]
                    sdf.loc[fi, "decision"] = "attached_missing_indicator"
                    sdf.loc[fi, "retained"] = True
                    sdf.loc[fi, "S6_note"] = "attached to %s" % r.candidate_id
                    break
    sdf = sdf.sort_values(["group", "candidate_id"])
    write_csv(sdf, "candidate-screening.csv", smoke)
    retained = sdf[sdf.retained].copy()
    write_csv(retained[["candidate_id", "field", "group", "unit", "formula",
                        "available_at", "missing_rule", "decision"]],
              "tables/r3_retained_fields.csv", smoke)

    # ---------------- January descriptive direction (NOT selection) ----------------
    jan_rows = []
    fjan, ajan = f[f.snapshot_date == VALIDATION_SNAPSHOT], a[a.snapshot_date == VALIDATION_SNAPSHOT]
    if len(fjan) and len(v):
        xj = build_candidate_frame(fjan, ajan)
        xj = xj.merge(v[KEY + ["cluster_id"]], on=KEY, how="left", validate="one_to_one")
        xj = xj.merge(l[KEY + ["y"]], on=KEY, how="left", validate="one_to_one")
        yj, clj = xj.y.to_numpy(int), xj.cluster_id.to_numpy(int)
        for _, r in retained.iterrows():
            col = CANDIDATE_COL[r.candidate_id]
            s = xj[col].to_numpy(float)
            oct_d = float(r.cohens_d_all)
            jan_rows.append(dict(candidate_id=r.candidate_id, field=r.field, group=r.group,
                                 october_d_all=oct_d, january_d_all=cohens_d(s, yj),
                                 january_auc=auc(s, yj),
                                 january_N=len(xj), january_positives=int(yj.sum()),
                                 january_nonmissing=int(np.isfinite(s).sum()),
                                 january_missing=int(np.isnan(s).sum()),
                                 january_d_c0=cohens_d(s[clj == 0], yj[clj == 0]),
                                 january_d_c1=cohens_d(s[clj == 1], yj[clj == 1]),
                                 january_d_c2=cohens_d(s[clj == 2], yj[clj == 2]),
                                 same_sign=bool(np.sign(cohens_d(s, yj)) == np.sign(oct_d)),
                                 used_for_selection=False,
                                 note="January is already-seen development validation; "
                                      "post-hoc descriptive check only."))
    JAN_COLS = ["candidate_id", "field", "group", "october_d_all", "january_d_all",
                "january_auc", "january_N", "january_positives", "january_nonmissing",
                "january_missing", "january_d_c0", "january_d_c1", "january_d_c2",
                "same_sign", "used_for_selection", "note"]
    write_csv(pd.DataFrame(jan_rows, columns=JAN_COLS),
              "tables/r3_january_direction.csv", smoke)

    n_ret = int(sdf.retained.sum())
    print("[r3_evidence] smoke=%s rows=%d candidates=%d retained=%d groups=%s" %
          (smoke, len(x), len(CANDIDATES), n_ret,
           sorted(retained.group.unique().tolist())))
    print(retained[["candidate_id", "field", "group", "decision"]].to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    main(args.smoke)
