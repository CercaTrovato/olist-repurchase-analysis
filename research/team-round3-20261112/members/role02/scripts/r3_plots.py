"""Round-3 role-02 figures: PNG + editable SVG, each with aggregate chart data.

Figure text is English by default for slide reuse.  Every figure caption states
the window, unit, sample N, denominator, input version and the run command.
"""
from __future__ import annotations

import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from r3_common import (ASOF_VERSION, BASE_VERSION, CLUSTER_VERSION, SPEC_VERSION,
                       TRAIN_SNAPSHOT, VALIDATION_SNAPSHOT, KEY, out, sha256,
                       write_csv)

BLUE, ORANGE, GREY, GREEN, RED = "#2F6DB3", "#E1832B", "#8A8A8A", "#2E8B57", "#B23B3B"
CLABEL = {0: "C0 recent single-order", 1: "C1 old single-order", 2: "C2 multi-order"}


def tbl(name, smoke):
    p = out(smoke) / name
    try:
        return pd.read_csv(p)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def caption(fig, n, denominator, unit, window, note=""):
    """Four short lines beat one very long line that runs off the canvas."""
    fig.text(0.01, 0.080, "window %s | unit %s" % (window, unit),
             fontsize=6.9, color="#444444", ha="left", va="bottom")
    fig.text(0.01, 0.056, "N %s | denominator %s" % (n, denominator),
             fontsize=6.9, color="#444444", ha="left", va="bottom")
    fig.text(0.01, 0.032,
             "inputs %s / %s / %s%s" %
             (BASE_VERSION, ASOF_VERSION, CLUSTER_VERSION,
              " | " + note if note else ""),
             fontsize=6.7, color="#444444", ha="left", va="bottom")
    fig.text(0.99, 0.008, "role-02 round-3 | %s" % SPEC_VERSION, fontsize=6.9,
             color="#444444", ha="right", va="bottom")


def finish(fig, stem, smoke, title, source_tables, source_rows, unit, n,
           denominator, window, note="", bottom=0.16, left=0.10):
    caption(fig, n, denominator, unit, window, note)
    fig.subplots_adjust(bottom=bottom, top=0.90, left=left, right=0.97)
    fs = out(smoke) / "figures"
    fs.mkdir(parents=True, exist_ok=True)
    png, svg = fs / (stem + ".png"), fs / (stem + ".svg")
    fig.savefig(png, dpi=160, facecolor="white")
    fig.savefig(svg, facecolor="white")
    plt.close(fig)
    return dict(figure=stem, title=title,
                png="figures/" + png.name, svg="figures/" + svg.name,
                png_sha256=sha256(png), svg_sha256=sha256(svg),
                source_tables=";".join(source_tables),
                source_rows=";".join(str(r) for r in source_rows),
                window=window, unit=unit, sample_n=str(n),
                denominator=denominator,
                command="python r3_plots.py" + (" --smoke" if smoke else ""),
                data_version=BASE_VERSION, feature_version=ASOF_VERSION,
                cluster_version=CLUSTER_VERSION, spec_version=SPEC_VERSION, note=note)


