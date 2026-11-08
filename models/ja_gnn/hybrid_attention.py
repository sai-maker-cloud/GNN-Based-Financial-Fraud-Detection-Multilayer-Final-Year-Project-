import torch
import torch.nn as nn
import torch.nn.functional as F

from torch_geometric.utils import softmax


class HybridAttention(nn.Module):
    """
    Transaction-to-transaction attention with edge weight bias.

    Implements the similarity-aware message passing pathway
    for the hybrid JA-GNN architecture.

    The attention mechanism combines learned attention scores
    with pre-computed hybrid similarity scores (WMNC + Mahalanobis):

        e_ij = LeakyReLU(a^T [Wh_i || Wh_j])
        e_ij = e_ij + log(w_ij + epsilon)
        alpha_ij = softmax_j(e_ij)
        h_i' = sum_j (alpha_ij * Wh_j)

    This allows the model to leverage structural similarity
    (WMNC) and feature similarity (Mahalanobis) while learning
    task-specific attention patterns.

    Research principle:
        The log(weight) bias ensures that structurally and
        feature-wise similar transactions (high WMNC + low
        Mahalanobis distance) receive higher attention, while
        still allowing the model to learn task-specific
        adjustments through the learned attention parameters.
    """

    def __init__(
        self,
        in_channels,
        out_channels,
        dropout=0.5
    ):
        super().__init__()

        self.in_channels = in_channels
        self.out_channels = out_channels

        self.linear = nn.Linear(
            in_channels,
            out_channels,
            bias=False
        )

        self.attention = nn.Linear(
            out_channels * 2,
            1,
            bias=False
        )

        self.dropout = nn.Dropout(dropout)

    def forward(
        self,
        x,
        edge_index,
        edge_weight=None
    ):
        """
        Args:
            x: Transaction features [N_txn, in_channels]
            edge_index: [2, E] transaction-to-transaction edges
                        (compact transaction indices)
            edge_weight: [E] hybrid similarity scores (optional)

        Returns:
            output: [N_txn, out_channels] updated features
        """

        # ==========================================================
        # HANDLE EMPTY EDGES
        # ==========================================================

        if edge_index.shape[1] == 0:

            return torch.zeros(
                x.shape[0],
                self.out_channels,
                device=x.device,
                dtype=x.dtype
            )

        source = edge_index[0]
        target = edge_index[1]

        # ==========================================================
        # INDEX VALIDATION
        # ==========================================================

        if source.numel() > 0:

            source_min = source.min().item()
            source_max = source.max().item()
            target_min = target.min().item()
            target_max = target.max().item()
            num_nodes = x.shape[0]

            if source_min < 0 or source_max >= num_nodes:

                raise RuntimeError(
                    "\n"
                    "==================================================\n"
                    "INVALID HYBRID SOURCE INDEX\n"
                    "==================================================\n"
                    f"Source minimum : {source_min}\n"
                    f"Source maximum : {source_max}\n"
                    f"Num nodes     : {num_nodes}\n"
                    f"x shape       : {x.shape}\n"
                    f"edge_index    : {edge_index.shape}\n"
                    "==================================================\n"
                )

            if target_min < 0 or target_max >= num_nodes:

                raise RuntimeError(
                    "\n"
                    "==================================================\n"
                    "INVALID HYBRID TARGET INDEX\n"
                    "==================================================\n"
                    f"Target minimum : {target_min}\n"
                    f"Target maximum : {target_max}\n"
                    f"Num nodes      : {num_nodes}\n"
                    f"x shape        : {x.shape}\n"
                    f"edge_index     : {edge_index.shape}\n"
                    "==================================================\n"
                )

        # ==========================================================
        # LINEAR TRANSFORMATION
        # ==========================================================

        x_transformed = self.linear(x)

        # ==========================================================
        # EDGE FEATURE GATHER
        # ==========================================================

        source_features = x_transformed[source]
        target_features = x_transformed[target]

        # ==========================================================
        # ATTENTION SCORES
        # ==========================================================

        attention_input = torch.cat(
            [source_features, target_features],
            dim=1
        )

        attention_scores = self.attention(
            attention_input
        ).squeeze(-1)

        attention_scores = F.leaky_relu(
            attention_scores,
            negative_slope=0.2
        )

        # ==========================================================
        # EDGE WEIGHT BIAS
        #
        # log(w + epsilon) bias:
        #   w ~ 1.0  =>  bias ~ 0     (high similarity, no penalty)
        #   w ~ 0.0  =>  bias ~ -13.8 (low similarity, strong penalty)
        #
        # This allows pre-computed similarity to modulate
        # the learned attention without dominating it.
        # ==========================================================

        if edge_weight is not None:

            if edge_weight.shape[0] != edge_index.shape[1]:

                raise RuntimeError(
                    "\n"
                    "==================================================\n"
                    "INVALID HYBRID EDGE WEIGHT SIZE\n"
                    "==================================================\n"
                    f"Edge weights : {edge_weight.shape}\n"
                    f"Edges        : {edge_index.shape}\n"
                    "==================================================\n"
                )

            edge_weight_clamped = edge_weight.clamp(
                min=1e-6
            )

            attention_scores = (
                attention_scores
                +
                torch.log(edge_weight_clamped)
            )

        # ==========================================================
        # ATTENTION SOFTMAX
        # ==========================================================

        attention_weights = softmax(
            attention_scores,
            target,
            num_nodes=x.shape[0]
        )

        if self.training and self.dropout.p > 0:
            attention_weights = F.dropout(
                attention_weights,
                p=min(self.dropout.p, 0.1),
                training=True
            )

        # ==========================================================
        # MESSAGE PASSING
        # ==========================================================

        messages = (
            source_features
            *
            attention_weights.unsqueeze(-1)
        )

        # ==========================================================
        # AGGREGATION
        # ==========================================================

        output = torch.zeros_like(x_transformed)

        output.index_add_(
            0,
            target,
            messages
        )

        return output
