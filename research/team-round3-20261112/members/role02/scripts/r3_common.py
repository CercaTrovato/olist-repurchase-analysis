"""Round-3 role-02 shared configuration and helpers.

Frozen on 2026-11-12 before the final screening run.  Every candidate formula,
selection threshold and input version is declared here so that 3 号 can reproduce
the same fields and 4/5 号 can check the same denominators.

No row-level customer data is written by anything in the public bundle.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# frozen definitions
# --------------------------------------------------------------------------
FROZEN_AT = "2026-11-12 21:35 +0800"
SPEC_VERSION = "R3-role02-feature-v1"
BASE_VERSION = "H02-v2-candidate-reviewed"
ASOF_VERSION = "round3-role01-time-v1"
CLUSTER_VERSION = "H05-km3-v1"
TRAIN_SNAPSHOT = "2017-10-01"
VALIDATION_SNAPSHOT = "2018-01-01"
KEY = ["customer_unique_id", "snapshot_date"]
SEED = 2026
N_FOLDS = 5
OUT_CAP_PER_GROUP = 2  # at most 2 numeric fields per delivered field group

# Selection thresholds (locked before the final screening run; training side only)
MIN_CLUSTER_NONMISSING_RATE = 0.80   # in each of the 3 clusters, all customers in denominator
MIN_POSITIVES_NONMISSING = 10        # overall, on training side
MIN_CLUSTER_POSITIVES_NONMISSING = 3  # in each of cluster 0 and 1
MIN_ABS_D = 0.08                      # standardized mean difference
MIN_D_CLUSTERS = 2                    # clusters with |d| >= MIN_ABS_D
MIN_SIGN_CLUSTERS = 2                 # clusters whose d sign matches the overall sign
MIN_FOLD_PASS_RATE = 0.80             # 5-fold, selection statistic re-fitted inside each fold
MAX_ABS_R_BASE = 0.80                 # vs any of the original 8 numeric model fields
MAX_ABS_R_WITHIN_GROUP = 0.80         # vs an already retained field in the same group

# Expected input hashes, taken from docs/team/round-3/input-versions.csv and
# 1 号 data-version.json / CHECKSUMS.sha256.
EXPECTED = {
    "snapshot_features.csv": "ce62dedacb5af0e08c419586ff55e45043de56771553620ef3f08100e12712b9",
    "snapshot_labels.csv": "5e75eae468449bb9810e8ac0b796bea588762dd6c3335f2923da91a46220888f",
    "coverage-and-cohorts.csv": "a1003f7847e194281307f6c9f7ceb9a8a5ada1673bbd9e361875f04fa815c242",
    "validation_clusters.csv": "509e6df79c758be73c693ea63a5e1ff9a33db97bcbc168d218b47dfe02d55f85",
    "snapshot-asof-features.csv": "549f0502199291466a42e674e2f9f746462de57953974ff06b5b66dc409b0628",
    "H02_candidate_v2.zip": "3b58f4e493e825a76ccc569f205cfa0db5d27e22b13389c3c00ff958a316419a",
    "H04_role03_prediction_v0.4.zip": "d22c2e9f8290f590dabf7e30c174ebd5209baa840eff1a13e775fbec30ded3b7",
    "H05_role04_2026-11-10(1).zip": "7fd04f2ed38f3537fe783fe1c7ad42cbdb8cd908aa3505f9ead847531541d9c3",
}
EXPECTED_RAW = {
    "olist_orders_dataset.csv": "8df58ef3d2d7e9944010f7beecd9b75367f5588ec6e3c91cec19ae3345ef9ecf",
    "olist_customers_dataset.csv": "983a422239e1712ded753b3bf9ecf47dc73f144d306029dcfa99e70a226883d2",
    "olist_order_items_dataset.csv": "0bc4d068c4fe38cbb01bd90e8746e3c613fe7b4baef75fab7b0e329701c3e279",
    "olist_order_reviews_dataset.csv": "012b61c7593e34f51fa614efdf802b9c7056ce6aae5307ddb93236e7cfc797d7",
}

# candidate_id, field, group, unit, formula, source_columns, available_at,
# missing_rule, assumption_dependent, note
CANDIDATES = [
    ("C01", "known_delivery_ratio", "G1_fulfilment", "fraction",
     "delivered_known_n / F",
     "asof.delivered_known_n + H02.F",
     "delivery timestamp strictly < snapshot",
     "no missing; F>=1 for every snapshot customer", False,
     "Share of historical eligible orders with a known delivery before the snapshot."),
    ("C02", "delivery_pending_n", "G1_fulfilment", "orders",
     "F - delivered_known_n",
     "asof.delivered_known_n + H02.F",
     "delivery timestamp strictly < snapshot",
     "no missing; F>=1 for every snapshot customer", False,
     "Count of eligible orders with no known delivery before the snapshot (in-flight / unobserved)."),
    ("C03", "delivery_days_log", "G1_fulfilment", "log(days)",
     "log1p(max(delivery_days_mean, 0))",
     "asof.delivery_days_mean",
     "actual delivery strictly < snapshot; duration from approval",
     "NaN when no known valid delivery; explicit missing indicator", False,
     "Mean approval-to-delivery time over known deliveries, log-compressed."),
    ("C04", "delivery_days_mean_missing", "G1_fulfilment", "binary",
     "1{delivery_days_mean is NaN}",
     "asof.delivery_days_mean",
     "derived from prediction-day truncation only",
     "no missing; explicit zero/one", False,
     "Missingness flag; keeps every customer in the denominator."),
    ("C05", "delivered_known_log", "G1_fulfilment", "log(orders)",
     "log1p(delivered_known_n)",
     "asof.delivered_known_n",
     "delivery timestamp strictly < snapshot",
     "no missing", False,
     "Raw count of known deliveries; expected to be an F proxy."),
    ("C06", "delivery_known_any", "G1_fulfilment", "binary",
     "1{delivered_known_n > 0}",
     "asof.delivered_known_n",
     "delivery timestamp strictly < snapshot",
     "no missing", False,
     "Binary version of C01 for single-order customers."),
    ("C07", "late_delivery_share", "G1_fulfilment", "fraction",
     "asof.late_delivery_share as delivered",
     "asof.late_delivery_share",
     "conditional: estimated delivery date assumed known at approval and never rewritten",
     "NaN when no comparable delivery", True,
     "1 号 flags the promise-date assumption as unverified; kept as evidence, not recommended."),
    ("C08", "review_score_mean", "G2_review", "stars 1-5",
     "asof.review_score_mean as delivered",
     "asof.review_score_mean",
     "review answer strictly < snapshot; per-order latest valid answer",
     "NaN when no known answered review; explicit missing indicator", False,
     "Per-customer mean of per-order latest known answered scores."),
    ("C09", "review_score_mean_missing", "G2_review", "binary",
     "1{review_score_mean is NaN}",
     "asof.review_score_mean",
     "derived from prediction-day truncation only",
     "no missing; explicit zero/one", False,
     "Missingness flag; keeps every customer in the denominator."),
    ("C10", "low_review_share", "G2_review", "fraction",
     "asof.low_review_share as delivered",
     "asof.low_review_share",
     "review answer strictly < snapshot",
     "NaN when no known answered review", False,
     "Share of known answered reviews with score <= 2."),
    ("C11", "known_review_ratio", "G2_review", "fraction",
     "review_known_n / F",
     "asof.review_known_n + H02.F",
     "review answer strictly < snapshot",
     "no missing; F>=1 for every snapshot customer", False,
     "Share of historical orders with a known answered review before the snapshot."),
    ("C12", "review_per_delivery", "G2_review", "fraction",
     "review_known_n / delivered_known_n",
     "asof.review_known_n + asof.delivered_known_n",
     "both events strictly < snapshot",
     "NaN when delivered_known_n = 0", False,
     "Review coverage conditional on a known delivery."),
    ("C13", "review_known_any", "G2_review", "binary",
     "1{review_known_n > 0}",
     "asof.review_known_n",
     "review answer strictly < snapshot",
     "no missing", False,
     "Binary version of C11 for single-order customers."),
    ("C14", "review_known_log", "G2_review", "log(orders)",
     "log1p(review_known_n)",
     "asof.review_known_n",
     "review answer strictly < snapshot",
     "no missing", False,
     "Raw count of known answered reviews; expected to be an F proxy."),
]
CANDIDATE_COLS = ["candidate_id", "field", "group", "unit", "formula",
                  "source_columns", "available_at", "missing_rule",
                  "assumption_dependent", "note"]
ASOF_FIELDS = ["delivered_known_n", "delivery_days_mean", "delivery_promise_known_n",
               "late_delivery_share", "review_known_n", "review_score_mean", "low_review_share"]
BASE_NUMERIC = ["R", "F_log", "M_log", "average_item_rows", "freight_share",
                "recent30_orders", "recent30_spend_log", "observed_history_days"]

# --------------------------------------------------------------------------
# paths
# --------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
BUNDLE = HERE.parent
REPO_ROOT = BUNDLE.parent.parent
WORKSPACE = REPO_ROOT.parent
RAW = Path(os.environ.get("R3_RAW_DIR", REPO_ROOT / "data" / "raw"))
PRIVATE_IN = Path(os.environ.get("R3_PRIVATE_IN", WORKSPACE / "private_inputs"))
PRIVATE_OUT = Path(os.environ.get("R3_PRIVATE_OUT", WORKSPACE / "private_outputs" / "Round3_role02"))

H02_CANDIDATES = [
    Path(os.environ["R3_H02_DIR"]) if os.environ.get("R3_H02_DIR") else None,
    REPO_ROOT / "outputs" / "H02_candidate_v2",
    WORKSPACE / "private_inputs" / "H02_candidate_v2",
    Path(r"MEMBER_HOME/xwechat_files/PRIVATE_WECHAT_ID/msg/file/2026-11/H02_candidate_v2"),
]
H02_DIR = next((p for p in H02_CANDIDATES if p and (p / "snapshot_features.csv").exists()), None)
ROLE01_DIR = Path(os.environ.get("R3_ROLE01_DIR", PRIVATE_IN / "Round3_role01_time_v1"))
H05_DIR = Path(os.environ.get("R3_H05_DIR", PRIVATE_IN / "H05_role04_2026-11-10" / "results"))
WECHAT_DIR = Path(r"MEMBER_HOME/xwechat_files/PRIVATE_WECHAT_ID/msg/file/2026-11")


def out(smoke: bool = False) -> Path:
    p = BUNDLE / "smoke" if smoke else BUNDLE
    p.mkdir(parents=True, exist_ok=True)
    return p


def private_out(smoke: bool = False) -> Path:
    p = PRIVATE_OUT / "smoke" if smoke else PRIVATE_OUT
    p.mkdir(parents=True, exist_ok=True)
    return p


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_csv(df: pd.DataFrame, name: str, smoke: bool = False) -> Path:
    p = out(smoke) / name
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, encoding="utf-8")
    return p


def write_text(text: str, name: str, smoke: bool = False) -> Path:
    p = out(smoke) / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")
    return p


def write_json(obj: dict, name: str, smoke: bool = False) -> Path:
    return write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", name, smoke)


def read_inputs(smoke: bool = False):
    """Return (features, labels, asof, train_clusters, validation_clusters)."""
    if H02_DIR is None:
        raise FileNotFoundError("H02 dir not found; set R3_H02_DIR")
    f = pd.read_csv(H02_DIR / "snapshot_features.csv", dtype={"customer_unique_id": str})
    l = pd.read_csv(H02_DIR / "snapshot_labels.csv", dtype={"customer_unique_id": str})
    a = pd.read_csv(ROLE01_DIR / "snapshot-asof-features.csv", dtype={"customer_unique_id": str})
    t = pd.read_csv(H05_DIR / "feedback_round1" / "local_data" / "train_audit.local.csv",
                    dtype={"customer_unique_id": str})
    v = pd.read_csv(H05_DIR / "validation_clusters.csv", dtype={"customer_unique_id": str})
    if smoke:
        keys = (f.loc[f.snapshot_date == TRAIN_SNAPSHOT, KEY]
                .sample(n=5000, random_state=SEED).reset_index(drop=True))
        f = keys.merge(f, on=KEY, how="inner", validate="one_to_one")
        l = keys.merge(l, on=KEY, how="inner", validate="one_to_one")
        a = keys.merge(a, on=KEY, how="inner", validate="one_to_one")
        t = keys.merge(t, on=KEY, how="inner", validate="one_to_one")
        v = v.iloc[0:0].copy()
    return f, l, a, t, v


def build_candidate_frame(features: pd.DataFrame, asof: pd.DataFrame) -> pd.DataFrame:
    """Pure function: H02 features + 1 号 as-of columns -> the 14 frozen candidates."""
    d = features[KEY + ["R", "F", "M", "average_item_rows", "freight_share",
                        "recent30_orders", "recent30_spend", "observed_history_days"]].merge(
        asof[KEY + ASOF_FIELDS], on=KEY, how="inner", validate="one_to_one")
    F = d["F"].astype(float)
    dk = d["delivered_known_n"].astype(float)
    rk = d["review_known_n"].astype(float)
    x = pd.DataFrame(index=d.index)
    x["C01_known_delivery_ratio"] = dk / F
    x["C02_delivery_pending_n"] = F - dk
    x["C03_delivery_days_log"] = np.log1p(d["delivery_days_mean"].clip(lower=0))
    x["C04_delivery_days_mean_missing"] = d["delivery_days_mean"].isna().astype(float)
    x["C05_delivered_known_log"] = np.log1p(dk)
    x["C06_delivery_known_any"] = (dk > 0).astype(float)
    x["C07_late_delivery_share"] = d["late_delivery_share"]
    x["C08_review_score_mean"] = d["review_score_mean"]
    x["C09_review_score_mean_missing"] = d["review_score_mean"].isna().astype(float)
    x["C10_low_review_share"] = d["low_review_share"]
    x["C11_known_review_ratio"] = rk / F
    x["C12_review_per_delivery"] = rk / dk.replace(0, np.nan)
    x["C13_review_known_any"] = (rk > 0).astype(float)
    x["C14_review_known_log"] = np.log1p(rk)
    x["F_log"] = np.log1p(F)
    x["M_log"] = np.log1p(d["M"].astype(float))
    x["recent30_spend_log"] = np.log1p(d["recent30_spend"].astype(float))
    for c in ["R", "average_item_rows", "freight_share", "recent30_orders",
              "observed_history_days"]:
        x[c] = d[c].astype(float)
    out = pd.concat([d[KEY], x], axis=1)
    return out


CANDIDATE_COL = {c[0]: "C%02d_%s" % (int(c[0][1:]), c[1]) for c in CANDIDATES}


def cohens_d(v: np.ndarray, y: np.ndarray) -> float:
    ok = np.isfinite(v)
    v, y = v[ok], y[ok]
    a, b = v[y == 1], v[y == 0]
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    s = np.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1))
                / (len(a) + len(b) - 2))
    return float((a.mean() - b.mean()) / s) if s > 0 else float("nan")


def auc(v: np.ndarray, y: np.ndarray) -> float:
    """Rank-based AUC with average ties; no scipy dependency."""
    ok = np.isfinite(v)
    v, y = v[ok], y[ok]
    n1 = int(y.sum())
    n0 = len(y) - n1
    if len(v) < 10 or n1 == 0 or n0 == 0:
        return float("nan")
    r = pd.Series(v).rank(method="average").to_numpy()
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    hw = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (float(mid - hw), float(mid + hw))
