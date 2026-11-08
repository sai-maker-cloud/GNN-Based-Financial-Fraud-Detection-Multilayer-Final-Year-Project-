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


print("\nCreating loader...")

loader = create_relation_neighbor_loader(
    data,
    relation_edges,
    batch_size=1024,
    num_neighbors=3
)


print("\nLoading one batch...")

batch = next(iter(loader))


device = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)

print(
    "\nDevice:",
    device
)


batch = batch.to(device)


model = JAGNN(
    input_channels=21,
    hidden_channels=128,
    num_relations=12,
    num_layers=3,
    dropout=0.5,
    num_transactions=210000
).to(device)


model.eval()


print("\nRunning model...")

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


print("\n========== MODEL DIAGNOSTICS ==========")

print(
    "Total logits:",
    logits.shape
)

print(
    "Target logits:",
    target_logits.shape
)

print(
    "Logit mean:",
    target_logits.mean().item()
)

print(
    "Logit std:",
    target_logits.std().item()
)

print(
    "Logit min:",
    target_logits.min().item()
)

print(
    "Logit max:",
    target_logits.max().item()
)


probabilities = torch.sigmoid(
    target_logits
)


print("\n========== PROBABILITY DIAGNOSTICS ==========")

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


print("\n========== LABEL DISTRIBUTION ==========")

labels = batch.y[
    :batch.batch_size
].float()


print(
    "Fraud:",
    int(labels.sum().item())
)

print(
    "Legitimate:",
    int((labels == 0).sum().item())
)

print(
    "Fraud ratio:",
    labels.mean().item()
)


print("\n========== PREDICTION DISTRIBUTION ==========")

predictions = (
    probabilities >= 0.5
).long()


print(
    "Predicted fraud:",
    int(predictions.sum().item())
)

print(
    "Predicted legitimate:",
    int((predictions == 0).sum().item())
)


print("\n========== PARAMETER DIAGNOSTICS ==========")

total_parameters = 0
nonzero_gradients = 0

for name, parameter in model.named_parameters():

    parameter_count = parameter.numel()

    total_parameters += parameter_count

    print(
        name,
        "| shape:",
        tuple(parameter.shape),
        "| mean:",
        parameter.mean().item(),
        "| std:",
        parameter.std().item()
    )


print(
    "\nTotal parameters:",
    total_parameters
)


print("\n========== FORWARD CHECK ==========")

if torch.isnan(logits).any():

    print("ERROR: NaN detected in logits")

elif torch.isinf(logits).any():

    print("ERROR: Inf detected in logits")

else:

    print("No NaN or Inf detected.")


if target_logits.std().item() < 0.001:

    print(
        "WARNING: Very low logit variance."
    )

    print(
        "The model may be suffering from"
        " representation/logit collapse."
    )

else:

    print(
        "Logit variance looks non-collapsed."
    )


print("\nDiagnostic complete.")