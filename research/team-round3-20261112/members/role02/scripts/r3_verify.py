"""Pre-handoff self-check and LF-terminated SHA-256 manifest for the public bundle."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from r3_common import (ASOF_VERSION, BASE_VERSION, CLUSTER_VERSION, BUNDLE,
                       KEY, SPEC_VERSION, TRAIN_SNAPSHOT, VALIDATION_SNAPSHOT,
                       out, sha256, write_text)

CHECKS = []
REQUIRED = [
    "README.md", "HANDOFF.md", "ROLE01_RECEIPT.md", "GROUP_MESSAGE.md",
    "feature-spec.md", "feature-spec.json", "candidate-definitions.csv",
    "candidate-screening.csv", "training-feature-evidence.csv",
    "group-comparison.csv", "field-correlation.csv", "chart-index.csv",
    "SELF_CHECK.md", "RUN_LOG.md", "tables/HANDOFF_SUMMARY.md",
    "tables/r3_input_checks.csv", "tables/r3_asof_verification.csv",
    "tables/r3_candidate_support.csv", "tables/r3_fold_selection.csv",
    "tables/r3_january_direction.csv", "tables/r3_distribution_bins.csv",
    "tables/r3_retained_fields.csv", "tables/r3_transform_fit.json",
    "tables/r3_private_manifest.json", "tables/r3_environment.json",
]


def check(name, ok, detail=""):
    CHECKS.append(dict(check=name, status="PASS" if ok else "FAIL", detail=str(detail)))


def read(name):
    p = out() / name
    if not p.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(p)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def main():
    # SELF_CHECK.md and CHECKSUMS.sha256 are produced by this very script, so a
    # first-ever clean run must create the placeholder BEFORE the "present"
    # checks.  Otherwise r3_verify reports a false FAIL on its own output file.
    if not (out() / "SELF_CHECK.md").exists():
        write_text("pending\n", "SELF_CHECK.md")
    for f in REQUIRED:
        check("present: " + f, (out() / f).exists(), str(out() / f))

    ic = read("tables/r3_input_checks.csv")
    check("input checks all PASS", len(ic) > 0 and (ic.status == "PASS").all(),
          "%d/%d PASS" % (int((ic.status == "PASS").sum()), len(ic)))
    av = read("tables/r3_asof_verification.csv")
    check("independent as-of recomputation all PASS",
          len(av) == 14 and (av.status == "PASS").all(),
          "%d/14 PASS, max_abs_diff=%s" % (len(av), av.max_abs_diff.max() if len(av) else "n/a"))

    gc = read("group-comparison.csv")
    coh = gc[gc.field == "(cohort)"] if len(gc) else gc
    check("October cohort N and positives",
          len(coh) == 3 and int(coh.N.sum()) == 21160 and int(coh.positives.sum()) == 211,
          "N=%s pos=%s" % (coh.N.sum() if len(coh) else None,
                           coh.positives.sum() if len(coh) else None))
    check("three clusters reported", sorted(coh.cluster_id.tolist()) == [0, 1, 2] if len(coh) else False,
          coh.cluster_id.tolist() if len(coh) else [])

    sc = read("candidate-screening.csv")
    ret = sc[sc.retained] if len(sc) else sc
    num = ret[~ret.is_missing_flag] if len(ret) else ret
    groups = sorted(num.group.unique().tolist()) if len(num) else []
    check("at most two field groups", 1 <= len(groups) <= 2, groups)
    check("each group has <=2 numeric fields",
          all(int((num.group == g).sum()) <= 2 for g in groups),
          {g: int((num.group == g).sum()) for g in groups})
    check("all 14 candidates retained as evidence", len(sc) == 14, len(sc))
    check("no late/promise-dependent field retained",
          not bool(ret.assumption_dependent.any()) if len(ret) else False,
          ret[ret.assumption_dependent].field.tolist() if len(ret) else [])
    check("rejected candidates have reasons",
          bool((sc[~sc.retained].decision != "screened_out").all()) if len(sc) else False,
          sc[~sc.retained].decision.value_counts().to_dict() if len(sc) else {})

    ev = read("training-feature-evidence.csv")
    check("evidence table has all candidates x 4 scopes", len(ev) == 14 * 4, len(ev))
    jd = read("tables/r3_january_direction.csv")
    check("January direction not used for selection",
          len(jd) > 0 and bool((jd.used_for_selection == False).all()),  # noqa: E712
          "%d rows, used_for_selection=%s" % (len(jd), set(jd.used_for_selection) if len(jd) else {}))

    # privacy: no row-level customer key anywhere in the public bundle
    leaks = []
    for p in sorted(BUNDLE.rglob("*.csv")):
        if "smoke" in p.parts:
            continue
        try:
            cols = pd.read_csv(p, nrows=0).columns.tolist()
        except Exception:
            continue
        if "customer_unique_id" in cols:
            leaks.append(str(p.relative_to(BUNDLE)))
    check("no row-level customer key in public CSVs", not leaks, leaks)
    check("private tables are outside the public bundle",
          not (BUNDLE / "candidate_features_train.csv").exists()
          and not (BUNDLE / "candidate_features_validation.csv").exists())

    pm = json.loads((out() / "tables/r3_private_manifest.json").read_text(encoding="utf-8"))
    ok_private = True
    detail = {}
    for name, meta in pm["files"].items():
        p = Path(meta["path"])
        good = p.exists() and sha256(p) == meta["sha256"]
        ok_private &= good
        detail[name] = dict(exists=p.exists(), rows=meta["rows"], hash_ok=good)
    check("private candidate table hashes match manifest", ok_private, detail)

    ci = read("chart-index.csv")
    fig_ok, fig_bad = 0, []
    for r in ci.itertuples():
        for col in ["png", "svg"]:
            p = out() / getattr(r, col)
            h = getattr(r, col + "_sha256")
            if p.exists() and sha256(p) == h:
                fig_ok += 1
            else:
                fig_bad.append(getattr(r, col))
    check("all figure hashes match chart-index", len(ci) >= 8 and not fig_bad,
          "%d figures, %d hash checks OK, bad=%s" % (len(ci), fig_ok, fig_bad))
    cd = sorted((out() / "chart-data").glob("*.csv"))
    check("chart-data files present and non-empty",
          len(cd) >= 8 and all(p.stat().st_size > 50 for p in cd),
          "%d files" % len(cd))

    spec = (out() / "feature-spec.md").read_text(encoding="utf-8")
    for token in [BASE_VERSION, ASOF_VERSION, CLUSTER_VERSION, SPEC_VERSION,
                  "不", "2,937", "79"]:
        check("feature-spec mentions " + token, token in spec)
    summ = (out() / "tables/HANDOFF_SUMMARY.md").read_text(encoding="utf-8")
    check("handoff summary has real numbers", "21160" in summ and "sha256=" in summ)

    # ---- finalize --------------------------------------------------------
    # Ordering matters (same rule as H03): SELF_CHECK.md must contain its FINAL
    # bytes before we hash the bundle, otherwise the manifest hashes a stale file
    # and `sha256sum -c` fails on SELF_CHECK.md itself.
    df = pd.DataFrame(CHECKS)
    n_fail = int((df.status == "FAIL").sum())
    bundle_files = [p for p in sorted(BUNDLE.rglob("*"))
                    if p.is_file()
                    and p.name != "CHECKSUMS.sha256"
                    and "__pycache__" not in p.parts
                    and p.suffix != ".pyc"]
    n_files = len(bundle_files)
    md = ["# 第三轮 2 号交付前自检", "",
          "由 `scripts/r3_verify.py` 生成。%d 项检查，PASS %d，FAIL %d。" %
          (len(df), len(df) - n_fail, n_fail), "",
          "| 检查 | 结果 | 说明 |", "|---|---|---|"]
    for r in df.itertuples():
        md.append("| %s | %s | %s |" % (r.check, r.status, str(r.detail).replace("|", "\\|")[:220]))
    md += ["", "哈希清单 `CHECKSUMS.sha256` 含 %d 个文件（LF 行尾，可 `sha256sum -c`）。" % n_files,
           "本自检只核文件、版本、人数、哈希与隐私边界；**不核模型增益**，本包未运行模型。", ""]
    write_text("\n".join(md) + "\n", "SELF_CHECK.md")

    # Hash only after every file (including SELF_CHECK.md) is final.
    lines = ["%s  %s" % (sha256(p), p.relative_to(BUNDLE).as_posix()) for p in bundle_files]
    write_text("\n".join(lines) + "\n", "CHECKSUMS.sha256")
    # Re-read the manifest from disk and confirm every entry really matches.
    verified = 0
    for line in (out() / "CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines():
        hh, rel = line.split(None, 1)
        verified += int(sha256(BUNDLE / rel.strip()) == hh)
    print("[r3_verify] %d checks, %d FAIL; wrote SELF_CHECK.md and CHECKSUMS.sha256 "
          "(%d files, %d/%d re-verified)" %
          (len(df), n_fail, len(lines), verified, len(lines)))
    if n_fail:
        print(df[df.status == "FAIL"].to_string(index=False))
        raise SystemExit(1)
    if verified != len(lines):
        raise SystemExit("checksum manifest re-verification failed")


if __name__ == "__main__":
    main()
