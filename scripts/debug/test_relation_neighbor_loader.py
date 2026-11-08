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

from training.graph_loader import load_graph
from training.relation_neighbor_loader import (
    create_relation_neighbor_loader
)


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


print("\nLoading one batch...")

batch = next(iter(loader))

print(
    "Batch nodes:",
    batch.x.shape
)

print(
    "Batch edges:",
    batch.edge_index.shape
)

print(
    "Edge type:",
    batch.edge_type.shape
)

print(
    "Node type:",
    batch.node_type.shape
)

print(
    "Target nodes:",
    batch.batch_size
)

print(
    "Transaction nodes:",
    int(
        (batch.node_type == 0).sum()
    )
)

print(
    "Attribute nodes:",
    int(
        (batch.node_type == 1).sum()
    )
)

print(
    "Target node labels:",
    batch.y[:batch.batch_size].shape
)

print("\nNode type check passed.")