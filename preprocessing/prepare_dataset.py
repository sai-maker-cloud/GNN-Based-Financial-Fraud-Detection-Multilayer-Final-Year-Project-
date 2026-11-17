import pandas as pd
import numpy as np
import os
import json

INPUT_FILE = "data/raw/ja_gnn_financial_transactions_300k.csv"
OUTPUT_DIR = "data/processed"

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Loading dataset:", INPUT_FILE)
df = pd.read_csv(INPUT_FILE)
print("Dataset shape:", df.shape)

# Sort chronologically
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values("timestamp").reset_index(drop=True)

train_mask = df["split"] == "train"
validation_mask = df["split"] == "validation"
test_mask = df["split"] == "test"

train_df = df.loc[train_mask].reset_index(drop=True)
val_df = df.loc[validation_mask].reset_index(drop=True)
test_df = df.loc[test_mask].reset_index(drop=True)

print(f"Train txns: {len(train_df)}, Val txns: {len(val_df)}, Test txns: {len(test_df)}")

# Compute graph and entity statistics strictly on training data
print("Computing graph and entity topological statistics on train split...")
sender_as_send = train_df.groupby("sender_id")["receiver_id"].agg(["count", "nunique"]).to_dict()
sender_as_rec = train_df.groupby("receiver_id")["sender_id"].agg(["count", "nunique"]).to_dict()

dev_senders = train_df.groupby("device_id")["sender_id"].nunique().to_dict()
dev_receivers = train_df.groupby("device_id")["receiver_id"].nunique().to_dict()

ip_senders = train_df.groupby("ip_id")["sender_id"].nunique().to_dict()
ip_receivers = train_df.groupby("ip_id")["receiver_id"].nunique().to_dict()

sender_amt_mean = train_df.groupby("sender_id")["amount"].mean().to_dict()
rec_amt_mean = train_df.groupby("receiver_id")["amount"].mean().to_dict()

feature_columns = [
    "amount",
    "log_amount",
    "sender_tx_cnt",
    "receiver_tx_cnt",
    "time_sender_sec",
    "time_receiver_sec",
    "sender_out_degree",
    "sender_in_degree",
    "sender_pass_through",
    "receiver_in_degree",
    "receiver_out_degree",
    "receiver_pass_through",
    "sender_uniq_rec",
    "receiver_uniq_send",
    "dev_send_cnt",
    "dev_rec_cnt",
    "ip_send_cnt",
    "ip_rec_cnt",
    "sender_amt_ratio",
    "rec_amt_ratio",
    "is_upi"
]

print(f"Extracting {len(feature_columns)} high-signal financial and topological features...")
assert len(feature_columns) == 21, "Model architecture expects exactly 21 input channels"

def extract_features(d):
    f = pd.DataFrame()
    f["amount"] = d["amount"].astype(np.float32)
    f["log_amount"] = np.log1p(d["amount"]).astype(np.float32)
    f["sender_tx_cnt"] = d["sender_transaction_count_to_date"].astype(np.float32)
    f["receiver_tx_cnt"] = d["receiver_transaction_count_to_date"].astype(np.float32)
    f["time_sender_sec"] = np.log1p(d["time_since_previous_sender_tx_sec"]).astype(np.float32)
    f["time_receiver_sec"] = np.log1p(d["time_since_previous_receiver_tx_sec"]).astype(np.float32)

    # In-degree & Out-degree
    s_out = d["sender_id"].map(sender_as_send["count"]).fillna(0).astype(np.float32)
    s_in = d["sender_id"].map(sender_as_rec["count"]).fillna(0).astype(np.float32)
    f["sender_out_degree"] = s_out
    f["sender_in_degree"] = s_in
    f["sender_pass_through"] = (s_in / (s_out + 1.0)).astype(np.float32)

    r_in = d["receiver_id"].map(sender_as_rec["count"]).fillna(0).astype(np.float32)
    r_out = d["receiver_id"].map(sender_as_send["count"]).fillna(0).astype(np.float32)
    f["receiver_in_degree"] = r_in
    f["receiver_out_degree"] = r_out
    f["receiver_pass_through"] = (r_out / (r_in + 1.0)).astype(np.float32)

    # Fan-in and Fan-out unique peer counts
    f["sender_uniq_rec"] = d["sender_id"].map(sender_as_send["nunique"]).fillna(0).astype(np.float32)
    f["receiver_uniq_send"] = d["receiver_id"].map(sender_as_rec["nunique"]).fillna(0).astype(np.float32)

    # Device & IP multiplexing (mule syndicates)
    f["dev_send_cnt"] = d["device_id"].map(dev_senders).fillna(1).astype(np.float32)
    f["dev_rec_cnt"] = d["device_id"].map(dev_receivers).fillna(1).astype(np.float32)
    f["ip_send_cnt"] = d["ip_id"].map(ip_senders).fillna(1).astype(np.float32)
    f["ip_rec_cnt"] = d["ip_id"].map(ip_receivers).fillna(1).astype(np.float32)

    # Relative amount deviation
    s_mean = d["sender_id"].map(sender_amt_mean).fillna(d["amount"]).astype(np.float32)
    r_mean = d["receiver_id"].map(rec_amt_mean).fillna(d["amount"]).astype(np.float32)
    f["sender_amt_ratio"] = (d["amount"] / (s_mean + 1.0)).astype(np.float32)
    f["rec_amt_ratio"] = (d["amount"] / (r_mean + 1.0)).astype(np.float32)

    # Channel
    f["is_upi"] = (d["channel"] == "UPI").astype(np.float32)

    return f

X_train = extract_features(train_df)
X_validation = extract_features(val_df)
X_test = extract_features(test_df)

y_train = train_df["is_fraud"].astype("int64")
y_validation = val_df["is_fraud"].astype("int64")
y_test = test_df["is_fraud"].astype("int64")

# Save features
X_train.to_csv(f"{OUTPUT_DIR}/train_features.csv", index=False)
X_validation.to_csv(f"{OUTPUT_DIR}/validation_features.csv", index=False)
X_test.to_csv(f"{OUTPUT_DIR}/test_features.csv", index=False)

# Save labels
y_train.to_csv(f"{OUTPUT_DIR}/train_labels.csv", index=False)
y_validation.to_csv(f"{OUTPUT_DIR}/validation_labels.csv", index=False)
y_test.to_csv(f"{OUTPUT_DIR}/test_labels.csv", index=False)

with open(f"{OUTPUT_DIR}/feature_columns.json", "w") as f:
    json.dump(feature_columns, f, indent=2)

print("\n========== PREPROCESSING COMPLETE ==========")
print(f"Train features: {X_train.shape}, Fraud: {y_train.sum()} ({y_train.mean()*100:.2f}%)")
print(f"Validation features: {X_validation.shape}, Fraud: {y_validation.sum()} ({y_validation.mean()*100:.2f}%)")
print(f"Test features: {X_test.shape}, Fraud: {y_test.sum()} ({y_test.mean()*100:.2f}%)")
print("Saved feature columns to:", f"{OUTPUT_DIR}/feature_columns.json")
