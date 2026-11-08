import os
import sys

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

import random
import numpy as np
import torch
import torch.nn as nn

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score
)

from training.graph_loader import load_graph
from training.relation_neighbor_loader import (
    create_relation_neighbor_loader,
    HYBRID_EDGE_TYPE
)
from models.ja_gnn.model import JAGNN


# ==========================================================
# CONFIGURATION (PROVEN HIGH-PERFORMANCE CONFIG)
# ==========================================================

SEED = 42

BATCH_SIZE = 1024

NUM_NEIGHBORS = 5

INPUT_CHANNELS = 21

HIDDEN_CHANNELS = 128

NUM_RELATIONS = 12

NUM_LAYERS = 2

DROPOUT = 0.1

LEARNING_RATE = 1e-3

WEIGHT_DECAY = 1e-5

EPOCHS = 20

PATIENCE = 7

CHECKPOINT_PATH = (
    "results/checkpoints/"
    "best_ja_gnn_custom.pt"
)


# ==========================================================
# SEED
# ==========================================================

def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


# ==========================================================
# METRICS
# ==========================================================

def calculate_metrics(labels, probabilities):
    predictions = (probabilities >= 0.5).astype(int)

    precision = precision_score(labels, predictions, zero_division=0)
    recall = recall_score(labels, predictions, zero_division=0)
    f1 = f1_score(labels, predictions, zero_division=0)
    roc_auc = roc_auc_score(labels, probabilities)
    pr_auc = average_precision_score(labels, probabilities)

    return precision, recall, f1, roc_auc, pr_auc


# ==========================================================
# CREATE LOCAL NODE MAPS
# ==========================================================

def create_local_maps(batch):
    num_nodes = batch.x.shape[0]
    num_transactions = batch.batch_size

    transaction_nodes = torch.where(batch.node_type == 0)[0]
    attribute_nodes = torch.where(batch.node_type == 1)[0]

    transaction_map = torch.full(
        (num_nodes,), -1, dtype=torch.long, device=batch.x.device
    )
    transaction_map[transaction_nodes] = torch.arange(
        transaction_nodes.shape[0], device=batch.x.device
    )

    attribute_map = torch.full(
        (num_nodes,), -1, dtype=torch.long, device=batch.x.device
    )
    attribute_map[attribute_nodes] = torch.arange(
        attribute_nodes.shape[0], device=batch.x.device
    )

    transaction_indices = torch.arange(
        num_transactions, device=batch.x.device
    )

    return transaction_map, attribute_map, transaction_indices


# ==========================================================
# CREATE RELATION EDGES
# ==========================================================

def create_local_relation_edges(batch):
    relation_edges = []
    for relation_index in range(NUM_RELATIONS):
        mask = batch.edge_type == relation_index
        edge_index = batch.edge_index[:, mask]
        relation_edges.append(edge_index)
    return relation_edges


# ==========================================================
# CREATE HYBRID EDGES
# ==========================================================

def create_local_hybrid_edges(batch):
    if not hasattr(batch, "edge_type"):
        return None, None

    mask = batch.edge_type == HYBRID_EDGE_TYPE
    if not mask.any():
        return None, None

    hybrid_edge_index = batch.edge_index[:, mask]
    hybrid_edge_weight = (
        batch.edge_weight[mask]
        if hasattr(batch, "edge_weight")
        else None
    )

    return hybrid_edge_index, hybrid_edge_weight


# ==========================================================
# EVALUATION LOOP
# ==========================================================

def evaluate(model, val_loader, criterion, device):
    model.eval()

    total_loss = 0.0
    all_labels = []
    all_probabilities = []
    total_samples = 0

    with torch.no_grad():
        for batch in val_loader:
            batch = batch.to(device)

            local_relation_edges = create_local_relation_edges(batch)
            local_hybrid_edges, local_hybrid_weight = create_local_hybrid_edges(batch)

            transaction_map, attribute_map, transaction_indices = create_local_maps(batch)

            logits = model(
                batch.x,
                local_relation_edges,
                transaction_map,
                attribute_map,
                transaction_indices,
                hybrid_edge_index=local_hybrid_edges,
                hybrid_edge_weight=local_hybrid_weight
            )

            target_labels = batch.y[:batch.batch_size].float()
            loss = criterion(logits, target_labels)

            total_loss += loss.item() * batch.batch_size
            total_samples += batch.batch_size

            probabilities = torch.sigmoid(logits)

            all_labels.extend(target_labels.cpu().numpy())
            all_probabilities.extend(probabilities.cpu().numpy())

    val_loss = total_loss / max(total_samples, 1)

    all_labels = np.array(all_labels)
    all_probabilities = np.array(all_probabilities)

    precision, recall, f1, roc_auc, pr_auc = calculate_metrics(
        all_labels, all_probabilities
    )

    return val_loss, precision, recall, f1, roc_auc, pr_auc


# ==========================================================
# TRAIN
# ==========================================================

