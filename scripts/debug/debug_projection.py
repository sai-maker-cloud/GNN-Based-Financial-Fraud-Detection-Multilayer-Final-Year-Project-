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


with torch.no_grad():

    x = model.input_projection(
        batch.x
    )

    x = torch.relu(x)

    attribute_outputs = []

    for relation_index in range(12):

        mask = (
            batch.edge_type == relation_index
        )

        relation_edges = (
            batch.edge_index[:, mask]
        )

        source = relation_edges[0]
        target = relation_edges[1]

        valid = (
            (batch.node_type[source] == 0)
            &
            (batch.node_type[target] == 1)
        )

        relation_edges = (
            relation_edges[:, valid]
        )

        if relation_edges.shape[1] == 0:

            output = torch.zeros_like(x)

        else:

            output = (
                model.attribute_layers[0][
                    relation_index
                ](
                    x,
                    relation_edges
                )
            )

        attribute_outputs.append(output)

        print(
            "Relation",
            relation_index,
            "std:",
            output.std().item()
        )

    combined = torch.cat(
        attribute_outputs,
        dim=1
    )

    print(
        "\nCombined relation tensor shape:",
        combined.shape
    )

    print(
        "Combined std:",
        combined.std().item()
    )

    projected = model.relation_projection(
        combined
    )

    print(
        "Projected std:",
        projected.std().item()
    )

    projected = torch.relu(
        projected
    )

    print(
        "Projected ReLU std:",
        projected.std().item()
    )

    target_nodes = (
        batch.node_type == 1
    )

    print(
        "\nAttribute target std:",
        projected[target_nodes].std().item()
    )