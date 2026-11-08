import numpy as np
import pandas as pd


TRAIN_CSV = "data/raw/ja_gnn_financial_transactions_300k.csv"
WMNC_FILE = "data/graphs/wmnc/wmnc_scores.npz"


print("=" * 60)
print("FRAUD GRAPH SIGNAL ANALYSIS")
print("=" * 60)


# ============================================================
# LOAD DATA
# ============================================================

print("\nLoading transactions...")

df = pd.read_csv(TRAIN_CSV)

df = df[df["split"] == "train"].copy()
df = df.reset_index(drop=True)

labels = df["is_fraud"].to_numpy()

print("Transactions:", len(df))
print("Fraud:", int(labels.sum()))
print("Legitimate:", int((labels == 0).sum()))


# ============================================================
# BUILD ATTRIBUTE MEMBERSHIP
# ============================================================

relation_columns = {
    "sender": ["sender_id"],
    "receiver": ["receiver_id"],
    "merchant": ["merchant_id"],
    "device": ["device_id"],
    "ip": ["ip_id"],
    "location": ["location_id"],
    "transaction_type": ["transaction_type"],
    "channel": ["channel"],
    "hour": ["hour"],
    "day_of_week": ["day_of_week"],
    "receiver_merchant": ["receiver_id", "merchant_id"],
    "sender_merchant": ["sender_id", "merchant_id"]
}


print("\nBuilding attribute groups...")

fraud_neighbor_ratios = []
legit_neighbor_ratios = []


# ============================================================
# ANALYZE EACH RELATION
# ============================================================

for relation_name, columns in relation_columns.items():

    print("\n" + "-" * 60)
    print("Relation:", relation_name)

    groups = df.groupby(columns).indices

    fraud_ratios = []
    legit_ratios = []

    for indices in groups.values():

        indices = np.asarray(indices)

        if len(indices) < 2:
            continue

        group_labels = labels[indices]

        fraud_indices = indices[group_labels == 1]
        legit_indices = indices[group_labels == 0]

        fraud_count = len(fraud_indices)
        legit_count = len(legit_indices)

        total = fraud_count + legit_count

        if total == 0:
            continue

        fraud_ratio = fraud_count / total

        fraud_ratios.append(fraud_ratio)

        if fraud_count > 0:
            fraud_neighbor_ratios.extend(
                [fraud_ratio] * fraud_count
            )

        if legit_count > 0:
            legit_neighbor_ratios.extend(
                [fraud_ratio] * legit_count
            )

    if fraud_ratios:

        print(
            "Groups:",
            len(fraud_ratios)
        )

        print(
            "Average fraud ratio:",
            round(float(np.mean(fraud_ratios)), 6)
        )

        print(
            "Median fraud ratio:",
            round(float(np.median(fraud_ratios)), 6)
        )

        print(
            "Maximum fraud ratio:",
            round(float(np.max(fraud_ratios)), 6)
        )

        print(
            "Groups containing fraud:",
            sum(x > 0 for x in fraud_ratios)
        )

        print(
            "Groups containing only fraud:",
            sum(x == 1 for x in fraud_ratios)
        )


# ============================================================
# TRANSACTION-LEVEL SIGNAL
# ============================================================

print("\n" + "=" * 60)
print("TRANSACTION-LEVEL GRAPH SIGNAL")
print("=" * 60)

print(
    "\nAverage fraud-neighborhood ratio for fraud transactions:",
    round(float(np.mean(fraud_neighbor_ratios)), 6)
)

print(
    "Average fraud-neighborhood ratio for legitimate transactions:",
    round(float(np.mean(legit_neighbor_ratios)), 6)
)


# ============================================================
# WMNC ANALYSIS
# ============================================================

print("\n" + "=" * 60)
print("WMNC ANALYSIS")
print("=" * 60)

data = np.load(WMNC_FILE)

pairs = data["pairs"]
scores = data["scores"]

print("WMNC pairs:", len(pairs))
print("WMNC scores:", len(scores))


source_labels = labels[pairs[:, 0]]
target_labels = labels[pairs[:, 1]]


fraud_fraud = (
    (source_labels == 1) &
    (target_labels == 1)
)

fraud_legit = (
    (
        (source_labels == 1) &
        (target_labels == 0)
    )
    |
    (
        (source_labels == 0) &
        (target_labels == 1)
    )
)

legit_legit = (
    (source_labels == 0) &
    (target_labels == 0)
)


def print_stats(name, mask):

    values = scores[mask]

    print("\n", name)

    print("Pairs:", len(values))

    if len(values) == 0:
        print("No pairs")
        return

    print(
        "Mean:",
        round(float(np.mean(values)), 6)
    )

    print(
        "Median:",
        round(float(np.median(values)), 6)
    )

    print(
        "Maximum:",
        round(float(np.max(values)), 6)
    )


print_stats(
    "Fraud-Fraud",
    fraud_fraud
)

print_stats(
    "Fraud-Legitimate",
    fraud_legit
)

print_stats(
    "Legitimate-Legitimate",
    legit_legit
)


# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 60)
print("ANALYSIS COMPLETE")
print("=" * 60)