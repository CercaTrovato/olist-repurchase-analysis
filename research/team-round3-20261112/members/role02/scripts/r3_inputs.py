"""Verify round-3 inputs, versions, keys, and independently recompute 1 号 as-of fields.

The recomputation is written from field-time-audit.csv definitions and the raw CSVs,
not by importing 1 号 build_audit.py.  It is the evidence that every proposed field
uses only events strictly before the prediction day.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys

import numpy as np
import pandas as pd

from r3_common import (ASOF_FIELDS, ASOF_VERSION, BASE_VERSION, CLUSTER_VERSION,
                       EXPECTED, EXPECTED_RAW, H02_DIR, H05_DIR, KEY, RAW, REPO_ROOT,
                       ROLE01_DIR, TRAIN_SNAPSHOT, VALIDATION_SNAPSHOT, WECHAT_DIR,
                       read_inputs, sha256, write_csv, write_json)

CHECKS = []


def check(name, ok, expected, observed, note=""):
    CHECKS.append(dict(check=name, status="PASS" if ok else "FAIL",
                       expected=str(expected), observed=str(observed), note=note))


def recompute_asof(snapshot: str) -> pd.DataFrame:
    """Independent implementation of 1 号 field-time-audit.csv for one snapshot."""
    orders = pd.read_csv(
        RAW / "olist_orders_dataset.csv",
        parse_dates=["order_purchase_timestamp", "order_approved_at",
                     "order_delivered_customer_date", "order_estimated_delivery_date"])
    customers = pd.read_csv(RAW / "olist_customers_dataset.csv",
                            usecols=["customer_id", "customer_unique_id"])
    items = pd.read_csv(RAW / "olist_order_items_dataset.csv",
                        usecols=["order_id", "order_item_id", "price"])
    reviews = pd.read_csv(
        RAW / "olist_order_reviews_dataset.csv",
        usecols=["order_id", "review_id", "review_score", "review_creation_date",
                 "review_answer_timestamp"],
        parse_dates=["review_creation_date", "review_answer_timestamp"])

    # item grain -> order grain, then order -> customer; never join item rows directly
    amount = items.groupby("order_id", sort=False)["price"].sum(min_count=1).rename("amount").reset_index()
    fact = orders.merge(amount, on="order_id", how="left", validate="one_to_one")
    fact = fact.merge(customers[["customer_id", "customer_unique_id"]],
                      on="customer_id", how="left", validate="one_to_one")
    qualified = fact.loc[fact.order_approved_at.notna() & fact.amount.gt(0)].copy()
    snap = pd.Timestamp(snapshot)
    history = qualified.loc[(qualified.order_approved_at >= snap - pd.DateOffset(months=6))
                            & (qualified.order_approved_at < snap)].copy()

    # reviews: exact de-dup, validate answer sequence, cut off BEFORE taking latest per order
    cand = reviews.loc[reviews.order_id.isin(history.order_id)].drop_duplicates().merge(
        history[["order_id", "order_purchase_timestamp"]], on="order_id",
        how="left", validate="many_to_one")
    answered, created = cand.review_answer_timestamp, cand.review_creation_date
    valid = (answered.notna()
             & answered.ge(cand.order_purchase_timestamp)
             & (created.isna() | answered.ge(created))
             & cand.review_score.isin([1, 2, 3, 4, 5]))
    eligible = cand.loc[valid & answered.lt(snap)].copy()
    latest = (eligible.sort_values(
        ["review_answer_timestamp", "review_creation_date", "review_id", "review_score"],
        na_position="first").drop_duplicates("order_id", keep="last"))
    o = history.merge(latest[["order_id", "review_score"]], on="order_id",
                      how="left", validate="one_to_one")

    actual, approved, purchased = (o.order_delivered_customer_date,
                                   o.order_approved_at, o.order_purchase_timestamp)
    promised = o.order_estimated_delivery_date
    coherent = actual.notna() & actual.ge(approved) & actual.ge(purchased)
    delivered = coherent & actual.lt(snap)
    comparable = delivered & promised.notna() & promised.dt.normalize().ge(purchased.dt.normalize())
    o["delivery_days"] = ((actual - approved).dt.total_seconds() / 86400).where(delivered)
    o["late"] = actual.dt.normalize().gt(promised.dt.normalize()).astype(float).where(comparable)
    o["low_score"] = o.review_score.le(2).astype(float).where(o.review_score.notna())

    summary = o.groupby("customer_unique_id").agg(
        delivered_known_n=("delivery_days", "count"),
        delivery_days_mean=("delivery_days", "mean"),
        delivery_promise_known_n=("late", "count"),
        late_delivery_share=("late", "mean"),
        review_known_n=("review_score", "count"),
        review_score_mean=("review_score", "mean"),
        low_review_share=("low_score", "mean"),
    ).reset_index()
    summary["snapshot_date"] = snapshot
    # Every source event used above is strictly before the prediction day.
    assert bool(actual.loc[delivered].lt(snap).all())
    assert bool(eligible.review_answer_timestamp.lt(snap).all())
    assert bool(latest.review_answer_timestamp.lt(snap).all())
    return summary


def main(smoke: bool):
    f, l, a, t, v = read_inputs(smoke)
    src = {}
    src["H02_dir"] = str(H02_DIR)
    src["role01_dir"] = str(ROLE01_DIR)

    # --- file hashes ------------------------------------------------------
    for name, exp in EXPECTED.items():
        if name == "snapshot-asof-features.csv":
            p = ROLE01_DIR / name
        elif name == "validation_clusters.csv":
            p = H05_DIR / name
        elif name.endswith(".zip"):
            p = WECHAT_DIR / name.replace("(1)", "")
        else:
            p = H02_DIR / name
        got = sha256(p) if p.exists() else "MISSING"
        check("hash:" + name, got == exp, exp[:16] + "...", got[:16] + "...", str(p))
    for name, exp in EXPECTED_RAW.items():
        got = sha256(RAW / name)
        check("hash:" + name, got == exp, exp[:16] + "...", got[:16] + "...")

    # --- 1 号 package internal checksums ---------------------------------
    lines = (ROLE01_DIR / "CHECKSUMS.sha256").read_text(encoding="utf-8-sig").splitlines()
    bad = []
    for line in lines:
        if not line.strip():
            continue
        h, n = line.split(None, 1)
        p = ROLE01_DIR / n.strip()
        if not p.exists() or sha256(p) != h:
            bad.append(n.strip())
    check("role01 CHECKSUMS.sha256", not bad, "0 mismatches", "%d mismatches" % len(bad),
          "CRLF-tolerant Python comparison" if not bad else ",".join(bad))

    # --- structure and keys ----------------------------------------------
    check("H02 feature rows", len(f) == (5000 if smoke else 88341), 5000 if smoke else 88341, len(f))
    check("asof rows", len(a) == len(f), len(f), len(a))
    check("H02 feature key unique", not f.duplicated(KEY).any(), "0 duplicates",
          int(f.duplicated(KEY).sum()))
    check("asof key unique", not a.duplicated(KEY).any(), "0 duplicates",
          int(a.duplicated(KEY).sum()))
    m = f[KEY].merge(a[KEY], on=KEY, how="outer", validate="one_to_one", indicator=True)
    check("feature/asof key alignment", bool((m._merge == "both").all()), "all both",
          m._merge.value_counts().to_dict())
    ml = f[KEY].merge(l[KEY], on=KEY, how="outer", validate="one_to_one", indicator=True)
    check("feature/label key alignment", bool((ml._merge == "both").all()), "all both",
          ml._merge.value_counts().to_dict())
    check("label domain", bool(l.y.isin([0, 1]).all()), "{0,1}",
          sorted(l.y.unique().tolist()))
    check("asof version", bool((a.feature_version == ASOF_VERSION).all()), ASOF_VERSION,
          sorted(a.feature_version.unique().tolist()))
    check("asof base version", bool((a.data_version == BASE_VERSION).all()), BASE_VERSION,
          sorted(a.data_version.unique().tolist()))

    # --- cluster labels ---------------------------------------------------
    oct_ = f[f.snapshot_date == TRAIN_SNAPSHOT]
    oct_join = oct_[KEY].merge(t[KEY + ["cluster_id"]], on=KEY, how="outer",
                               validate="one_to_one", indicator=True)
    check("October cluster labels cover all training customers",
          bool((oct_join._merge == "both").all()) and len(oct_join) == len(oct_),
          "%d keys" % len(oct_), "%d keys" % len(oct_join))
    check("October cluster domain", bool(t.cluster_id.isin([0, 1, 2]).all()), "{0,1,2}",
          sorted(t.cluster_id.unique().tolist()))
    # H05 train_audit R/F/M/y must agree with H02 exactly at 1e-10
    cmp = oct_[KEY + ["R", "F", "M"]].merge(
        l[KEY + ["y"]], on=KEY, validate="one_to_one").merge(
        t[KEY + ["R", "F", "M", "y"]], on=KEY, validate="one_to_one", suffixes=("_h02", "_h05"))
    diffs = {c: float(np.abs(cmp[c + "_h02"] - cmp[c + "_h05"]).max())
             for c in ["R", "F", "M", "y"]}
    check("train_audit R/F/M/y == H02 (<=1e-10)", all(x <= 1e-10 for x in diffs.values()),
          "<=1e-10", {k: round(v, 14) for k, v in diffs.items()})
    if not smoke:
        jan = f[f.snapshot_date == VALIDATION_SNAPSHOT]
        jj = jan[KEY].merge(v[KEY + ["cluster_id"]], on=KEY, how="outer",
                            validate="one_to_one", indicator=True)
        check("January cluster labels cover all validation customers",
              bool((jj._merge == "both").all()) and len(jj) == 29368,
              "29368 keys", "%d keys" % len(jj))
        check("January cluster counts",
              v.cluster_id.value_counts().sort_index().to_dict() == {0: 16335, 1: 12330, 2: 703},
              "{0:16335,1:12330,2:703}", v.cluster_id.value_counts().sort_index().to_dict())
        check("January cluster version", bool((v.cluster_version == CLUSTER_VERSION).all()),
              CLUSTER_VERSION, sorted(v.cluster_version.unique().tolist()))
        # Two claims used in feature-spec.md are checked here rather than asserted
        # in prose: (a) cluster-1 recent30_orders is structurally all zero,
        # (b) our October cluster sizes equal 6 号 public support table.
        oct_feat = f[f.snapshot_date == TRAIN_SNAPSHOT][KEY + ["recent30_orders"]]
        oct_cl = oct_feat.merge(t[KEY + ["cluster_id"]], on=KEY, how="left",
                                validate="one_to_one")
        c1 = oct_cl[oct_cl.cluster_id == 1].recent30_orders
        check("October cluster 1 recent30_orders all zero", bool((c1 == 0).all()),
              "all zero", "max=%s nonzero=%d" % (c1.max(), int((c1 != 0).sum())))
        sup = pd.read_csv(REPO_ROOT / "research" / "round3" / "data" / "features"
                          / "october-feature-support.csv")
        sizes = (sup[sup.feature == "delivery_known_any"]
                 .groupby("cluster_id").n.sum().sort_index().to_dict())
        expected_sizes = oct_cl.cluster_id.value_counts().sort_index().to_dict()
        check("October cluster sizes == public support table",
              sizes == expected_sizes, expected_sizes, sizes)

    # --- independent as-of recomputation ----------------------------------
    rows = []
    for snap in [TRAIN_SNAPSHOT, VALIDATION_SNAPSHOT]:
        ref = a[a.snapshot_date == snap]
        if smoke and ref.empty:
            continue  # smoke sample contains October keys only
        mine = recompute_asof(snap)
        if smoke:
            # The smoke sample is 5,000 October keys; compare that same subset
            # instead of the whole snapshot (same rule as H03 smoke checks).
            mine = f.loc[f.snapshot_date == snap, KEY].merge(
                mine, on=KEY, how="inner", validate="one_to_one")
        j = mine.merge(ref[KEY + ASOF_FIELDS], on=KEY, how="outer",
                       validate="one_to_one", indicator=True, suffixes=("_mine", "_ref"))
        check("asof key coverage %s" % snap, bool((j._merge == "both").all()), "all both",
              j._merge.value_counts().to_dict())
        for c in ASOF_FIELDS:
            x, y = j[c + "_mine"].to_numpy(float), j[c + "_ref"].to_numpy(float)
            both_nan = np.isnan(x) & np.isnan(y)
            diff = np.abs(x[~both_nan] - y[~both_nan])
            maxdiff = float(diff.max()) if diff.size else 0.0
            nan_mismatch = int((np.isnan(x) != np.isnan(y)).sum())
            rows.append(dict(snapshot_date=snap, field=c, compared_rows=len(j),
                             max_abs_diff=maxdiff, nan_pattern_mismatches=nan_mismatch,
                             status="PASS" if maxdiff <= 1e-9 and nan_mismatch == 0 else "FAIL"))
        check("asof recompute %s (7 fields)" % snap,
              all(r["status"] == "PASS" for r in rows if r["snapshot_date"] == snap),
              "7/7 PASS",
              "%d/7 PASS" % sum(r["status"] == "PASS" for r in rows if r["snapshot_date"] == snap),
              "independent implementation from raw CSVs; prediction-day truncation re-checked")
    write_csv(pd.DataFrame(rows), "tables/r3_asof_verification.csv", smoke)

    env = dict(python=platform.python_version(), pandas=pd.__version__,
               numpy=np.__version__, matplotlib=__import__("matplotlib").__version__,
               platform=platform.platform(), seed=2026, smoke=smoke,
               base_version=BASE_VERSION, asof_version=ASOF_VERSION,
               cluster_version=CLUSTER_VERSION, sources=src)
    write_json(env, "tables/r3_environment.json", smoke)
    df = pd.DataFrame(CHECKS)
    write_csv(df, "tables/r3_input_checks.csv", smoke)
    n_fail = int((df.status == "FAIL").sum())
    print("[r3_inputs] smoke=%s checks=%d PASS=%d FAIL=%d" %
          (smoke, len(df), len(df) - n_fail, n_fail))
    if n_fail:
        print(df[df.status == "FAIL"].to_string(index=False))
        sys.exit(1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    main(args.smoke)
