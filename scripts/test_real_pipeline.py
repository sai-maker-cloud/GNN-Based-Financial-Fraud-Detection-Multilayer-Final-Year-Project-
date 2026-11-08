"""
Test script to prototype end-to-end real IEEE-CIS data processing,
graph construction, and JA-GNN training without any synthetic data.
"""

import os
import time
from collections import defaultdict
import numpy as np
import pandas as pd
import scipy.sparse as sp
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, average_precision_score, precision_score, recall_score, f1_score

os.chdir("Financial-Fraud-Detection")

NUM_TXNS = 100000
print(f"--- Loading {NUM_TXNS} real IEEE-CIS transactions ---")
t0 = time.time()

tr_cols = [
    'TransactionID', 'isFraud', 'TransactionDT', 'TransactionAmt',
    'card1', 'card2', 'card3', 'card4', 'card5', 'card6',
    'addr1', 'addr2', 'P_emaildomain', 'R_emaildomain', 'ProductCD',
    'dist1', 'C1', 'C2', 'C4', 'C6', 'C8', 'C11', 'C13', 'C14',
    'D1', 'D2', 'D10', 'D15', 'V44', 'V86', 'V94', 'V70'
]

df_tr = pd.read_csv("data/raw/train_transaction.csv", nrows=NUM_TXNS, usecols=tr_cols)
df_id = pd.read_csv("data/raw/train_identity.csv", nrows=NUM_TXNS, usecols=['TransactionID', 'DeviceInfo'])

df = pd.merge(df_tr, df_id, on="TransactionID", how="left")
print(f"Loaded and merged {len(df)} transactions in {time.time()-t0:.2f}s")
print(f"Real Frauds: {df['isFraud'].sum()} ({df['isFraud'].mean()*100:.2f}%)")

# Extract 21 high-signal real features
df['has_identity'] = df['DeviceInfo'].notna().astype(np.float32)
df['log_amount'] = np.log1p(df['TransactionAmt']).astype(np.float32)
df['hour'] = ((df['TransactionDT'] // 3600) % 24).astype(np.float32)
df['day_of_week'] = ((df['TransactionDT'] // (3600 * 24)) % 7).astype(np.float32)

feature_cols = [
    'log_amount', 'hour', 'day_of_week', 'dist1',
    'C1', 'C2', 'C4', 'C6', 'C8', 'C11', 'C13', 'C14',
    'D1', 'D2', 'D10', 'D15', 'V44', 'V86', 'V94', 'V70', 'has_identity'
]

X = df[feature_cols].copy()
for col in feature_cols:
    X[col] = X[col].fillna(X[col].median()).fillna(0).astype(np.float32)

y = df['isFraud'].values.astype(np.float32)

# Build 12 Bipartite Relations
RELATIONS = {
    0: 'card1', 1: 'card2', 2: 'card3', 3: 'card4',
    4: 'card5', 5: 'card6', 6: 'addr1', 7: 'addr2',
    8: 'P_emaildomain', 9: 'R_emaildomain', 10: 'DeviceInfo', 11: 'ProductCD'
}

print("--- Building 12 real relations ---")
t1 = time.time()
edges_s, edges_t, edges_r = [], [], []
attr_to_id = {}
next_attr_id = len(df)

for r_id, col in RELATIONS.items():
    s = df[col].dropna()
    for idx, val in s.items():
        k = (r_id, str(val))
        if k not in attr_to_id:
            attr_to_id[k] = next_attr_id
            next_attr_id += 1
        edges_s.append(idx)
        edges_t.append(attr_to_id[k])
        edges_r.append(r_id)

print(f"Built bipartite graph: {len(df)} txns, {len(attr_to_id)} attr nodes, {len(edges_s)} edges in {time.time()-t1:.2f}s")


# --- Vectorized WMNC and Candidate Generation ---
print("--- Generating candidate pairs and WMNC scores ---")
t2 = time.time()
attr_txns = defaultdict(list)
for s, t in zip(edges_s, edges_t):
    attr_txns[t].append(s)

candidate_pairs = set()
MAX_DEGREE = 50
for t_node, txns in attr_txns.items():
    if len(txns) > MAX_DEGREE:
        txns = txns[-MAX_DEGREE:]
    n = len(txns)
    if n < 2:
        continue
    for i in range(n):
        a = txns[i]
        for j in range(i + 1, n):
            b = txns[j]
            if a != b:
                candidate_pairs.add((min(a, b), max(a, b)))

cand_array = np.array(list(candidate_pairs), dtype=np.int64)
print(f"Generated {len(cand_array)} candidate pairs in {time.time()-t2:.2f}s")

# Vectorized WMNC via transaction attribute sets
t3 = time.time()
txn_attrs = defaultdict(set)
for s, t in zip(edges_s, edges_t):
    txn_attrs[s].add(t)

txn_degrees = {k: len(v) for k, v in txn_attrs.items()}

# Vectorized/batched computation
wmnc_scores = np.zeros(len(cand_array), dtype=np.float32)
for idx, (a, b) in enumerate(cand_array):
    common = len(txn_attrs[a].intersection(txn_attrs[b]))
    deg = min(txn_degrees.get(a, 1), txn_degrees.get(b, 1))
    wmnc_scores[idx] = common / max(deg, 1)

print(f"Computed WMNC scores in {time.time()-t3:.2f}s | Mean: {wmnc_scores.mean():.4f}")

# --- Vectorized Mahalanobis Distance ---
print("--- Computing Mahalanobis feature similarity ---")
t4 = time.time()
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X.values)

cov = np.cov(X_scaled, rowvar=False)
inv_cov = np.linalg.pinv(cov)

a_indices = cand_array[:, 0]
b_indices = cand_array[:, 1]

# Batch compute Mahalanobis to keep memory minimal
batch_sz = 100000
mahal_dist = np.zeros(len(cand_array), dtype=np.float32)

for i in range(0, len(cand_array), batch_sz):
    a_batch = a_indices[i:i+batch_sz]
    b_batch = b_indices[i:i+batch_sz]
    diff = X_scaled[a_batch] - X_scaled[b_batch]
    # (diff @ inv_cov) * diff summed over columns
    dist_sq = np.sum((diff @ inv_cov) * diff, axis=1)
    mahal_dist[i:i+batch_sz] = np.sqrt(np.maximum(dist_sq, 0.0))

print(f"Computed Mahalanobis in {time.time()-t4:.2f}s | Mean dist: {mahal_dist.mean():.4f}")

# --- Hybrid Sampling ---
print("--- Sampling hybrid edges ---")
t5 = time.time()
mahal_sim = 1.0 - (mahal_dist - mahal_dist.min()) / (mahal_dist.max() - mahal_dist.min() + 1e-8)
wmnc_norm = (wmnc_scores - wmnc_scores.min()) / (wmnc_scores.max() - wmnc_scores.min() + 1e-8)
hybrid_scores = 0.5 * wmnc_norm + 0.5 * mahal_sim

# Neighbor list & top-K sampling
neighbors = defaultdict(list)
for idx, (a, b) in enumerate(cand_array):
    score = hybrid_scores[idx]
    neighbors[a].append((b, score))
    neighbors[b].append((a, score))

TOP_K = 10
sampled_src = []
sampled_tgt = []
sampled_score = []

for u, nbrs in neighbors.items():
    nbrs.sort(key=lambda x: x[1], reverse=True)
    for v, sc in nbrs[:TOP_K]:
        sampled_src.append(u)
        sampled_tgt.append(v)
        sampled_score.append(sc)

print(f"Sampled {len(sampled_src)} hybrid transaction edges in {time.time()-t5:.2f}s")