def train():
    set_seed(SEED)

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    print("========== DEVICE ==========")
    print("Device:", device)
    if torch.cuda.is_available():
        print("GPU:", torch.cuda.get_device_name(0))

    # Load Graph
    print("\n========== LOADING GRAPH ==========")
    data, relation_edges, hybrid_edge_index, hybrid_scores = load_graph()

    # Stratified Train/Val split (80/20) on transaction nodes
    num_transactions = getattr(data, "num_transactions", 210000)
    all_transaction_indices = np.arange(num_transactions)
    txn_labels = data.y[:num_transactions].numpy()

    train_idx, val_idx = train_test_split(
        all_transaction_indices,
        test_size=0.2,
        random_state=SEED,
        stratify=txn_labels
    )

    train_nodes = torch.tensor(train_idx, dtype=torch.long)
    val_nodes = torch.tensor(val_idx, dtype=torch.long)

    print(f"Train transaction nodes: {len(train_nodes)}")
    print(f"Val transaction nodes:   {len(val_nodes)}")

    print("\n========== CREATING LOADERS ==========")
    train_loader = create_relation_neighbor_loader(
        data,
        relation_edges,
        hybrid_edge_index=hybrid_edge_index,
        hybrid_scores=hybrid_scores,
        input_nodes=train_nodes,
        batch_size=BATCH_SIZE,
        num_neighbors=NUM_NEIGHBORS,
        num_layers=NUM_LAYERS,
        shuffle=True
    )

    val_loader = create_relation_neighbor_loader(
        data,
        relation_edges,
        hybrid_edge_index=hybrid_edge_index,
        hybrid_scores=hybrid_scores,
        input_nodes=val_nodes,
        batch_size=BATCH_SIZE,
        num_neighbors=NUM_NEIGHBORS,
        num_layers=NUM_LAYERS,
        shuffle=False
    )

    print("\n========== CREATING MODEL ==========")
    model = JAGNN(
        input_channels=INPUT_CHANNELS,
        hidden_channels=HIDDEN_CHANNELS,
        num_relations=NUM_RELATIONS,
        num_layers=NUM_LAYERS,
        dropout=DROPOUT
    ).to(device)

    total_parameters = sum(
        p.numel() for p in model.parameters()
    )
    print("Model parameters:", total_parameters)

    # Standard Adam Optimizer (proven fast convergence for JA-GNN)
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY
    )

    train_labels = data.y[train_nodes]
    positive_samples = int(train_labels.sum().item())
    negative_samples = int((train_labels == 0).sum().item())

    pos_weight = negative_samples / max(positive_samples, 1)

    print("\nTrain Positive samples:", positive_samples)
    print("Train Negative samples:", negative_samples)
    print("Positive class weight:", round(pos_weight, 4))

    criterion = nn.BCEWithLogitsLoss(
        pos_weight=torch.tensor(
            pos_weight, dtype=torch.float32, device=device
        )
    )

    checkpoint_directory = os.path.dirname(CHECKPOINT_PATH)
    os.makedirs(checkpoint_directory, exist_ok=True)

    best_val_pr_auc = 0.0
    best_val_roc_auc = 0.0
    patience_counter = 0

    print("\n========== STARTING TRAINING ==========")

    for epoch in range(1, EPOCHS + 1):
        model.train()

        total_train_loss = 0.0
        train_samples = 0
        all_train_labels = []
        all_train_probs = []

        for batch_number, batch in enumerate(train_loader, start=1):
            batch = batch.to(device)
            optimizer.zero_grad()

            local_relation_edges = create_local_relation_edges(batch)
            local_hybrid_edges, local_hybrid_weight = create_local_hybrid_edges(batch)

            transaction_map, attribute_map, transaction_indices = create_local_maps(batch)

            logits = model(
                batch.x,
                local_relation_edges,
                transaction_map,
                attribute_map,
                transaction_indices,
                hybrid_edge_index=local_hybrid_edges,
                hybrid_edge_weight=local_hybrid_weight
            )

            target_labels = batch.y[:batch.batch_size].float()
            loss = criterion(logits, target_labels)

            loss.backward()

            optimizer.step()

            total_train_loss += loss.item() * batch.batch_size
            train_samples += batch.batch_size

            probabilities = torch.sigmoid(logits)

            all_train_labels.extend(target_labels.detach().cpu().numpy())
            all_train_probs.extend(probabilities.detach().cpu().numpy())

            if batch_number % 20 == 0:
                print(
                    f"Epoch {epoch:02d} | Batch {batch_number:03d} | Loss: {loss.item():.4f}"
                )

        train_loss = total_train_loss / max(train_samples, 1)

        train_prec, train_rec, train_f1, train_roc, train_pr = calculate_metrics(
            np.array(all_train_labels), np.array(all_train_probs)
        )

        val_loss, val_prec, val_rec, val_f1, val_roc, val_pr = evaluate(
            model, val_loader, criterion, device
        )

        print("\n----------------------------------------")
        print(f"Epoch: {epoch:02d}")
        print(f"Train Loss: {train_loss:.6f} | Train ROC-AUC: {train_roc:.6f} | Train PR-AUC: {train_pr:.6f}")
        print(f"Val Loss:   {val_loss:.6f}")
        print(f"Val Precision: {val_prec:.6f} | Val Recall: {val_rec:.6f} | Val F1: {val_f1:.6f}")
        print(f"Val ROC-AUC:   {val_roc:.6f}")
        print(f"Val PR-AUC:    {val_pr:.6f}")
        print("----------------------------------------")

        if val_pr > best_val_pr_auc:
            best_val_pr_auc = val_pr
            best_val_roc_auc = val_roc
            patience_counter = 0

            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "val_pr_auc": val_pr,
                    "val_roc_auc": val_roc,
                    "val_f1": val_f1,
                    "val_precision": val_prec,
                    "val_recall": val_rec,
                },
                CHECKPOINT_PATH
            )

            print("--> Best model saved.")

        else:
            patience_counter += 1
            print(f"No improvement: {patience_counter}/{PATIENCE}")

        if patience_counter >= PATIENCE:
            print("\nEarly stopping triggered.")
            break

    print("\n========== TRAINING COMPLETE ==========")
    print(f"Best Val PR-AUC:  {best_val_pr_auc:.6f}")
    print(f"Best Val ROC-AUC: {best_val_roc_auc:.6f}")
    print("Checkpoint saved at:", CHECKPOINT_PATH)


if __name__ == "__main__":
    train()