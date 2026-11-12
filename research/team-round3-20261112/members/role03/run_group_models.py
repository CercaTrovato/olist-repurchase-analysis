from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parents[1]
H02 = ROOT / "H02_candidate_v2"
OUT = Path(__file__).resolve().parent
TRAIN_CLUSTERS = OUT / "training_clusters.csv"
VALIDATION_CLUSTERS = Path(__file__).resolve().parent / "validation_clusters.csv"
KEY = ["customer_unique_id", "snapshot_date"]
TRAIN_DATE = "2017-10-01"
VALIDATION_DATE = "2018-01-01"
BASE_NUMERIC = [
    "R", "F", "M", "average_item_rows", "freight_share",
    "recent30_orders", "recent30_spend",
]
BASE_CATEGORICAL = ["state"]


def load_snapshots() -> tuple[pd.DataFrame, pd.DataFrame]:
    features = pd.read_csv(
        H02 / "snapshot_features.csv",
        dtype={"customer_unique_id": "string"},
    )
    labels = pd.read_csv(
        H02 / "snapshot_labels.csv",
        dtype={"customer_unique_id": "string"},
        usecols=KEY + ["y"],
    )
    data = features.merge(labels, on=KEY, validate="one_to_one")
    train = data.loc[data["snapshot_date"].eq(TRAIN_DATE)].copy()
    validation = data.loc[data["snapshot_date"].eq(VALIDATION_DATE)].copy()
    train_clusters = pd.read_csv(
        TRAIN_CLUSTERS,
        dtype={"customer_unique_id": "string"},
    )
    validation_clusters = pd.read_csv(
        VALIDATION_CLUSTERS,
        dtype={"customer_unique_id": "string"},
    )
    train = train.merge(
        train_clusters[KEY + ["cluster_id"]],
        on=KEY,
        validate="one_to_one",
    )
    validation = validation.merge(
        validation_clusters[KEY + ["cluster_id"]],
        on=KEY,
        validate="one_to_one",
    )
    if train.empty or validation.empty:
        raise ValueError("Training or validation snapshot is empty.")
    if train["cluster_id"].isna().any() or validation["cluster_id"].isna().any():
        raise ValueError("Cluster labels contain missing values.")
    return train, validation