def main(smoke: bool):
    gc = tbl("group-comparison.csv", smoke)
    ev = tbl("training-feature-evidence.csv", smoke)
    sc = tbl("candidate-screening.csv", smoke)
    fd = tbl("tables/r3_fold_selection.csv", smoke)
    sup = tbl("tables/r3_candidate_support.csv", smoke)
    jd = tbl("tables/r3_january_direction.csv", smoke)
    bins = tbl("tables/r3_distribution_bins.csv", smoke)
    cd = out(smoke) / "chart-data"
    cd.mkdir(parents=True, exist_ok=True)
    idx = []
    W = "history [2017-04-01,2017-10-01) / label [2017-10-01,2017-12-30)"
    WJ = "history [2017-07-01,2018-01-01) / label [2018-01-01,2018-04-01)"

    # --- 01 groups ---------------------------------------------------------
    coh = gc[gc.field == "(cohort)"].copy()
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.4))
    xs = np.arange(len(coh))
    ax[0].bar(xs, coh.N, color=BLUE, width=.6)
    for i, r in enumerate(coh.itertuples()):
        ax[0].text(i, r.N, "%d\n(%.2f%%)" % (r.N, 100 * r.N / coh.N.sum()),
                   ha="center", va="bottom", fontsize=9)
    ax[0].set_xticks(xs)
    ax[0].set_xticklabels(["C0", "C1", "C2"])
    ax[0].set_ylabel("customers"); ax[0].set_ylim(0, coh.N.max() * 1.25)
    ax[0].set_title("October training cohort size (N=21,160)" if not smoke
                    else "October SMOKE subset")
    ax[1].bar(xs, coh.positives, color=ORANGE, width=.6)
    for i, r in enumerate(coh.itertuples()):
        ax[1].text(i, r.positives + coh.positives.max() * 0.05,
                   "%d positives\n%.3f%%  [%d/%d]" % (r.positives, 100 * r.positive_rate,
                                                      r.positives, r.N),
                   ha="center", va="bottom", fontsize=8, linespacing=1.3)
    ax[1].set_xticks(xs); ax[1].set_xticklabels(["C0", "C1", "C2"])
    ax[1].set_ylabel("repurchasers"); ax[1].set_ylim(0, coh.positives.max() * 1.9)
    # Fixed coarse ticks keep the C0 value label clear of the axis numbers.
    top = coh.positives.max() * 1.9
    ax[1].set_yticks(np.arange(0, top + 1, 50))
    ax[1].set_title("Repurchasers by cluster (211 here; 740 over 3 periods)")
    # No suptitle: the two axes titles would collide with it.  Version context
    # is carried by the caption and by chart-index.csv instead.
    c01 = coh[["cluster_id", "N", "positives", "negatives", "positive_rate",
               "wilson_lo", "wilson_hi"]].copy()
    c01.to_csv(cd / "01-groups.csv", index=False)
    idx.append(finish(fig, "01-october-groups", smoke,
                      "October training cohort by H05 cluster",
                      ["group-comparison.csv"], [len(coh)], "customers / rate",
                      int(coh.N.sum()), "all October snapshot customers", W))

    # --- 02 effect sizes ---------------------------------------------------
    o = ev[ev.scope == "ALL"].merge(
        sc[["candidate_id", "field", "group", "retained", "decision", "abs_d"]],
        on=["candidate_id", "field", "group"], how="left").sort_values("cohens_d")
    fig, ax = plt.subplots(figsize=(10.5, 6.4))
    yy = np.arange(len(o))
    cols = [GREEN if bool(r.retained) else (GREY if "rejected" in str(r.decision) else BLUE)
            for r in o.itertuples()]
    ax.errorbar(o.cohens_d, yy, xerr=[o.cohens_d - o.d_ci_lo, o.d_ci_hi - o.cohens_d],
                fmt="none", ecolor="#BBBBBB", elinewidth=1, capsize=2)
    ax.scatter(o.cohens_d, yy, c=cols, s=42, zorder=3)
    for k, marker, lab in [(0, "o", "C0 d"), (1, "s", "C1 d"), (2, "^", "C2 d")]:
        sub = ev[ev.scope == str(k)].set_index("candidate_id")
        ax.scatter(sub.loc[o.candidate_id, "cohens_d"].to_numpy(), yy,
                   marker=marker, s=20, facecolors="none", edgecolors="#777777",
                   linewidths=.8, label=lab, zorder=2)
    ax.axvline(0, color="#333333", linewidth=.8)
    ax.set_yticks(yy)
    ax.set_yticklabels(["%s %s" % (r.candidate_id, r.field) for r in o.itertuples()], fontsize=8)
    ax.set_xlabel("Cohen's d, repurchasers minus non-repurchasers (95% CI)")
    ax.legend(loc="lower right", fontsize=8, ncol=3, frameon=False)
    ax.set_title("All 14 frozen candidates: October descriptive separation")
    o[["candidate_id", "field", "group", "cohens_d", "d_ci_lo", "d_ci_hi",
       "auc", "nonmissing", "missing_rate", "retained", "decision"]].to_csv(
        cd / "02-effects.csv", index=False)
    idx.append(finish(fig, "02-candidate-effect-sizes", smoke,
                      "Descriptive effect sizes of all frozen candidates",
                      ["training-feature-evidence.csv", "candidate-screening.csv"],
                      [len(ev), len(sc)], "standardized mean difference",
                      "%d (%d October customers, %d candidates)" %
                      (len(o), int(coh.N.sum()), len(o)),
                      "October non-missing customers for each candidate", W,
                      note="green=retained; gray markers=per-cluster d; descriptive only, not model gain",
                      bottom=0.18, left=0.24))

    # --- 03 / 04 distributions --------------------------------------------
    for stem, grp, title in [
        ("03-fulfilment-distribution", "G1_fulfilment", "Fulfilment group"),
        ("04-review-distribution", "G2_review", "Review group")]:
        ret = sc[(sc.group == grp) & (sc.retained) & (~sc.is_missing_flag)]
        fields = ret.field.tolist()[:2]
        if not fields or bins.empty:
            fields = fields or []
        fig, axes = plt.subplots(len(fields) or 1, 3,
                                 figsize=(12, 2.9 * max(1, len(fields))), squeeze=False)
        for i, fld in enumerate(fields):
            for k in [0, 1, 2]:
                ax = axes[i][k]
                for lab, col in [(1, ORANGE), (0, BLUE)]:
                    s = bins[(bins.field == fld) & (bins.cluster_id == k) & (bins.y == lab)]
                    if s.empty:
                        continue
                    ax.plot(s.bin_lo, s.share_within_group, marker="o", ms=3,
                            color=col, linewidth=1.4,
                            label=("repurchasers" if lab == 1 else "non-repurchasers"))
                    ax.fill_between(s.bin_lo, 0, s.share_within_group, color=col, alpha=.10)
                ax.set_title("%s | %s" % (CLABEL[k], fld), fontsize=8.5)
                ax.tick_params(labelsize=7)
                ax.set_ylabel("share within y group" if k == 0 else "")
                ax.set_xlabel("field value" if i == len(fields) - 1 else "", fontsize=7)
                ax.grid(alpha=.2)
                if i == 0 and k == 2:
                    ax.legend(fontsize=7, frameon=False)
        for i in range(len(fields), axes.shape[0]):
            for k in range(3):
                axes[i][k].axis("off")
        fig.suptitle("Round-3 role-02 | %s: October distributions by cluster and outcome"
                     % title, fontsize=11)
        sub = bins[bins.field.isin(fields)][
            ["candidate_id", "field", "group", "cluster_id", "y", "bin", "bin_lo",
             "bin_hi", "count", "group_total", "share_within_group"]]
        sub.to_csv(cd / (stem[:2] + "-distributions.csv"), index=False)
        # N = customers whose values were binned, summed over the plotted fields.
        # Do NOT sum group_total over bin rows: that repeats each customer 10x.
        n_obs = 0
        for fld in fields:
            q = sup[(sup.field == fld) & (sup.snapshot_date == TRAIN_SNAPSHOT)]
            if len(q):
                n_obs += int(q.nonmissing.iloc[0])
        idx.append(finish(fig, stem, smoke,
                          "%s: October distribution comparison" % title,
                          ["tables/r3_distribution_bins.csv", "candidate-screening.csv",
                           "tables/r3_candidate_support.csv"],
                          [len(bins), len(sc), len(sup)],
                          "within-group density (1st-99th pct, 10 bins)",
                          "%d (Oct non-missing, summed over %d fields)" % (n_obs, len(fields)),
                          "October non-missing customers per field, split by cluster and y=1/y=0", W,
                          note="aggregate bin counts only; no row-level data", bottom=0.17))

    # --- 05 support / missing ---------------------------------------------
    s = sup.copy()
    fig, ax = plt.subplots(figsize=(11, 4.8))
    piv = s.pivot_table(index="field", columns="snapshot_date", values="nonmissing",
                        aggfunc="sum").fillna(0)
    piv = piv.reindex(sc.field.tolist())
    xx = np.arange(len(piv))
    w = .38 if piv.shape[1] > 1 else .6
    for j, col in enumerate(piv.columns):
        ax.bar(xx + (j - (piv.shape[1] - 1) / 2) * w, piv[col], width=w,
               color=[BLUE, ORANGE][j % 2], label="non-missing " + col)
    ax.set_xticks(xx)
    ax.set_xticklabels(piv.index, rotation=40, ha="right", fontsize=7.2)
    ax.set_ylabel("customers with a computed value")
    ax.legend(fontsize=8, frameon=False)
    ax.grid(axis="y", alpha=.25)
    ax.set_title("Support counts (N with a value) by candidate and snapshot")
    s.to_csv(cd / "05-support.csv", index=False)
    idx.append(finish(fig, "05-support-and-missing", smoke,
                      "Candidate support counts by snapshot",
                      ["tables/r3_candidate_support.csv"], [len(s)], "customers",
                      "21,160 Oct / 29,368 Jan (%d support counts)" % len(s),
                      "all snapshot customers; one bar per candidate x snapshot "
                      "(missing kept in denominator)",
                      W + " ; " + WJ, bottom=0.38,
                      note="a NaN is a known-event absence, not a dropped customer"))

    # --- 06 fold selection -------------------------------------------------
    fr = fd.groupby(["candidate_id", "field"]).pass_fold.mean().reset_index()
    fr = fr.set_index("candidate_id").reindex(sc.candidate_id).reset_index()
    fr["field"] = fr.field.fillna(fr.candidate_id.map(sc.set_index("candidate_id").field))
    fig, ax = plt.subplots(figsize=(10.5, 4.4))
    ax.bar(np.arange(len(fr)), fr.pass_fold, color=[GREEN if v >= .8 else GREY
                                                    for v in fr.pass_fold.fillna(0)])
    ax.axhline(.8, color=RED, linestyle="--", linewidth=1, label="required 0.80")
    ax.set_xticks(np.arange(len(fr)))
    ax.set_xticklabels(fr.candidate_id, fontsize=8)
    ax.set_ylim(0, 1.08); ax.set_ylabel("fraction of 5 folds passing")
    ax.legend(fontsize=8, frameon=False); ax.grid(axis="y", alpha=.25)
    ax.set_title("Training-side fold re-fitted selection stability (seed 2026)")
    fr.to_csv(cd / "06-fold-selection.csv", index=False)
    idx.append(finish(fig, "06-fold-selection", smoke,
                      "Fold-wise candidate selection stability",
                      ["tables/r3_fold_selection.csv"], [len(fd)], "pass rate over 5 folds",
                      "21,160 October customers (%d fold x candidate rows)" % len(fd),
                      "October training customers; each fold refits on its own 4/5 part", W,
                      note="each fold refits median imputation and scaling on its own training part"))

    # --- 07 October vs January --------------------------------------------
    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    if len(jd):
        xx = np.arange(len(jd)); w = .36
        ax.bar(xx - w / 2, jd.october_d_all, width=w, color=BLUE, label="October (selection)")
        ax.bar(xx + w / 2, jd.january_d_all, width=w, color=ORANGE,
               label="January (post-hoc descriptive)")
        ax.set_xticks(xx); ax.set_xticklabels(jd.field, rotation=20, ha="right", fontsize=8)
        ax.axhline(0, color="#333333", linewidth=.8)
        ax.set_ylabel("Cohen's d")
        ax.legend(fontsize=8, frameon=False); ax.grid(axis="y", alpha=.25)
        ax.set_title("Retained fields: October vs already-seen January direction")
        jd.to_csv(cd / "07-direction.csv", index=False)
        note = "January labels NOT used for selection; already-seen development validation"
    else:
        ax.text(.5, .5, "January direction check: not computed in smoke mode",
                ha="center", va="center", transform=ax.transAxes)
        ax.set_title("Retained fields: October vs January direction")
        pd.DataFrame(columns=["candidate_id", "field"]).to_csv(cd / "07-direction.csv", index=False)
        note = "smoke run only"
    idx.append(finish(fig, "07-october-january-direction", smoke,
                      "October training vs January descriptive direction",
                      ["tables/r3_january_direction.csv"], [len(jd)],
                      "standardized mean difference",
                      "21,160 Oct / 29,368 Jan (%d retained fields)" % len(jd),
                      "all customers in each snapshot, per retained field",
                      W + " ; " + WJ, note=note, bottom=0.32))

    # --- 08 prediction-day availability -----------------------------------
    av = pd.DataFrame([
        ["history window start", "2017-04-01", "included", "eligible purchase / approval"],
        ["order approval", "< 2017-10-01", "available", "H02 eligibility; F, M, R"],
        ["actual delivery", "< 2017-10-01", "available", "G1 fulfilment fields"],
        ["review answer", "< 2017-10-01", "available", "G2 review fields"],
        ["snapshot t", "2017-10-01", "cut", "prediction day; cut strictly before t"],
        ["label window start", "2017-10-01", "excluded", "future repurchase y"],
        ["label window end", "2017-12-30", "excluded", "90-day target, right-open"],
        ["final order_status", "n/a", "excluded", "no state snapshot / change log"],
        ["estimated delivery date", "may be > t", "conditional", "promise-date assumption unverified"],
        ["delivery / answer at or after t", ">= 2017-10-01", "excluded", "future information"],
    ], columns=["event", "date_or_rule", "status", "used_for"])
    fig, ax = plt.subplots(figsize=(11, 4.6))
    ypos = np.arange(len(av))[::-1]
    cmap = {"available": GREEN, "included": BLUE, "cut": RED, "excluded": GREY,
            "conditional": ORANGE}
    ax.scatter([1] * len(av), ypos, s=90, c=[cmap[s] for s in av.status], zorder=3)
    for y, r in zip(ypos, av.itertuples()):
        ax.text(1.06, y, "%s  |  %s  |  %s" % (r.event, r.date_or_rule, r.used_for),
                va="center", fontsize=8.2)
    ax.axvline(1, color="#CCCCCC", linewidth=1)
    ax.set_xlim(.7, 2.9); ax.set_ylim(-.6, len(av) - .4)
    ax.set_yticks([]); ax.set_xticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("Prediction-day availability: what role-02 allows into the two field groups")
    av.to_csv(cd / "08-availability.csv", index=False)
    idx.append(finish(fig, "08-prediction-day-availability", smoke,
                      "Prediction-day availability of proposed fields",
                      ["field-time-audit.csv (role-01)", "time-window-audit.csv (role-01)"],
                      [len(av)], "event / rule", "88,341 snapshot rows",
                      "all three H02 snapshots (October shown)", W,
                      note="green=usable, orange=unverified assumption, grey/red=excluded",
                      bottom=0.14))

    write_csv(pd.DataFrame(idx), "chart-index.csv", smoke)
    print("[r3_plots] smoke=%s figures=%d -> %s" % (smoke, len(idx), out(smoke) / "chart-index.csv"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    main(args.smoke)
