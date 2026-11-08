import os
import sys

import torch


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

sys.path.insert(
    0,
    PROJECT_ROOT
)


# ============================================================
# IMPORTS
# ============================================================

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


# ============================================================
# DEVICE
# ============================================================

DEVICE = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)

print()
print("Device:", DEVICE)


# ============================================================
# LOAD GRAPH
# ============================================================

print()
print("Loading graph...")

data, relation_edges, hybrid_edge_index, hybrid_scores = load_graph()


# ============================================================
# CREATE LOADER
# ============================================================

loader = create_relation_neighbor_loader(
    data,
    relation_edges,
    batch_size=BATCH_SIZE,
    num_neighbors=3
)


# ============================================================
# GET ONE BATCH
# ============================================================

batch = next(iter(loader))

batch = batch.to(DEVICE)

print()
print("Batch loaded")

print(
    "Batch nodes:",
    batch.x.shape
)

print(
    "Batch edges:",
    batch.edge_index.shape
)


# ============================================================
# CREATE MODEL
# ============================================================

model = JAGNN(
    input_channels=INPUT_CHANNELS,
    hidden_channels=HIDDEN_CHANNELS,
    num_relations=NUM_RELATIONS,
    num_layers=NUM_LAYERS,
    dropout=DROPOUT
)

model = model.to(DEVICE)

model.eval()


# ============================================================
# RAW FEATURES
# ============================================================

x = batch.x

node_type = batch.node_type

transaction_mask = (
    node_type == 0
)

attribute_mask = (
    node_type == 1
)

raw_transaction_x = x[
    transaction_mask
]

raw_attribute_x = x[
    attribute_mask
]


# ============================================================
# INPUT PROJECTION
# ============================================================

print()
print("=" * 60)
print("INPUT PROJECTION")
print("=" * 60)


# Find the model input projection.
if hasattr(
    model,
    "input_projection"
):

    transaction_x = model.input_projection(
        raw_transaction_x
    )

    attribute_x = model.input_projection(
        raw_attribute_x
    )

elif hasattr(
    model,
    "input_proj"
):

    transaction_x = model.input_proj(
        raw_transaction_x
    )

    attribute_x = model.input_proj(
        raw_attribute_x
    )

elif hasattr(
    model,
    "projection"
):

    transaction_x = model.projection(
        raw_transaction_x
    )

    attribute_x = model.projection(
        raw_attribute_x
    )

else:

    raise RuntimeError(
        "Could not find input projection "
        "inside JAGNN model."
    )


print(
    "Raw transaction features:",
    raw_transaction_x.shape
)

print(
    "Projected transaction features:",
    transaction_x.shape
)

print(
    "Raw attribute features:",
    raw_attribute_x.shape
)

print(
    "Projected attribute features:",
    attribute_x.shape
)

print(
    "Transaction projected std:",
    transaction_x.std().item()
)

print(
    "Attribute projected std:",
    attribute_x.std().item()
)


# ============================================================
# LOCAL NODE MAPS
# ============================================================

local_transaction_indices = torch.where(
    transaction_mask
)[0]

local_attribute_indices = torch.where(
    attribute_mask
)[0]


transaction_map = torch.full(
    (x.shape[0],),
    -1,
    dtype=torch.long,
    device=DEVICE
)

attribute_map = torch.full(
    (x.shape[0],),
    -1,
    dtype=torch.long,
    device=DEVICE
)


transaction_map[
    local_transaction_indices
] = torch.arange(
    transaction_x.shape[0],
    device=DEVICE
)

attribute_map[
    local_attribute_indices
] = torch.arange(
    attribute_x.shape[0],
    device=DEVICE
)


# ============================================================
# INITIAL REPRESENTATIONS
# ============================================================

print()
print("=" * 60)
print("INITIAL REPRESENTATIONS")
print("=" * 60)

print(
    "Transaction representation std:",
    transaction_x.std().item()
)

print(
    "Attribute representation std:",
    attribute_x.std().item()
)


# ============================================================
# JUMP REPRESENTATIONS
# ============================================================

jump_representations = []


# ============================================================
# LAYER LOOP
# ============================================================

