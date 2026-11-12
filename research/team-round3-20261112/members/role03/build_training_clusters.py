from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits


ROOT = Path(__file__).resolve().parents[1]
FEATURES_PATH = ROOT / "H02_candidate_v2" / "snapshot_features.csv"
OUTPUT_PATH = Path(__file__).resolve().parent / "training_clusters.csv"
TRAIN_DATE = "2017-10-01"
CLUSTER_VERSION = "H05-km3-v1"


def main() -> None:
    snapshots = pd.read_csv(
        FEATURES_PATH,
        dtype={"customer_unique_id": "string"},
    )
    train = snapshots.loc[snapshots["snapshot_date"].eq(TRAIN_DATE)].copy()
    required = ["customer_unique_id", "snapshot_date", "R", "F", "M"]
    missing = sorted(set(required) - set(train.columns))
    if missing:
        raise ValueError(f"Training snapshot is missing required columns: {missing}")
    if train.empty or train["customer_unique_id"].duplicated().any():
        raise ValueError("Training snapshot is empty or has duplicate customers.")

    values = np.column_stack(
        [train["R"], np.log1p(train["F"]), np.log1p(train["M"])]
    )
    scaler = StandardScaler()
    scaled = scaler.fit_transform(values)
    model = KMeans(
        n_clusters=3,
        init="k-means++",
        algorithm="lloyd",
        n_init=20,
        max_iter=300,
        tol=1e-4,
        random_state=42,
    )
    with threadpool_limits(limits=1):
        model.fit(scaled)

    # Match H05's fixed label mapping: the two single-order groups are
    # ordered by recency, and the multi-order group receives label 2.
    by_frequency = np.argsort(model.cluster_centers_[:, 1])
    ordered = sorted(
        by_frequency[:2],
        key=lambda index: model.cluster_centers_[index, 0],
    ) + [by_frequency[2]]
    label_map = np.argsort(ordered)
    train["cluster_id"] = label_map[model.labels_].astype(int)
    train["cluster_version"] = CLUSTER_VERSION

    output = train[
        ["customer_unique_id", "snapshot_date", "cluster_id", "cluster_version"]
    ].sort_values("customer_unique_id")
    output.to_csv(OUTPUT_PATH, index=False)
    print(output.groupby("cluster_id").size().to_string())
    print(f"Wrote {len(output)} training cluster labels to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
