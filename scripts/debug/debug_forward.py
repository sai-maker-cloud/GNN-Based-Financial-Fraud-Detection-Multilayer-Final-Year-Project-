import os
import sys

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

sys.path.insert(
    0,
    PROJECT_ROOT
)

import torch

from training.graph_loader import load_graph
from training.relation_neighbor_loader import (
    create_relation_neighbor_loader
)
from models.ja_gnn.model import JAGNN


print("Loading graph...")

(
    data,
    relation_edges,
    hybrid_edge_index,
    hybrid_scores
) = load_graph()


loader = create_relation_neighbor_loader(
    data,
    relation_edges,
    batch_size=1024,
    num_neighbors=3
)


batch = next(iter(loader))


device = torch.device(
    "cuda" if torch.cuda.is_available()
    else "cpu"
)

batch = batch.to(device)


model = JAGNN(
    input_channels=21,
    hidden_channels=128,
    num_relations=12,
    num_layers=3,
    dropout=0.5,
    num_transactions=210000
)

model = model.to(device)

model.eval()


print("\nRunning full forward pass...")


with torch.no_grad():

    logits = model(
        batch.x,
        batch.edge_index,
        batch.edge_type,
        batch.node_type
    )


target_logits = logits[
    :batch.batch_size
]


print(
    "\nLogits shape:",
    logits.shape
)

print(
    "Target logits shape:",
    target_logits.shape
)

print(
    "Target logits mean:",
    target_logits.mean().item()
)

print(
    "Target logits std:",
    target_logits.std().item()
)

print(
    "Target logits min:",
    target_logits.min().item()
)

print(
    "Target logits max:",
    target_logits.max().item()
)

print(
    "\nTarget labels mean:",
    batch.y[
        :batch.batch_size
    ].float().mean().item()
)

print(
    "Forward pass successful."
)