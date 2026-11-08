import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

import torch
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, average_precision_score

from training.graph_loader import load_graph
from training.relation_neighbor_loader import create_relation_neighbor_loader
from models.ja_gnn.model import JAGNN
from training.train_ja_gnn import (
    create_local_relation_edges,
    create_local_hybrid_edges,
    SEED, BATCH_SIZE, NUM_NEIGHBORS
)

def create_local_maps_fixed(batch):
    num_nodes = batch.x.shape[0]
    num_transactions = batch.batch_size

    transaction_nodes = torch.where(batch.node_type == 0)[0]
    attribute_nodes = torch.where(batch.node_type == 1)[0]

    transaction_map = torch.full((num_nodes,), -1, dtype=torch.long, device=batch.x.device)
    transaction_map[transaction_nodes] = torch.arange(transaction_nodes.shape[0], device=batch.x.device)

    attribute_map = torch.full((num_nodes,), -1, dtype=torch.long, device=batch.x.device)
    attribute_map[attribute_nodes] = torch.arange(attribute_nodes.shape[0], device=batch.x.device)

    # FIXED: Extract target node positions in compact transaction_x tensor
    target_transaction_indices = transaction_map[:num_transactions]

    return transaction_map, attribute_map, target_transaction_indices

def test_fixed_mapping():
    data, relation_edges, hybrid_edge_index, hybrid_scores = load_graph()
    num_transactions = data.y.shape[0]
    all_indices = np.arange(num_transactions)

    train_idx, val_idx = train_test_split(
        all_indices, test_size=0.2, random_state=SEED, stratify=data.y.numpy()
    )
    train_nodes = torch.tensor(train_idx, dtype=torch.long)
    val_nodes = torch.tensor(val_idx, dtype=torch.long)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    torch.manual_seed(42)
    np.random.seed(42)

    train_loader = create_relation_neighbor_loader(
        data, relation_edges, hybrid_edge_index, hybrid_scores,
        input_nodes=train_nodes, batch_size=BATCH_SIZE, num_neighbors=NUM_NEIGHBORS, shuffle=True
    )
    val_loader = create_relation_neighbor_loader(
        data, relation_edges, hybrid_edge_index, hybrid_scores,
        input_nodes=val_nodes, batch_size=BATCH_SIZE, num_neighbors=NUM_NEIGHBORS, shuffle=False
    )

    model = JAGNN(input_channels=21, hidden_channels=128, num_relations=12, num_layers=3, dropout=0.3).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)

    train_labels = data.y[train_nodes]
    pos_weight = (train_labels == 0).sum().item() / max(train_labels.sum().item(), 1)
    criterion = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(pos_weight, device=device))

    print("\n========== TESTING FIXED TARGET MAPPING ==========")
    for epoch in range(1, 4):
        model.train()
        train_loss = 0.0
        for batch in train_loader:
            batch = batch.to(device)
            optimizer.zero_grad()
            local_rel = create_local_relation_edges(batch)
            local_hyb_idx, local_hyb_wt = create_local_hybrid_edges(batch)
            t_map, a_map, t_idx = create_local_maps_fixed(batch)

            logits = model(batch.x, local_rel, t_map, a_map, t_idx, local_hyb_idx, local_hyb_wt)
            loss = criterion(logits, batch.y[:batch.batch_size].float())
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            train_loss += loss.item() * batch.batch_size

        model.eval()
        val_labels, val_probs = [], []
        with torch.no_grad():
            for batch in val_loader:
                batch = batch.to(device)
                local_rel = create_local_relation_edges(batch)
                local_hyb_idx, local_hyb_wt = create_local_hybrid_edges(batch)
                t_map, a_map, t_idx = create_local_maps_fixed(batch)
                logits = model(batch.x, local_rel, t_map, a_map, t_idx, local_hyb_idx, local_hyb_wt)
                val_labels.extend(batch.y[:batch.batch_size].cpu().numpy())
                val_probs.extend(torch.sigmoid(logits).cpu().numpy())

        val_roc = roc_auc_score(val_labels, val_probs)
        val_pr = average_precision_score(val_labels, val_probs)
        print(f"Epoch {epoch:02d} | Val ROC-AUC: {val_roc:.6f} | Val PR-AUC: {val_pr:.6f}")

if __name__ == "__main__":
    test_fixed_mapping()
