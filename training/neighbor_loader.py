import torch

from torch_geometric.loader import NeighborLoader
from torch_geometric.data import Data


def create_neighbor_loader(
    data,
    relation_edges,
    batch_size=2048,
    num_neighbors=5
):

    print("Creating combined graph...")

    all_edges = []

    for edge_index in relation_edges:

        all_edges.append(
            edge_index
        )


    edge_index = torch.cat(
        all_edges,
        dim=1
    )


    graph = Data(
        x=data.x,
        y=data.y,
        edge_index=edge_index
    )


    # Only transaction nodes have labels.
    # Transaction nodes are 0 ... 209999.

    train_nodes = torch.arange(
        data.y.shape[0],
        dtype=torch.long
    )


    loader = NeighborLoader(
        graph,
        input_nodes=train_nodes,
        num_neighbors=[
            num_neighbors,
            num_neighbors,
            num_neighbors
        ],
        batch_size=batch_size,
        shuffle=True
    )


    print(
        "Total graph nodes:",
        graph.num_nodes
    )

    print(
        "Total graph edges:",
        graph.edge_index.shape[1]
    )

    print(
        "Training nodes:",
        train_nodes.shape[0]
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


if __name__ == "__main__":

    from graph_loader import load_graph


    print(
        "========== LOADING GRAPH =========="
    )


    data, relation_edges, _, _ = load_graph()


    print(
        "\n========== CREATING NEIGHBOR LOADER =========="
    )


    loader = create_neighbor_loader(
        data,
        relation_edges,
        batch_size=2048,
        num_neighbors=5
    )


    print(
        "\n========== TESTING FIRST BATCH =========="
    )


    batch = next(
        iter(loader)
    )


    print(
        "Batch nodes:",
        batch.x.shape
    )

    print(
        "Batch edges:",
        batch.edge_index.shape
    )

    print(
        "Batch size:",
        batch.batch_size
    )


    print(
        "\n========== FIRST BATCH SUCCESS =========="
    )

    print(
        "Target transactions:",
        batch.batch_size
    )

    print(
        "Sampled nodes:",
        batch.x.shape[0]
    )

    print(
        "Sampled edges:",
        batch.edge_index.shape[1]
    )