for layer_index in range(NUM_LAYERS):

    print()
    print("=" * 60)
    print(
        "LAYER",
        layer_index + 1
    )
    print("=" * 60)


    # ========================================================
    # ATTRIBUTE UPDATE
    # ========================================================

    print()
    print("ATTRIBUTE UPDATE")

    relation_attribute_outputs = []


    for relation_index in range(NUM_RELATIONS):

        relation_mask = (
            batch.edge_type == relation_index
        )

        relation_edges = batch.edge_index[
            :,
            relation_mask
        ]


        if relation_edges.shape[1] == 0:

            continue


        source_nodes = relation_edges[0]

        target_nodes = relation_edges[1]


        # Transaction -> Attribute
        forward_mask = (
            (node_type[source_nodes] == 0)
            &
            (node_type[target_nodes] == 1)
        )

        forward_edges = relation_edges[
            :,
            forward_mask
        ]


        if forward_edges.shape[1] == 0:

            continue


        # ----------------------------------------------------
        # Convert to compact local indices
        # ----------------------------------------------------

        compact_source = transaction_map[
            forward_edges[0]
        ]

        compact_target = attribute_map[
            forward_edges[1]
        ]

        compact_edges = torch.stack(
            [
                compact_source,
                compact_target
            ],
            dim=0
        )


        # ----------------------------------------------------
        # Safety checks
        # ----------------------------------------------------

        if (
            compact_edges[0].min() < 0
            or
            compact_edges[0].max()
            >= transaction_x.shape[0]
        ):

            raise RuntimeError(
                "Invalid transaction index."
            )


        if (
            compact_edges[1].min() < 0
            or
            compact_edges[1].max()
            >= attribute_x.shape[0]
        ):

            raise RuntimeError(
                "Invalid attribute index."
            )


        print()
        print(
            "Relation",
            relation_index,
            "-",
            "Forward edges:",
            compact_edges.shape[1]
        )


        # ----------------------------------------------------
        # Attention
        # ----------------------------------------------------

        output = model.attribute_layers[
            layer_index
        ][
            relation_index
        ](
            transaction_x,
            attribute_x,
            compact_edges
        )


        relation_attribute_outputs.append(
            output
        )


        print(
            "Output std:",
            output.std().item()
        )


    # ========================================================
    # ATTRIBUTE AGGREGATION
    # ========================================================

    if len(
        relation_attribute_outputs
    ) == 0:

        raise RuntimeError(
            "No attribute outputs."
        )


    attribute_representation = torch.stack(
        relation_attribute_outputs,
        dim=0
    ).mean(
        dim=0
    )


    print()
    print(
        "Attribute representation std:",
        attribute_representation.std().item()
    )


    # ========================================================
    # TRANSACTION UPDATE
    # ========================================================

    print()
    print("TRANSACTION UPDATE")

    relation_transaction_outputs = []


    for relation_index in range(NUM_RELATIONS):

        relation_mask = (
            batch.edge_type == relation_index
        )

        relation_edges = batch.edge_index[
            :,
            relation_mask
        ]


        if relation_edges.shape[1] == 0:

            continue


        source_nodes = relation_edges[0]

        target_nodes = relation_edges[1]


        # Attribute -> Transaction
        reverse_mask = (
            (node_type[source_nodes] == 1)
            &
            (node_type[target_nodes] == 0)
        )

        reverse_edges = relation_edges[
            :,
            reverse_mask
        ]


        if reverse_edges.shape[1] == 0:

            continue


        # ----------------------------------------------------
        # Compact indices
        # ----------------------------------------------------

        compact_source = attribute_map[
            reverse_edges[0]
        ]

        compact_target = transaction_map[
            reverse_edges[1]
        ]

        compact_edges = torch.stack(
            [
                compact_source,
                compact_target
            ],
            dim=0
        )


        # ----------------------------------------------------
        # Safety checks
        # ----------------------------------------------------

        if (
            compact_edges[0].min() < 0
            or
            compact_edges[0].max()
            >= attribute_representation.shape[0]
        ):

            raise RuntimeError(
                "Invalid attribute index."
            )


        if (
            compact_edges[1].min() < 0
            or
            compact_edges[1].max()
            >= transaction_x.shape[0]
        ):

            raise RuntimeError(
                "Invalid transaction index."
            )


        print()
        print(
            "Relation",
            relation_index,
            "-",
            "Reverse edges:",
            compact_edges.shape[1]
        )


        # ----------------------------------------------------
        # Attention
        # ----------------------------------------------------

        output = model.transaction_layers[
            layer_index
        ][
            relation_index
        ](
            attribute_representation,
            transaction_x,
            compact_edges
        )


        relation_transaction_outputs.append(
            output
        )


        print(
            "Output std:",
            output.std().item()
        )


    # ========================================================
    # TRANSACTION AGGREGATION
    # ========================================================

    if len(
        relation_transaction_outputs
    ) == 0:

        raise RuntimeError(
            "No transaction outputs."
        )


    transaction_representation = torch.stack(
        relation_transaction_outputs,
        dim=0
    ).mean(
        dim=0
    )


    print()
    print(
        "Transaction representation std:",
        transaction_representation.std().item()
    )


    # ========================================================
    # JUMP
    # ========================================================

    jump_representations.append(
        transaction_representation
    )


    # ========================================================
    # NEXT LAYER
    # ========================================================

    transaction_x = transaction_representation

    attribute_x = attribute_representation


