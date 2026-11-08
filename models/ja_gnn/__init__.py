"""
Jump-Attentive Graph Neural Network (JA-GNN) Package.
Implements multi-relation attention and jump-knowledge pooling for camouflage fraud detection.
"""

from models.ja_gnn.model import JAGNN
from models.ja_gnn.attention import RelationAttention
from models.ja_gnn.hybrid_attention import HybridAttention

__all__ = [
    "JAGNN",
    "RelationAttention",
    "HybridAttention",
]
