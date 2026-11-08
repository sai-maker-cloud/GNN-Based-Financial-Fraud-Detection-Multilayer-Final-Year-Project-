import os
import sys

import torch


PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

sys.path.insert(
    0,
    PROJECT_ROOT
)


from training.config import (
    INPUT_CHANNELS,
    HIDDEN_CHANNELS,
    NUM_RELATIONS,
    NUM_LAYERS,
    DROPOUT,
    BATCH_SIZE
)

from training.graph_loader import load_graph

from training.relation_neighbor_loader import (
    create_relation_neighbor_loader
)

from models.ja_gnn.model import JAGNN


DEVICE = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)


print("Device:", DEVICE)

print()
print("Loading graph...")

data, relation_edges, hybrid_edge_index, hybrid_scores = load_graph()


loader = create_relation_neighbor_loader(
    data,
    relation_edges,
    batch_size=BATCH_SIZE,
    num_neighbors=3
)


batch = next(iter(loader))

batch = batch.to(DEVICE)


print()
print("Batch nodes:", batch.x.shape)
print("Batch edges:", batch.edge_index.shape)


model = JAGNN(
    input_channels=INPUT_CHANNELS,
    hidden_channels=HIDDEN_CHANNELS,
    num_relations=NUM_RELATIONS,
    num_layers=NUM_LAYERS,
    dropout=DROPOUT
).to(DEVICE)


model.eval()


# ============================================================
# CREATE LOCAL MAPS
# ============================================================

node_type = batch.node_type

transaction_mask = (
    node_type == 0
)

attribute_mask = (
    node_type == 1
)


transaction_nodes = torch.where(
    transaction_mask
)[0]

attribute_nodes = torch.where(
    attribute_mask
)[0]


transaction_map = torch.full(
    (batch.x.shape[0],),
    -1,
    dtype=torch.long,
    device=DEVICE
)

attribute_map = torch.full(
    (batch.x.shape[0],),
    -1,
    dtype=torch.long,
    device=DEVICE
)


transaction_map[
    transaction_nodes
] = torch.arange(
    transaction_nodes.shape[0],
    device=DEVICE
)


attribute_map[
    attribute_nodes
] = torch.arange(
    attribute_nodes.shape[0],
    device=DEVICE
)


# ============================================================
# LOCAL RELATION EDGES
# ============================================================

local_relation_edges = []


for relation_index in range(
    NUM_RELATIONS
):

    relation_mask = (
        batch.edge_type == relation_index
    )

    edges = batch.edge_index[
        :,
        relation_mask
    ]

    local_relation_edges.append(
        edges
    )


# ============================================================
# RUN ACTUAL MODEL
# ============================================================

print()
print("=" * 60)
print("RUNNING ACTUAL JA-GNN MODEL")
print("=" * 60)


with torch.no_grad():

    logits = model(
        batch.x,
        local_relation_edges,
        transaction_map,
        attribute_map,
        torch.arange(
            batch.batch_size,
            device=DEVICE
        )
    )


# ============================================================
# RESULTS
# ============================================================

print()
print("=" * 60)
print("MODEL OUTPUT")
print("=" * 60)


print(
    "Logits shape:",
    logits.shape
)

print(
    "Logits mean:",
    logits.mean().item()
)

print(
    "Logits std:",
    logits.std().item()
)

print(
    "Logits min:",
    logits.min().item()
)

print(
    "Logits max:",
    logits.max().item()
)


probabilities = torch.sigmoid(
    logits
)


print()
print(
    "Probability mean:",
    probabilities.mean().item()
)

print(
    "Probability std:",
    probabilities.std().item()
)

print(
    "Probability min:",
    probabilities.min().item()
)

print(
    "Probability max:",
    probabilities.max().item()
)


print()
print(
    "NaN:",
    torch.isnan(logits).any().item()
)

print(
    "Inf:",
    torch.isinf(logits).any().item()
)


print()
print("=" * 60)
print("ACTUAL MODEL TEST COMPLETE")
print("=" * 60)