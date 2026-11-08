"""
Real IEEE-CIS Dataset & Graph Builder for JA-GNN.
Processes raw IEEE-CIS dataset (train_transaction.csv + train_identity.csv)
without ANY synthetic data.
Constructs:
  1. 21-dimensional normalized transaction feature matrix
  2. 12 real-world bipartite entity relations
  3. WMNC candidate co-occurrences
  4. Mahalanobis distance similarity
  5. Top-K hybrid sampled edges with weights
"""

import os
import sys
import time
import json
from collections import defaultdict
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)

def build_real_dataset(num_txns=100000, top_k=10, max_degree=50):
    print("=" * 60)
    print(f"BUILDING REAL IEEE-CIS DATASET & GRAPH (N = {num_txns})")
    print("Zero synthetic data - 100% pure real transaction records")
    print("=" * 60)

    # 1. Read real data
    t0 = time.time()
    tr_path = "data/raw/train_transaction.csv"
    id_path = "data/raw/train_identity.csv"

    if not os.path.exists(tr_path) or not os.path.exists(id_path):
        raise FileNotFoundError(f"Missing raw files: {tr_path} or {id_path}")

    tr_cols = [
        'TransactionID', 'isFraud', 'TransactionDT', 'TransactionAmt',
        'card1', 'card2', 'card3', 'card4', 'card5', 'card6',
        'addr1', 'addr2', 'P_emaildomain', 'R_emaildomain', 'ProductCD',
        'dist1', 'C1', 'C2', 'C4', 'C6', 'C8', 'C11', 'C13', 'C14',
        'D1', 'D2', 'D10', 'D15', 'V44', 'V86', 'V94', 'V70'
    ]

    print(f"Loading {num_txns} transactions from {tr_path}...")
    df_tr = pd.read_csv(tr_path, nrows=num_txns, usecols=tr_cols)
    print(f"Loading matching identity records from {id_path}...")
    df_id = pd.read_csv(id_path, nrows=num_txns, usecols=['TransactionID', 'DeviceInfo'])

    df = pd.merge(df_tr, df_id, on="TransactionID", how="left")
    print(f"Merged in {time.time()-t0:.2f}s. Total transactions: {len(df)}")
    
    fraud_count = int(df['isFraud'].sum())
    legit_count = len(df) - fraud_count
    print(f"Distribution: {fraud_count} Fraud ({df['isFraud'].mean()*100:.2f}%), {legit_count} Legitimate")

    # 2. Extract 21 high-signal real features
    print("\n[Step 1/5] Extracting 21 real features...")
    df['has_identity'] = df['DeviceInfo'].notna().astype(np.float32)
    df['log_amount'] = np.log1p(df['TransactionAmt']).astype(np.float32)
    df['hour'] = ((df['TransactionDT'] // 3600) % 24).astype(np.float32)
    df['day_of_week'] = ((df['TransactionDT'] // (3600 * 24)) % 7).astype(np.float32)

    feature_cols = [
        'log_amount', 'hour', 'day_of_week', 'dist1',
        'C1', 'C2', 'C4', 'C6', 'C8', 'C11', 'C13', 'C14',
        'D1', 'D2', 'D10', 'D15', 'V44', 'V86', 'V94', 'V70', 'has_identity'
    ]

    X_df = df[feature_cols].copy()
    for col in feature_cols:
        X_df[col] = X_df[col].fillna(X_df[col].median()).fillna(0).astype(np.float32)

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_df.values).astype(np.float32)

    # Ensure output directories exist
    os.makedirs("data/processed/scaled", exist_ok=True)
    os.makedirs("data/graphs/bipartite", exist_ok=True)
    os.makedirs("data/graphs/wmnc", exist_ok=True)
    os.makedirs("data/graphs/sampled", exist_ok=True)

    # Save processed features & labels
    scaled_df = pd.DataFrame(X_scaled, columns=feature_cols)
    scaled_df.to_csv("data/processed/scaled/train_scaled.csv", index=False)
    
    labels_df = pd.DataFrame({'is_fraud': df['isFraud'].values.astype(int)})
    labels_df.to_csv("data/processed/train_labels.csv", index=False)

    with open("data/processed/feature_columns.json", "w") as f:
        json.dump(feature_cols, f, indent=2)

    print("Saved scaled features to data/processed/scaled/train_scaled.csv")
    print("Saved labels to data/processed/train_labels.csv")

    # 3. Build 12 Bipartite Relations
    print("\n[Step 2/5] Building 12 real bipartite relations...")
    t1 = time.time()
    RELATIONS = {
        0: 'card1', 1: 'card2', 2: 'card3', 3: 'card4',
        4: 'card5', 5: 'card6', 6: 'addr1', 7: 'addr2',
        8: 'P_emaildomain', 9: 'R_emaildomain', 10: 'DeviceInfo', 11: 'ProductCD'
    }

    edges_s, edges_t, edges_r = [], [], []
    attr_to_id = {}
    attr_mapping = []
    next_attr_id = len(df)

    for r_id, col in RELATIONS.items():
        s = df[col].dropna()
        for idx, val in s.items():
            val_str = str(val)
            k = (r_id, val_str)
            if k not in attr_to_id:
                attr_to_id[k] = next_attr_id
                attr_mapping.append({
                    "attribute_node": next_attr_id,
                    "relation": r_id,
                    "relation_name": col,
                    "value": val_str
                })
                next_attr_id += 1
            edges_s.append(idx)
            edges_t.append(attr_to_id[k])
            edges_r.append(r_id)

    edges_s = np.array(edges_s, dtype=np.int64)
    edges_t = np.array(edges_t, dtype=np.int64)
    edges_r = np.array(edges_r, dtype=np.int64)

    np.savez_compressed(
        "data/graphs/bipartite/train_edges.npz",
        source=edges_s,
        target=edges_t,
        relation=edges_r
    )
    pd.DataFrame(attr_mapping).to_csv("data/graphs/bipartite/attribute_mapping.csv", index=False)

    print(f"Built bipartite graph: {len(df)} transactions, {len(attr_to_id)} attribute nodes, {len(edges_s)} edges in {time.time()-t1:.2f}s")

    # 4. Generate candidate pairs & WMNC
    print("\n[Step 3/5] Generating candidate pairs & computing WMNC scores...")
    t2 = time.time()
    attr_txns = defaultdict(list)
    for s, t in zip(edges_s, edges_t):
        attr_txns[t].append(s)

    candidate_pairs = set()
    for t_node, txns in attr_txns.items():
        if len(txns) > max_degree:
            txns = txns[-max_degree:]
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

    t3 = time.time()
    txn_attrs = defaultdict(set)
    for s, t in zip(edges_s, edges_t):
        txn_attrs[s].add(t)

    txn_degrees = {k: len(v) for k, v in txn_attrs.items()}
    wmnc_scores = np.zeros(len(cand_array), dtype=np.float32)
    for idx, (a, b) in enumerate(cand_array):
        common = len(txn_attrs[a].intersection(txn_attrs[b]))
        deg = min(txn_degrees.get(a, 1), txn_degrees.get(b, 1))
        wmnc_scores[idx] = common / max(deg, 1)

    np.savez_compressed(
        "data/graphs/wmnc/wmnc_scores.npz",
        pairs=cand_array,
        scores=wmnc_scores
    )
    print(f"Computed WMNC scores in {time.time()-t3:.2f}s | Mean: {wmnc_scores.mean():.4f}")

    # 5. Mahalanobis distance
    print("\n[Step 4/5] Computing Mahalanobis feature similarity...")
    t4 = time.time()
    cov = np.cov(X_scaled, rowvar=False)
    inv_cov = np.linalg.pinv(cov)

    a_indices = cand_array[:, 0]
    b_indices = cand_array[:, 1]
    batch_sz = 100000
    mahal_dist = np.zeros(len(cand_array), dtype=np.float32)

    for i in range(0, len(cand_array), batch_sz):
        a_b = a_indices[i:i+batch_sz]
        b_b = b_indices[i:i+batch_sz]
        diff = X_scaled[a_b] - X_scaled[b_b]
        dist_sq = np.sum((diff @ inv_cov) * diff, axis=1)
        mahal_dist[i:i+batch_sz] = np.sqrt(np.maximum(dist_sq, 0.0))

    np.savez_compressed(
        "data/graphs/wmnc/mahalanobis_scores.npz",
        pairs=cand_array,
        distances=mahal_dist
    )
    print(f"Computed Mahalanobis in {time.time()-t4:.2f}s | Mean dist: {mahal_dist.mean():.4f}")

    # 6. Hybrid Sampling
    print("\n[Step 5/5] Sampling hybrid edges (Path B similarity)...")
    t5 = time.time()
    mahal_sim = 1.0 - (mahal_dist - mahal_dist.min()) / (mahal_dist.max() - mahal_dist.min() + 1e-8)
    wmnc_norm = (wmnc_scores - wmnc_scores.min()) / (wmnc_scores.max() - wmnc_scores.min() + 1e-8)
    hybrid_scores = (0.5 * wmnc_norm + 0.5 * mahal_sim).astype(np.float32)

    neighbors = defaultdict(list)
    for idx, (a, b) in enumerate(cand_array):
        sc = hybrid_scores[idx]
        neighbors[a].append((b, sc))
        neighbors[b].append((a, sc))

    sampled_src = []
    sampled_tgt = []
    sampled_score = []

    for u, nbrs in neighbors.items():
        nbrs.sort(key=lambda x: x[1], reverse=True)
        for v, sc in nbrs[:top_k]:
            sampled_src.append(u)
            sampled_tgt.append(v)
            sampled_score.append(sc)

    sampled_src = np.array(sampled_src, dtype=np.int64)
    sampled_tgt = np.array(sampled_tgt, dtype=np.int64)
    sampled_score = np.array(sampled_score, dtype=np.float32)

    np.savez_compressed(
        "data/graphs/sampled/hybrid_edges.npz",
        source=sampled_src,
        target=sampled_tgt,
        score=sampled_score
    )
    print(f"Sampled {len(sampled_src)} hybrid edges in {time.time()-t5:.2f}s")
    print("\n" + "=" * 60)
    print(f"SUCCESS: Real IEEE-CIS Dataset & Graph completely built in {time.time()-t0:.2f}s!")
    print("=" * 60)

if __name__ == "__main__":
    num_txns = 100000
    if len(sys.argv) > 1:
        num_txns = int(sys.argv[1])
    build_real_dataset(num_txns=num_txns)
