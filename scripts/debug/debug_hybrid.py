import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import torch
from training.graph_loader import load_graph
from training.relation_neighbor_loader import create_relation_neighbor_loader, HYBRID_EDGE_TYPE
from training.train_ja_gnn import create_local_relation_edges, create_local_hybrid_edges, create_local_maps
from models.ja_gnn.model import JAGNN

def debug():
    data, relation_edges, hybrid_edge_index, hybrid_scores = load_graph()
    print("Loaded graph.")
    
    loader = create_relation_neighbor_loader(
        data,
        relation_edges,
        hybrid_edge_index=hybrid_edge_index,
        hybrid_scores=hybrid_scores,
        batch_size=1024,
        num_neighbors=3,
        shuffle=True
    )
    
    for batch in loader:
        print("\n--- NEW BATCH ---")
        print("batch.x shape:", batch.x.shape)
        print("batch.batch_size:", batch.batch_size)
        print("batch.edge_index shape:", batch.edge_index.shape)
        print("batch.edge_type unique:", torch.unique(batch.edge_type))
        
        hybrid_mask = (batch.edge_type == HYBRID_EDGE_TYPE)
        print("Hybrid edge count in batch:", hybrid_mask.sum().item())
        
        local_hybrid_edges, local_hybrid_weight = create_local_hybrid_edges(batch)
        if local_hybrid_edges is not None:
            print("local_hybrid_edges shape:", local_hybrid_edges.shape)
            if local_hybrid_weight is not None:
                print("local_hybrid_weight shape:", local_hybrid_weight.shape)
                print("Weight sample min/max/mean:", local_hybrid_weight.min().item(), local_hybrid_weight.max().item(), local_hybrid_weight.mean().item())
        else:
            print("local_hybrid_edges IS NONE!")
            
        transaction_map, attribute_map, transaction_indices = create_local_maps(batch)
        print("transaction_nodes in batch:", (transaction_map >= 0).sum().item())
        print("attribute_nodes in batch:", (attribute_map >= 0).sum().item())
        
        # Test forward pass with model
        model = JAGNN(input_channels=21, hidden_channels=128, num_relations=12, num_layers=3)
        local_relation_edges = create_local_relation_edges(batch)
        
        logits = model(
            batch.x,
            local_relation_edges,
            transaction_map,
            attribute_map,
            transaction_indices,
            hybrid_edge_index=local_hybrid_edges,
            hybrid_edge_weight=local_hybrid_weight
        )
        print("logits shape:", logits.shape)
        print("logits sample min/max/std:", logits.min().item(), logits.max().item(), logits.std().item())
        break

if __name__ == "__main__":
    debug()
