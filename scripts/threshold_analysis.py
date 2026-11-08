import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

import numpy as np
import torch
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, average_precision_score

from training.graph_loader import load_graph
from training.relation_neighbor_loader import create_relation_neighbor_loader
from training.train_ja_gnn import (
    create_local_relation_edges,
    create_local_hybrid_edges,
    create_local_maps,
    SEED, BATCH_SIZE, NUM_NEIGHBORS,
    INPUT_CHANNELS, HIDDEN_CHANNELS, NUM_RELATIONS, NUM_LAYERS, DROPOUT,
    CHECKPOINT_PATH
)
from models.ja_gnn.model import JAGNN


def analyze_thresholds():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    data, relation_edges, hybrid_edge_index, hybrid_scores = load_graph()

    num_transactions = getattr(data, "num_transactions", 210000)
    all_indices = np.arange(num_transactions)
    txn_labels = data.y[:num_transactions].numpy()

    train_idx, val_idx = train_test_split(
        all_indices, test_size=0.2, random_state=SEED, stratify=txn_labels
    )
    val_nodes = torch.tensor(val_idx, dtype=torch.long)

    val_loader = create_relation_neighbor_loader(
        data, relation_edges, hybrid_edge_index, hybrid_scores,
        input_nodes=val_nodes, batch_size=BATCH_SIZE, num_neighbors=NUM_NEIGHBORS, shuffle=False
    )

    model = JAGNN(
        input_channels=INPUT_CHANNELS, hidden_channels=HIDDEN_CHANNELS,
        num_relations=NUM_RELATIONS, num_layers=NUM_LAYERS, dropout=DROPOUT
    ).to(device)

    checkpoint = torch.load(CHECKPOINT_PATH, map_location=device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    all_labels, all_probs = [], []
    with torch.no_grad():
        for batch in val_loader:
            batch = batch.to(device)
            local_rel = create_local_relation_edges(batch)
            local_hyb_idx, local_hyb_wt = create_local_hybrid_edges(batch)
            t_map, a_map, t_idx = create_local_maps(batch)

            logits = model(batch.x, local_rel, t_map, a_map, t_idx, local_hyb_idx, local_hyb_wt)
            probs = torch.sigmoid(logits)

            all_labels.extend(batch.y[:batch.batch_size].cpu().numpy())
            all_probs.extend(probs.cpu().numpy())

    all_labels = np.array(all_labels)
    all_probs = np.array(all_probs)

    print("\n========== THRESHOLD SWEEP ANALYSIS ==========")
    print(f"{'Threshold':<12} | {'Precision':<12} | {'Recall':<12} | {'F1-Score':<12}")
    print("-" * 55)

    best_thresh_for_86 = None
    min_dist_to_86 = 999.0

    for t in np.arange(0.50, 0.96, 0.02):
        preds = (all_probs >= t).astype(int)
        prec = precision_score(all_labels, preds, zero_division=0)
        rec = recall_score(all_labels, preds, zero_division=0)
        f1 = f1_score(all_labels, preds, zero_division=0)
        print(f"{t:<12.2f} | {prec:<12.6f} | {rec:<12.6f} | {f1:<12.6f}")

        if prec >= 0.86 and best_thresh_for_86 is None:
            best_thresh_for_86 = (t, prec, rec, f1)

    if best_thresh_for_86:
        t, prec, rec, f1 = best_thresh_for_86
        print("\n" + "="*55)
        print(f"--> TARGET REACHED AT THRESHOLD {t:.2f}:")
        print(f"    Precision: {prec:.6f} (>= 0.86)")
        print(f"    Recall:    {rec:.6f}")
        print(f"    F1-Score:  {f1:.6f}")
        print("="*55)

if __name__ == "__main__":
    analyze_thresholds()
