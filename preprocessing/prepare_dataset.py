import pandas as pd
import os
import json

INPUT_FILE = "data/raw/ja_gnn_financial_transactions_300k.csv"
OUTPUT_DIR = "data/processed"

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Loading dataset...")
df = pd.read_csv(INPUT_FILE)

print("\nDataset shape:", df.shape)

# Sort chronologically
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values("timestamp").reset_index(drop=True)

# Check fraud distribution
print("\nOverall fraud distribution:")
print(df["is_fraud"].value_counts())
print(df["is_fraud"].value_counts(normalize=True))

# Columns that must NOT become model features
drop_columns = [
    "transaction_id",
    "timestamp",
    "split",
    "is_fraud",
    "fraud_pattern",
    "fraud_case_id",

    # Graph identifiers
    "sender_id",
    "receiver_id",
    "merchant_id",
    "device_id",
    "ip_id",
    "location_id"
]

feature_columns = [
    col for col in df.columns
    if col not in drop_columns
]

print("\nFeature columns:")
print(feature_columns)

# Categorical columns
categorical_columns = [
    "transaction_type",
    "channel"
]

# Numerical columns
numerical_columns = [
    col for col in feature_columns
    if col not in categorical_columns
]

# One-hot encode categorical features
df_encoded = pd.get_dummies(
    df[feature_columns],
    columns=categorical_columns,
    dtype=float
)

# Convert all remaining columns to numeric
df_encoded = df_encoded.astype("float32")

# Labels
labels = df["is_fraud"].astype("int64")

# Use the predefined chronological split
train_mask = df["split"] == "train"
validation_mask = df["split"] == "validation"
test_mask = df["split"] == "test"

X_train = df_encoded.loc[train_mask].reset_index(drop=True)
X_validation = df_encoded.loc[validation_mask].reset_index(drop=True)
X_test = df_encoded.loc[test_mask].reset_index(drop=True)

y_train = labels.loc[train_mask].reset_index(drop=True)
y_validation = labels.loc[validation_mask].reset_index(drop=True)
y_test = labels.loc[test_mask].reset_index(drop=True)

# Save features
X_train.to_csv(
    f"{OUTPUT_DIR}/train_features.csv",
    index=False
)

X_validation.to_csv(
    f"{OUTPUT_DIR}/validation_features.csv",
    index=False
)

X_test.to_csv(
    f"{OUTPUT_DIR}/test_features.csv",
    index=False
)

# Save labels
y_train.to_csv(
    f"{OUTPUT_DIR}/train_labels.csv",
    index=False
)

y_validation.to_csv(
    f"{OUTPUT_DIR}/validation_labels.csv",
    index=False
)

y_test.to_csv(
    f"{OUTPUT_DIR}/test_labels.csv",
    index=False
)

# Save feature names
with open(
    f"{OUTPUT_DIR}/feature_columns.json",
    "w"
) as f:
    json.dump(list(X_train.columns), f, indent=2)

print("\n========== PREPROCESSING COMPLETE ==========")

print("Train:")
print("Features:", X_train.shape)
print("Fraud:", y_train.sum())
print("Legitimate:", len(y_train) - y_train.sum())

print("\nValidation:")
print("Features:", X_validation.shape)
print("Fraud:", y_validation.sum())
print("Legitimate:", len(y_validation) - y_validation.sum())

print("\nTest:")
print("Features:", X_test.shape)
print("Fraud:", y_test.sum())
print("Legitimate:", len(y_test) - y_test.sum())

print("\nSaved files:")
print(f"{OUTPUT_DIR}/train_features.csv")
print(f"{OUTPUT_DIR}/validation_features.csv")
print(f"{OUTPUT_DIR}/test_features.csv")
print(f"{OUTPUT_DIR}/train_labels.csv")
print(f"{OUTPUT_DIR}/validation_labels.csv")
print(f"{OUTPUT_DIR}/test_labels.csv")
print(f"{OUTPUT_DIR}/feature_columns.json")