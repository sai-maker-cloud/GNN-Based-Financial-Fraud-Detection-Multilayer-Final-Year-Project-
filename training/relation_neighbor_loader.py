import torch

from torch_geometric.loader import NeighborLoader
from torch_geometric.data import Data


# Edge type 12 is reserved for hybrid transaction-to-transaction edges.
# Types 0-11 are bipartite relation edges.
HYBRID_EDGE_TYPE = 12


def create_relation_neighbor_loader(
    data,
    relation_edges,
    hybrid_edge_index=None,
    hybrid_scores=None,
    input_nodes=None,
    batch_size=1024,
    num_neighbors=15,
    num_layers=2,
    shuffle=True
):
    """
    Create a NeighborLoader with both bipartite relation edges
    and hybrid transaction-to-transaction similarity edges.

    The unified graph allows the NeighborLoader to sample
    neighbors from BOTH pathways, ensuring each mini-batch
    contains edges for both the bipartite and hybrid pathways.

    Args:
        data: PyG Data object with x (features) and y (labels)
        relation_edges: list of 12 [2, E_r] bipartite edge tensors
        hybrid_edge_index: [2, E_h] hybrid txn-txn edges (optional)
        hybrid_scores: [E_h] hybrid similarity scores (optional)
        batch_size: number of target nodes per batch
        num_neighbors: neighbors to sample per node per layer
        num_layers: number of GNN layers (determines sampling depth)
    """

    print("Creating relation-aware graph...")

    all_edges = []
    all_relations = []

    for relation_index, edge_index in enumerate(
        relation_edges
    ):

        number_of_edges = edge_index.shape[1]

        relation_tensor = torch.full(
            (number_of_edges,),
            relation_index,
            dtype=torch.long
        )

        all_edges.append(edge_index)
        all_relations.append(relation_tensor)

    # Combine bipartite edges
    combined_edges = torch.cat(
        all_edges,
        dim=1
    )

    combined_relations = torch.cat(
        all_relations,
        dim=0
    )

    # Edge weights: 1.0 for bipartite edges
    num_bipartite = combined_edges.shape[1]

    edge_weight = torch.ones(
        num_bipartite,
        dtype=torch.float32
    )

    # Add hybrid edges if provided
    if hybrid_edge_index is not None:

        num_hybrid = hybrid_edge_index.shape[1]

        print(
            f"Adding {num_hybrid} hybrid edges "
            f"(type {HYBRID_EDGE_TYPE})..."
        )

        hybrid_type = torch.full(
            (num_hybrid,),
            HYBRID_EDGE_TYPE,
            dtype=torch.long
        )

        combined_edges = torch.cat(
            [combined_edges, hybrid_edge_index],
            dim=1
        )

        combined_relations = torch.cat(
            [combined_relations, hybrid_type],
            dim=0
        )

        if hybrid_scores is not None:
            edge_weight = torch.cat(
                [edge_weight, hybrid_scores],
                dim=0
            )
        else:
            edge_weight = torch.cat(
                [
                    edge_weight,
                    torch.ones(
                        num_hybrid,
                        dtype=torch.float32
                    )
                ],
                dim=0
            )

    num_nodes = data.x.shape[0]
    num_transactions = getattr(data, "num_transactions", 210000)

    node_type = torch.ones(
        num_nodes,
        dtype=torch.long
    )

    node_type[:num_transactions] = 0

    graph = Data(
        x=data.x,
        y=data.y,
        edge_index=combined_edges,
        edge_type=combined_relations,
        edge_weight=edge_weight,
        node_type=node_type
    )

    if input_nodes is None:
        input_nodes = torch.arange(
            num_transactions,
            dtype=torch.long
        )

    loader = NeighborLoader(
        graph,
        input_nodes=input_nodes,
        num_neighbors=[num_neighbors] * num_layers,
        batch_size=batch_size,
        shuffle=shuffle
    )

    print("Total nodes:", graph.num_nodes)

    print(
        "Transaction nodes:",
        int((node_type == 0).sum())
    )

    print(
        "Attribute nodes:",
        int((node_type == 1).sum())
    )

    print(
        "Total edges:",
        graph.edge_index.shape[1]
    )

    print(
        "Bipartite edges:",
        num_bipartite
    )

    if hybrid_edge_index is not None:
        print(
            "Hybrid edges:",
            num_hybrid
        )

    print(
        "Relations:",
        len(relation_edges)
    )

    print(
        "Input nodes:",
        input_nodes.shape[0]
    )

    print(
        "Batch size:",
        batch_size
    )

    print(
        "Neighbors per layer:",
        num_neighbors
    )

    return loader