def make_model(categorical: list[str]) -> Pipeline:
    numeric_pipeline = Pipeline(
        [
            ("log1p", FunctionTransformer(np.log1p, feature_names_out="one-to-one")),
            ("impute", SimpleImputer(strategy="median", add_indicator=True)),
            ("scale", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        [
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    preprocess = ColumnTransformer(
        [
            ("numeric", numeric_pipeline, BASE_NUMERIC),
            ("categorical", categorical_pipeline, categorical),
        ],
        remainder="drop",
    )
    return Pipeline(
        [
            ("preprocess", preprocess),
            (
                "model",
                LogisticRegression(
                    C=1.0,
                    class_weight="balanced",
                    max_iter=2000,
                    random_state=2026,
                ),
            ),
        ]
    )


def top_k(scores: np.ndarray, ids: pd.Series, fraction: float) -> np.ndarray:
    k = math.ceil(fraction * len(scores))
    order = np.lexsort((ids.astype(str).to_numpy(), -scores))
    selected = np.zeros(len(scores), dtype=np.int8)
    selected[order[:k]] = 1
    return selected


def metrics(
    y: np.ndarray,
    scores: np.ndarray,
    ids: pd.Series,
    fraction: float,
) -> dict:
    selected = top_k(scores, ids, fraction)
    hits = int(y[selected == 1].sum())
    return {
        "N": len(y),
        "positive_count": int(y.sum()),
        "K": int(selected.sum()),
        "hits": hits,
        "precision": hits / int(selected.sum()),
        "recall": hits / int(y.sum()) if y.sum() else None,
        "AP": float(average_precision_score(y, scores)),
        "ROC_AUC": float(roc_auc_score(y, scores)),
    }


def fit_segmented(
    fit: pd.DataFrame,
    score: pd.DataFrame,
) -> np.ndarray:
    global_model = make_model(BASE_CATEGORICAL)
    global_model.fit(fit[BASE_NUMERIC + BASE_CATEGORICAL], fit["y"])
    scores = np.empty(len(score), dtype=float)
    for cluster in [0, 1]:
        fit_group = fit.loc[fit["cluster_id"].eq(cluster)]
        score_mask = score["cluster_id"].eq(cluster).to_numpy()
        if fit_group["y"].nunique() < 2:
            scores[score_mask] = global_model.predict_proba(
                score.loc[score_mask, BASE_NUMERIC + BASE_CATEGORICAL]
            )[:, 1]
            continue
        model = make_model(BASE_CATEGORICAL)
        model.fit(fit_group[BASE_NUMERIC + BASE_CATEGORICAL], fit_group["y"])
        scores[score_mask] = model.predict_proba(
            score.loc[score_mask, BASE_NUMERIC + BASE_CATEGORICAL]
        )[:, 1]
    score_group2 = score["cluster_id"].eq(2).to_numpy()
    scores[score_group2] = global_model.predict_proba(
        score.loc[score_group2, BASE_NUMERIC + BASE_CATEGORICAL]
    )[:, 1]
    return scores


def cross_validate(train: pd.DataFrame) -> pd.DataFrame:
    splitter = StratifiedKFold(n_splits=5, shuffle=True, random_state=2026)
    rows = []
    X = train[BASE_NUMERIC + BASE_CATEGORICAL]
    y = train["y"].to_numpy(dtype=int)
    for fold, (fit_idx, valid_idx) in enumerate(splitter.split(X, y), start=1):
        fit = train.iloc[fit_idx]
        valid = train.iloc[valid_idx]
        baseline = make_model(BASE_CATEGORICAL)
        baseline.fit(fit[BASE_NUMERIC + BASE_CATEGORICAL], fit["y"])
        baseline_scores = baseline.predict_proba(
            valid[BASE_NUMERIC + BASE_CATEGORICAL]
        )[:, 1]

        cluster_model = make_model(BASE_CATEGORICAL + ["cluster_id"])
        cluster_model.fit(
            fit[BASE_NUMERIC + BASE_CATEGORICAL + ["cluster_id"]],
            fit["y"],
        )
        cluster_scores = cluster_model.predict_proba(
            valid[BASE_NUMERIC + BASE_CATEGORICAL + ["cluster_id"]]
        )[:, 1]
        segmented_scores = fit_segmented(fit, valid)
        for method, scores in [
            ("F0_global_weighted", baseline_scores),
            ("B_global_with_cluster", cluster_scores),
            ("C_segmented_group2_global_fallback", segmented_scores),
        ]:
            rows.append(
                {
                    "method": method,
                    "fold": fold,
                    **metrics(
                        valid["y"].to_numpy(dtype=int),
                        scores,
                        valid["customer_unique_id"],
                        0.10,
                    ),
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    train, validation = load_snapshots()
    cv = cross_validate(train)
    cv.to_csv(OUT / "group-cv-fold-results.csv", index=False)
    cv_summary = (
        cv.groupby("method", as_index=False)
        .agg(
            cv_hits_mean=("hits", "mean"),
            cv_hits_std=("hits", "std"),
            cv_precision_mean=("precision", "mean"),
            cv_recall_mean=("recall", "mean"),
            cv_ap_mean=("AP", "mean"),
            cv_roc_auc_mean=("ROC_AUC", "mean"),
        )
    )
    cv_summary.to_csv(OUT / "group-cv-summary.csv", index=False)

    baseline = make_model(BASE_CATEGORICAL)
    baseline.fit(train[BASE_NUMERIC + BASE_CATEGORICAL], train["y"])
    cluster_model = make_model(BASE_CATEGORICAL + ["cluster_id"])
    cluster_model.fit(
        train[BASE_NUMERIC + BASE_CATEGORICAL + ["cluster_id"]],
        train["y"],
    )
    score_map = {
        "F0_global_weighted": baseline.predict_proba(
            validation[BASE_NUMERIC + BASE_CATEGORICAL]
        )[:, 1],
        "B_global_with_cluster": cluster_model.predict_proba(
            validation[BASE_NUMERIC + BASE_CATEGORICAL + ["cluster_id"]]
        )[:, 1],
        "C_segmented_group2_global_fallback": fit_segmented(train, validation),
    }

    prediction = validation[KEY + ["cluster_id", "y"]].copy()
    comparison = []
    for method, scores in score_map.items():
        prediction[method + "_score"] = scores
        for fraction in [0.05, 0.10, 0.20]:
            selected = top_k(scores, validation["customer_unique_id"], fraction)
            prediction[method + f"_selected_{int(fraction * 100)}"] = selected
            row = {
                "method": method,
                "top_fraction": fraction,
                **metrics(
                    validation["y"].to_numpy(dtype=int),
                    scores,
                    validation["customer_unique_id"],
                    fraction,
                ),
            }
            for cluster in [0, 1, 2]:
                mask = validation["cluster_id"].eq(cluster).to_numpy()
                row[f"cluster_{cluster}_N"] = int(mask.sum())
                row[f"cluster_{cluster}_selected"] = int(
                    (selected[mask] == 1).sum()
                )
                row[f"cluster_{cluster}_hits"] = int(
                    validation.loc[mask, "y"].to_numpy()[selected[mask] == 1].sum()
                )
            comparison.append(row)
    prediction.to_csv(OUT / "group-model-predictions.csv", index=False)
    pd.DataFrame(comparison).to_csv(OUT / "group-model-comparison.csv", index=False)

    metadata = {
        "train_snapshot": TRAIN_DATE,
        "validation_snapshot": VALIDATION_DATE,
        "cluster_version": "H05-km3-v1",
        "training_clusters": "training_clusters.csv",
        "validation_clusters": str(VALIDATION_CLUSTERS.relative_to(ROOT)),
        "methods": {
            "F0_global_weighted": "Global weighted logistic regression.",
            "B_global_with_cluster": "Global weighted logistic regression with cluster_id.",
            "C_segmented_group2_global_fallback": (
                "Separate weighted models for groups 0 and 1; group 2 uses "
                "the global weighted model."
            ),
        },
        "cv": {
            "method": "StratifiedKFold",
            "folds": 5,
            "random_state": 2026,
            "selection_metric": "Not selected using January labels; January is fixed validation.",
        },
        "ranking": "score descending, customer_unique_id ascending for ties",
        "capacities": [0.05, 0.10, 0.20],
    }
    (OUT / "group-model-metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(cv_summary.to_string(index=False))
    print(pd.DataFrame(comparison).query("top_fraction == 0.1").to_string(index=False))


if __name__ == "__main__":
    main()
