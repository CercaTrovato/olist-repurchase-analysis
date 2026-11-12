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
ROLE01 = ROOT / "Round3_role01_time_v1"
OUT = ROOT / "Round3_role03_prediction_v1"
FEATURES_PATH = H02 / "snapshot_features.csv"
LABELS_PATH = H02 / "snapshot_labels.csv"
ASOF_PATH = ROLE01 / "snapshot-asof-features.csv"
TRAIN_DATE = "2017-10-01"
VALIDATION_DATE = "2018-01-01"
KEY = ["customer_unique_id", "snapshot_date"]
BASE_NUMERIC = [
    "R", "F", "M", "average_item_rows", "freight_share",
    "recent30_orders", "recent30_spend",
]
BASE_CATEGORICAL = ["state"]
DELIVERY_FEATURES = [
    "delivered_known_n", "delivery_days_mean", "late_delivery_share",
]
REVIEW_FEATURES = [
    "review_known_n", "review_score_mean", "low_review_share",
]
VARIANTS = {
    "F0_base": [],
    "F1_delivery": DELIVERY_FEATURES,
    "F2_review": REVIEW_FEATURES,
}


def load_data() -> pd.DataFrame:
    features = pd.read_csv(FEATURES_PATH, dtype={"customer_unique_id": "string"})
    labels = pd.read_csv(
        LABELS_PATH, dtype={"customer_unique_id": "string"}, usecols=KEY + ["y"]
    )
    asof = pd.read_csv(ASOF_PATH, dtype={"customer_unique_id": "string"})
    data = (
        features.merge(labels, on=KEY, validate="one_to_one")
        .merge(asof, on=KEY, how="left", validate="one_to_one")
    )
    missing = sorted(set(sum(VARIANTS.values(), [])) - set(data.columns))
    if missing:
        raise ValueError(f"Round3 features missing from role01 output: {missing}")
    return data


def make_model(extra_features: list[str], weighted: bool) -> Pipeline:
    numeric = BASE_NUMERIC + extra_features
    numeric_pipeline = Pipeline(
        [
            ("log1p", FunctionTransformer(np.log1p, feature_names_out="one-to-one")),
            ("impute", SimpleImputer(strategy="median", add_indicator=True)),
            ("scale", StandardScaler()),
        ]
    )
    preprocess = ColumnTransformer(
        [
            ("numeric", numeric_pipeline, numeric),
            (
                "state",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
                    ]
                ),
                BASE_CATEGORICAL,
            ),
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
                    class_weight="balanced" if weighted else None,
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


def score_metrics(y: np.ndarray, scores: np.ndarray, ids: pd.Series, fraction: float) -> dict:
    selected = top_k(scores, ids, fraction)
    positives = int(y.sum())
    hits = int(y[selected == 1].sum())
    return {
        "N": len(y),
        "positive_count": positives,
        "K": int(selected.sum()),
        "hits": hits,
        "precision": hits / int(selected.sum()),
        "recall": hits / positives if positives else None,
        "AP": float(average_precision_score(y, scores)),
        "ROC_AUC": float(roc_auc_score(y, scores)),
    }


def cross_validate(
    train: pd.DataFrame,
    variant: str,
    weighted: bool,
    folds: int = 5,
) -> list[dict]:
    extra = VARIANTS[variant]
    X = train[BASE_NUMERIC + extra + BASE_CATEGORICAL]
    y = train["y"].to_numpy(dtype=int)
    ids = train["customer_unique_id"]
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=2026)
    rows = []
    for fold, (fit_idx, valid_idx) in enumerate(splitter.split(X, y), start=1):
        model = make_model(extra, weighted)
        model.fit(X.iloc[fit_idx], y[fit_idx])
        scores = model.predict_proba(X.iloc[valid_idx])[:, 1]
        metrics = score_metrics(
            y[valid_idx], scores, ids.iloc[valid_idx], fraction=0.10
        )
        rows.append(
            {
                "variant": variant,
                "weighted": weighted,
                "fold": fold,
                **metrics,
            }
        )
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = load_data()
    train = data.loc[data["snapshot_date"].eq(TRAIN_DATE)].copy()
    validation = data.loc[data["snapshot_date"].eq(VALIDATION_DATE)].copy()
    if train.empty or validation.empty:
        raise ValueError("October training or January validation snapshot is empty.")

    cv_rows = []
    for variant in VARIANTS:
        for weighted in [False, True]:
            cv_rows.extend(cross_validate(train, variant, weighted))
    cv = pd.DataFrame(cv_rows)
    cv.to_csv(OUT / "cv-fold-results.csv", index=False)
    cv_summary = (
        cv.groupby(["variant", "weighted"], as_index=False)
        .agg(
            cv_hits_mean=("hits", "mean"),
            cv_hits_std=("hits", "std"),
            cv_precision_mean=("precision", "mean"),
            cv_recall_mean=("recall", "mean"),
            cv_ap_mean=("AP", "mean"),
            cv_ap_std=("AP", "std"),
            cv_roc_auc_mean=("ROC_AUC", "mean"),
        )
    )
    cv_summary.to_csv(OUT / "cv-summary.csv", index=False)

    prediction_columns = KEY + ["split", "y"]
    if "data_version" in validation.columns:
        prediction_columns.insert(3, "data_version")
    prediction_frame = validation[prediction_columns].copy()
    jan_rows = []
    for variant, extra in VARIANTS.items():
        for weighted in [False, True]:
            name = f"{variant}_{'weighted' if weighted else 'unweighted'}"
            model = make_model(extra, weighted)
            model.fit(
                train[BASE_NUMERIC + extra + BASE_CATEGORICAL],
                train["y"],
            )
            scores = model.predict_proba(
                validation[BASE_NUMERIC + extra + BASE_CATEGORICAL]
            )[:, 1]
            prediction_frame[f"{name}_score"] = scores
            for fraction in [0.05, 0.10, 0.20]:
                selected = top_k(scores, validation["customer_unique_id"], fraction)
                prediction_frame[f"{name}_selected_{int(fraction * 100)}"] = selected
                jan_rows.append(
                    {
                        "variant": variant,
                        "weighted": weighted,
                        "method": name,
                        "top_fraction": fraction,
                        **score_metrics(
                            validation["y"].to_numpy(dtype=int),
                            scores,
                            validation["customer_unique_id"],
                            fraction,
                        ),
                    }
                )
    prediction_frame.to_csv(OUT / "january-predictions.csv", index=False)
    pd.DataFrame(jan_rows).to_csv(OUT / "january-comparison.csv", index=False)

    metadata = {
        "round": "round3",
        "feature_version": "round3-role01-time-v1",
        "train_snapshot": TRAIN_DATE,
        "validation_snapshot": VALIDATION_DATE,
        "cv": {
            "method": "StratifiedKFold",
            "folds": 5,
            "shuffle": True,
            "random_state": 2026,
            "fit_scope": "October training snapshot only",
        },
        "variants": VARIANTS,
        "models": ["LogisticRegression", "LogisticRegressionWeighted"],
        "ranking": "score descending, customer_unique_id ascending for ties",
        "capacities": [0.05, 0.10, 0.20],
        "group_models": "Not run: October customer-level group labels were not supplied in the permitted inputs.",
    }
    (OUT / "run-metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(cv_summary.to_string(index=False))
    print(jan_rows)
    print(f"Wrote Round3 outputs to {OUT}")


if __name__ == "__main__":
    main()
