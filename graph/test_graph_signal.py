import numpy as np
import pandas as pd

from sklearn.metrics import (
    roc_auc_score,
    average_precision_score
)


TRAIN_CSV = "data/raw/ja_gnn_financial_transactions_300k.csv"
WMNC_FILE = "data/graphs/wmnc/wmnc_scores.npz"


print("=" * 60)
print("GRAPH SIGNAL CLASSIFICATION TEST")
print("=" * 60)


# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_csv(TRAIN_CSV)

df = df[df["split"] == "train"].copy()
df = df.reset_index(drop=True)

labels = df["is_fraud"].to_numpy()

print("Transactions:", len(labels))
print("Fraud:", int(labels.sum()))
print("Legitimate:", int((labels == 0).sum()))


# ============================================================
# LOAD WMNC
# ============================================================

data = np.load(WMNC_FILE)

pairs = data["pairs"]
scores = data["scores"]

print("WMNC pairs:", len(pairs))


# ============================================================
# CALCULATE NEIGHBOR STATISTICS
# ============================================================

fraud_neighbor_score = np.zeros(
    len(labels),
    dtype=np.float64
)

neighbor_count = np.zeros(
    len(labels),
    dtype=np.int64
)


for i in range(len(pairs)):

    source = pairs[i, 0]
    target = pairs[i, 1]
    score = scores[i]

    fraud_neighbor_score[source] += (
        score * labels[target]
    )

    fraud_neighbor_score[target] += (
        score * labels[source]
    )

    neighbor_count[source] += 1
    neighbor_count[target] += 1


# ============================================================
# NORMALIZE
# ============================================================

fraud_neighbor_ratio = (
    fraud_neighbor_score
    / np.maximum(neighbor_count, 1)
)


# ============================================================
# METRICS
# ============================================================

roc_auc = roc_auc_score(
    labels,
    fraud_neighbor_ratio
)

pr_auc = average_precision_score(
    labels,
    fraud_neighbor_ratio
)


print("\n" + "=" * 60)
print("RESULT")
print("=" * 60)

print(
    "ROC-AUC:",
    round(roc_auc, 6)
)

print(
    "PR-AUC:",
    round(pr_auc, 6)
)


# ============================================================
# CLASS STATISTICS
# ============================================================

fraud_values = fraud_neighbor_ratio[
    labels == 1
]

legitimate_values = fraud_neighbor_ratio[
    labels == 0
]


print("\nFraud transactions:")
print(
    "Mean:",
    round(float(np.mean(fraud_values)), 6)
)

print(
    "Median:",
    round(float(np.median(fraud_values)), 6)
)

print(
    "Min:",
    round(float(np.min(fraud_values)), 6)
)

print(
    "Max:",
    round(float(np.max(fraud_values)), 6)
)


print("\nLegitimate transactions:")
print(
    "Mean:",
    round(float(np.mean(legitimate_values)), 6)
)

print(
    "Median:",
    round(float(np.median(legitimate_values)), 6)
)

print(
    "Min:",
    round(float(np.min(legitimate_values)), 6)
)

print(
    "Max:",
    round(float(np.max(legitimate_values)), 6)
)


print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)