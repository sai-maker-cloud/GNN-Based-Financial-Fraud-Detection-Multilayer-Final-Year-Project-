import numpy as np
import pandas as pd
import torch

from torch_geometric.data import Data


FEATURE_FILE = "data/processed/scaled/train_scaled.csv"
LABEL_FILE = "data/processed/train_labels.csv"
GRAPH_FILE = "data/graphs/bipartite/train_edges.npz"
SAMPLED_FILE = "data/graphs/sampled/hybrid_edges.npz"


def load_graph():

    print("Loading features...")

    transaction_features = pd.read_csv(
        FEATURE_FILE
    ).values.astype(np.float32)

    num_transactions = transaction_features.shape[0]

    print(
        "Transactions:",
        num_transactions
    )

    print(
        "Features:",
        transaction_features.shape
    )


    print("\nLoading labels...")

    labels = pd.read_csv(
        LABEL_FILE
    ).values.squeeze().astype(np.float32)

    print(
        "Labels:",
        labels.shape
    )

    print(
        "Fraud:",
        int(labels.sum())
    )

    print(
        "Legitimate:",
        int((labels == 0).sum())
    )


    print("\nLoading bipartite graph...")

    graph = np.load(
        GRAPH_FILE
    )

    source = graph["source"]
    target = graph["target"]
    relation = graph["relation"]


    num_attribute_nodes = (
        int(target.max())
        - num_transactions
        + 1
    )

    num_nodes = (
        num_transactions
        + num_attribute_nodes
    )


    print(
        "Attribute nodes:",
        num_attribute_nodes
    )

    print(
        "Total nodes:",
        num_nodes
    )


    print("\nCreating attribute node features...")


    attribute_features = np.zeros(
        (
            num_attribute_nodes,
            transaction_features.shape[1]
        ),
        dtype=np.float32
    )


    attribute_counts = np.zeros(
        num_attribute_nodes,
        dtype=np.int32
    )


    for transaction, attribute in zip(
        source,
        target
    ):

        attribute_index = (
            attribute -
            num_transactions
        )


        attribute_features[
            attribute_index
        ] += transaction_features[
            transaction
        ]


        attribute_counts[
            attribute_index
        ] += 1


    valid_attributes = (
        attribute_counts > 0
    )


    attribute_features[
        valid_attributes
    ] /= attribute_counts[
        valid_attributes,
        None
    ]


    print(
        "Attribute features created:",
        attribute_features.shape
    )

    print(
        "Attributes with transactions:",
        int(valid_attributes.sum())
    )


    print("\nCreating node feature matrix...")


    features = np.vstack(
        [
            transaction_features,
            attribute_features
        ]
    )


    print(
        "Node feature matrix:",
        features.shape
    )


    print("\nCreating bidirectional relation edges...")


    relation_edges = []


    for relation_index in range(12):

        mask = (
            relation == relation_index
        )


        relation_source = source[mask]

        relation_target = target[mask]


        # Transaction -> Attribute

        forward_edges = np.vstack(
            [
                relation_source,
                relation_target
            ]
        )


        # Attribute -> Transaction

        reverse_edges = np.vstack(
            [
                relation_target,
                relation_source
            ]
        )


        # Combine both directions

        edge_index = np.hstack(
            [
                forward_edges,
                reverse_edges
            ]
        )


        edge_index = torch.tensor(
            edge_index,
            dtype=torch.long
        )


        relation_edges.append(
            edge_index
        )


        print(
            "Relation",
            relation_index,
            "edges:",
            edge_index.shape[1]
        )


    print("\nLoading hybrid sampled edges...")


    sampled = np.load(
        SAMPLED_FILE
    )


    hybrid_source = sampled["source"]

    hybrid_target = sampled["target"]

    hybrid_score = sampled["score"]


    hybrid_edge_index = torch.tensor(
        np.vstack(
            [
                hybrid_source,
                hybrid_target
            ]
        ),
        dtype=torch.long
    )


    hybrid_scores = torch.tensor(
        hybrid_score,
        dtype=torch.float32
    )


    print(
        "Hybrid edges:",
        hybrid_edge_index.shape[1]
    )

    print(
        "Hybrid scores:",
        hybrid_scores.shape
    )


    # Pad labels to num_nodes so PyG NeighborLoader recognizes y as a node-level
    # attribute aligned with data.num_nodes and slices batch.y correctly for each batch
    full_labels = torch.full(
        (num_nodes,),
        -1.0,
        dtype=torch.float32
    )
    full_labels[:num_transactions] = torch.tensor(
        labels,
        dtype=torch.float32
    )

    data = Data(
        x=torch.tensor(
            features,
            dtype=torch.float32
        ),
        y=full_labels
    )
    data.num_transactions = num_transactions


    return (
        data,
        relation_edges,
        hybrid_edge_index,
        hybrid_scores
    )