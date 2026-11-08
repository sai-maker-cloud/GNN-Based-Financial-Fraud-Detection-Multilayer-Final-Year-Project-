import torch
import torch.nn as nn
import torch.nn.functional as F

from torch_geometric.utils import softmax


class RelationAttention(nn.Module):

    def __init__(
        self,
        in_channels,
        out_channels,
        dropout=0.5
    ):
        super().__init__()

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

        self.dropout = nn.Dropout(
            dropout
        )

    def forward(
        self,
        source_x,
        target_x,
        edge_index,
        edge_weight=None
    ):

        source = edge_index[0]
        target = edge_index[1]

        # ==========================================================
        # INDEX VALIDATION
        # ==========================================================

        if edge_index.dim() != 2:
            raise RuntimeError(
                f"edge_index must have 2 dimensions, "
                f"got {edge_index.shape}"
            )

        if edge_index.shape[0] != 2:
            raise RuntimeError(
                f"edge_index must have shape [2, E], "
                f"got {edge_index.shape}"
            )

        if source.numel() > 0:

            source_min = source.min().item()
            source_max = source.max().item()

            target_min = target.min().item()
            target_max = target.max().item()

            source_nodes = source_x.shape[0]
            target_nodes = target_x.shape[0]

            if source_min < 0 or source_max >= source_nodes:

                raise RuntimeError(
                    "\n"
                    "==================================================\n"
                    "INVALID SOURCE INDEX\n"
                    "==================================================\n"
                    f"Source minimum : {source_min}\n"
                    f"Source maximum : {source_max}\n"
                    f"Source nodes   : {source_nodes}\n"
                    f"source_x shape : {source_x.shape}\n"
                    f"edge_index     : {edge_index.shape}\n"
                    "==================================================\n"
                )

            if target_min < 0 or target_max >= target_nodes:

                raise RuntimeError(
                    "\n"
                    "==================================================\n"
                    "INVALID TARGET INDEX\n"
                    "==================================================\n"
                    f"Target minimum : {target_min}\n"
                    f"Target maximum : {target_max}\n"
                    f"Target nodes   : {target_nodes}\n"
                    f"target_x shape : {target_x.shape}\n"
                    f"edge_index     : {edge_index.shape}\n"
                    "==================================================\n"
                )

        # ==========================================================
        # LINEAR TRANSFORMATION
        # ==========================================================

        source_transformed = self.linear(
            source_x
        )

        target_transformed = self.linear(
            target_x
        )

        # ==========================================================
        # EDGE FEATURE GATHER
        # ==========================================================

        source_features = (
            source_transformed[source]
        )

        target_features = (
            target_transformed[target]
        )

        # ==========================================================
        # ATTENTION INPUT
        # ==========================================================

        attention_input = torch.cat(
            [
                source_features,
                target_features
            ],
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
        # EDGE WEIGHT
        # ==========================================================

        if edge_weight is not None:

            if edge_weight.shape[0] != edge_index.shape[1]:

                raise RuntimeError(
                    "\n"
                    "==================================================\n"
                    "INVALID EDGE WEIGHT SIZE\n"
                    "==================================================\n"
                    f"Edge weights : {edge_weight.shape}\n"
                    f"Edges        : {edge_index.shape}\n"
                    "==================================================\n"
                )

            edge_weight = edge_weight.clamp(
                min=1e-6
            )

            attention_scores = (
                attention_scores
                +
                torch.log(edge_weight)
            )

        # ==========================================================
        # ATTENTION SOFTMAX
        # ==========================================================

        attention_weights = softmax(
            attention_scores,
            target,
            num_nodes=target_x.shape[0]
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

        output = torch.zeros_like(
            target_transformed
        )

        output.index_add_(
            0,
            target,
            messages
        )

        return output