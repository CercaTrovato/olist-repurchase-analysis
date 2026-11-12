"""Build the two key-aligned private candidate tables (October + January).

These files contain row-level customer keys and are NEVER written into the public
bundle.  They go to private_outputs/Round3_role02/ and must travel through the
team's private space only.  The public bundle carries only their SHA-256, row
counts, column names and aggregate support tables.
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from r3_common import (CANDIDATES, CANDIDATE_COL, KEY, SPEC_VERSION, BASE_VERSION,
                       ASOF_VERSION, CLUSTER_VERSION, TRAIN_SNAPSHOT,
                       VALIDATION_SNAPSHOT, build_candidate_frame, private_out,
                       read_inputs, sha256, write_csv, write_json)


def main(smoke: bool):
    f, l, a, t, v = read_inputs(smoke)
    paths, support_rows, fit = {}, [], {}
    cluster_map = {
        TRAIN_SNAPSHOT: t[KEY + ["cluster_id"]].assign(cluster_version=CLUSTER_VERSION),
        VALIDATION_SNAPSHOT: v[KEY + ["cluster_id", "cluster_version"]],
    }
    for snap in [TRAIN_SNAPSHOT, VALIDATION_SNAPSHOT]:
        fs, as_ = f[f.snapshot_date == snap], a[a.snapshot_date == snap]
        if len(fs) == 0:
            continue
        x = build_candidate_frame(fs, as_)
        cm = cluster_map[snap]
        x = x.merge(cm, on=KEY, how="left", validate="one_to_one")
        x = x.merge(l[KEY + ["y"]], on=KEY, how="left", validate="one_to_one")
        assert x.cluster_id.notna().all() and x.y.notna().all(), snap
        ordered = (KEY + ["cluster_id", "cluster_version", "y",
                          "data_version", "feature_version", "spec_version"]
                   + [CANDIDATE_COL[c[0]] for c in CANDIDATES])
        x = x.assign(data_version=BASE_VERSION, feature_version=ASOF_VERSION,
                     spec_version=SPEC_VERSION)[ordered]
        tag = "train" if snap == TRAIN_SNAPSHOT else "validation"
        p = private_out(smoke) / ("candidate_features_%s.csv" % tag)
        x.to_csv(p, index=False, encoding="utf-8")
        paths[p.name] = dict(path=str(p), sha256=sha256(p), rows=len(x),
                             columns=list(x.columns), snapshot_date=snap)
        for c in CANDIDATES:
            col = CANDIDATE_COL[c[0]]
            s = x[col]
            support_rows.append(dict(
                snapshot_date=snap, candidate_id=c[0], field=c[1], group=c[2],
                N=len(s), nonmissing=int(s.notna().sum()),
                missing=int(s.isna().sum()), missing_rate=float(s.isna().mean()),
                zero=int((s == 0).sum()), mean=float(s.mean()), std=float(s.std()),
                p25=float(s.quantile(.25)), p50=float(s.quantile(.50)),
                p75=float(s.quantile(.75)), min=float(s.min()), max=float(s.max())))

    # Imputation / scaling parameters fitted on the TRAINING snapshot only.
    tr = pd.read_csv(paths.get("candidate_features_train.csv", {}).get("path", "")) \
        if "candidate_features_train.csv" in paths else pd.DataFrame()
    for c in CANDIDATES:
        col = CANDIDATE_COL[c[0]]
        if col not in tr.columns:
            continue
        s = tr[col].astype(float)
        med = float(s.median()) if s.notna().any() else 0.0
        filled = s.fillna(med)
        fit[c[1]] = dict(impute_median_train=med,
                         standard_mean_train=float(filled.mean()),
                         standard_std_train=float(filled.std(ddof=0)) or 1.0,
                         missing_indicator=(c[1].endswith("_missing")))
    write_json(dict(spec_version=SPEC_VERSION, train_snapshot=TRAIN_SNAPSHOT,
                    note="All fit statistics use only 2017-10-01 training rows. "
                         "Apply these fixed values to 2018-01-01; never refit on validation.",
                    fields=fit), "tables/r3_transform_fit.json", smoke)

    write_csv(pd.DataFrame(support_rows), "tables/r3_candidate_support.csv", smoke)
    write_json(dict(spec_version=SPEC_VERSION, privacy="team-only row-level data",
                    files=paths), "tables/r3_private_manifest.json", smoke)
    print("[r3_build_candidates] smoke=%s private_tables=%d candidates=%d -> %s" %
          (smoke, len(paths), len(CANDIDATES), private_out(smoke)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    main(args.smoke)