# ============================================================
# JUMP CONNECTION
# ============================================================

print()
print("=" * 60)
print("JUMP CONNECTION")
print("=" * 60)


jump_input = torch.cat(
    jump_representations,
    dim=1
)


print(
    "Jump input shape:",
    jump_input.shape
)

print(
    "Jump input std:",
    jump_input.std().item()
)


# ============================================================
# JUMP PROJECTION
# ============================================================

if hasattr(
    model,
    "jump_projection"
):

    jump_output = model.jump_projection(
        jump_input
    )

elif hasattr(
    model,
    "jump_linear"
):

    jump_output = model.jump_linear(
        jump_input
    )

else:

    jump_output = jump_input


print(
    "Jump output shape:",
    jump_output.shape
)

print(
    "Jump output std:",
    jump_output.std().item()
)


# ============================================================
# FINAL REPRESENTATION
# ============================================================

print()
print("=" * 60)
print("FINAL REPRESENTATION")
print("=" * 60)


final_input = torch.cat(
    [
        transaction_x,
        jump_output
    ],
    dim=1
)


print(
    "Final input shape:",
    final_input.shape
)

print(
    "Final input std:",
    final_input.std().item()
)


# ============================================================
# FINAL PROJECTION
# ============================================================

if hasattr(
    model,
    "final_projection"
):

    final_representation = model.final_projection(
        final_input
    )

elif hasattr(
    model,
    "final_linear"
):

    final_representation = model.final_linear(
        final_input
    )

else:

    final_representation = final_input


print(
    "Final representation shape:",
    final_representation.shape
)

print(
    "Final representation std:",
    final_representation.std().item()
)


# ============================================================
# CLASSIFIER
# ============================================================

print()
print("=" * 60)
print("LOGITS")
print("=" * 60)


if hasattr(
    model,
    "classifier"
):

    logits = model.classifier(
        final_representation
    ).squeeze(-1)

elif hasattr(
    model,
    "output_layer"
):

    logits = model.output_layer(
        final_representation
    ).squeeze(-1)

else:

    raise RuntimeError(
        "Classifier not found."
    )


# ============================================================
# TARGET LOGITS
# ============================================================

target_logits = logits[
    :batch.batch_size
]


print(
    "Total logits:",
    logits.shape
)

print(
    "Target logits:",
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


# ============================================================
# PROBABILITIES
# ============================================================

probabilities = torch.sigmoid(
    target_logits
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


# ============================================================
# LABELS
# ============================================================

target_labels = batch.y[
    :batch.batch_size
]


print()
print(
    "Fraud:",
    int(
        (target_labels == 1).sum()
    )
)

print(
    "Legitimate:",
    int(
        (target_labels == 0).sum()
    )
)

print(
    "Fraud ratio:",
    target_labels.float().mean().item()
)


# ============================================================
# PREDICTIONS
# ============================================================

predictions = (
    probabilities >= 0.5
).long()


print()
print(
    "Predicted fraud:",
    int(
        (predictions == 1).sum()
    )
)

print(
    "Predicted legitimate:",
    int(
        (predictions == 0).sum()
    )
)


# ============================================================
# NUMERICAL CHECK
# ============================================================

print()
print("=" * 60)
print("NUMERICAL CHECK")
print("=" * 60)


if torch.isnan(
    logits
).any():

    print(
        "WARNING: NaN detected."
    )

else:

    print(
        "No NaN detected."
    )


if torch.isinf(
    logits
).any():

    print(
        "WARNING: Inf detected."
    )

else:

    print(
        "No Inf detected."
    )


# ============================================================
# FINAL COLLAPSE CHECK
# ============================================================

print()

if target_logits.std().item() < 0.01:

    print(
        "WARNING: Very low logit variance."
    )

    print(
        "The model may be suffering from "
        "representation/logit collapse."
    )

else:

    print(
        "Logit variance looks reasonable."
    )


print()
print("=" * 60)
print("DEBUG COMPLETE")
print("=" * 60)