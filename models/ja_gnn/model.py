import torch
import torch.nn as nn
import torch.nn.functional as F

from models.ja_gnn.attention import RelationAttention
from models.ja_gnn.hybrid_attention import HybridAttention


class JAGNN(nn.Module):
    """
    Jump-Attentive Graph Neural Network with Hybrid Pathways.

    Architecture:

    PATH A - Relation-aware bipartite attention:
        Transaction -> Attribute -> Transaction
        via 12 relation-specific attention layers.

    PATH B - Similarity-aware transaction attention:
        Transaction -> Transaction
        via hybrid sampled neighbors with edge weight bias
        from WMNC + Mahalanobis similarity scores.

    Combined with attention-based jump connections across layers.

    Reference:
        Inspired by "Jump-Attentive Graph Learning for
        Camouflaged Financial Fraud in Transaction Networks"
        by Priyanka Muppuri (IEEE IATMSI 2026).
    """

    def __init__(
        self,
        input_channels=21,
        hidden_channels=128,
        num_relations=12,
        num_layers=3,
        dropout=0.5
    ):
        super().__init__()

        self.input_channels = input_channels
        self.hidden_channels = hidden_channels
        self.num_relations = num_relations
        self.num_layers = num_layers
        self.dropout_rate = dropout

        # ==========================================================
        # INPUT PROJECTION
        # ==========================================================

        self.input_projection = nn.Linear(
            input_channels,
            hidden_channels
        )

        # ==========================================================
        # PATH A: BIPARTITE RELATION ATTENTION
        # ==========================================================

        # Transaction -> Attribute attention (per layer, per relation)
        self.attribute_layers = nn.ModuleList()

        # Attribute -> Transaction attention (per layer, per relation)
        self.transaction_layers = nn.ModuleList()

        for _ in range(num_layers):

            attribute_relation_layers = nn.ModuleList()
            transaction_relation_layers = nn.ModuleList()

            for _ in range(num_relations):

                attribute_relation_layers.append(
                    RelationAttention(
                        hidden_channels,
                        hidden_channels,
                        dropout
                    )
                )

                transaction_relation_layers.append(
                    RelationAttention(
                        hidden_channels,
                        hidden_channels,
                        dropout
                    )
                )

            self.attribute_layers.append(
                attribute_relation_layers
            )

            self.transaction_layers.append(
                transaction_relation_layers
            )

        # Shared relation aggregation projections
        self.attribute_relation_projection = nn.Linear(
            hidden_channels,
            hidden_channels
        )

        self.transaction_relation_projection = nn.Linear(
            hidden_channels,
            hidden_channels
        )

        # ==========================================================
        # PATH B: HYBRID SIMILARITY ATTENTION
        # Transaction -> Transaction via similarity-sampled edges
        # ==========================================================

        self.hybrid_layers = nn.ModuleList([
            HybridAttention(
                hidden_channels,
                hidden_channels,
                dropout
            )
            for _ in range(num_layers)
        ])

        # ==========================================================
        # PATHWAY COMBINATION
        # Per-layer projection: concat(bipartite, hybrid) -> hidden
        # ==========================================================

        self.combine_projections = nn.ModuleList([
            nn.Linear(
                hidden_channels * 2,
                hidden_channels
            )
            for _ in range(num_layers)
        ])

        # ==========================================================
        # NORMALIZATION
        # ==========================================================

        self.attribute_norms = nn.ModuleList()
        self.transaction_norms = nn.ModuleList()

        for _ in range(num_layers):

            self.attribute_norms.append(
                nn.LayerNorm(hidden_channels)
            )

            self.transaction_norms.append(
                nn.LayerNorm(hidden_channels)
            )

        # ==========================================================
        # JUMP ATTENTION
        # Attention-weighted aggregation across layers,
        # replacing simple concatenation + projection.
        # ==========================================================

        self.jump_attention_layer = nn.Linear(
            hidden_channels,
            1
        )

        # ==========================================================
        # FINAL PROJECTION & CLASSIFIER
        # ==========================================================

        self.final_projection = nn.Linear(
            hidden_channels * 2,
            hidden_channels
        )

        self.final_norm = nn.LayerNorm(
            hidden_channels
        )

        self.classifier = nn.Linear(
            hidden_channels,
            1
        )

        self.dropout = nn.Dropout(dropout)

        # Initialize classifier bias to log-prior log(0.15/0.85) = -1.7349
        # to break the zero-gradient saddle point at logit=0 with pos_weight=5.6667
        nn.init.xavier_uniform_(self.classifier.weight)
        nn.init.constant_(self.classifier.bias, -1.7349)

    # ==============================================================
    # JUMP ATTENTION
    # ==============================================================

    def _jump_attention(self, layer_outputs):
        """
        Attention-weighted aggregation of layer representations.

        Instead of concatenation + linear projection, learn to
        weight each layer's contribution based on its content.

        Args:
            layer_outputs: list of [N, hidden] tensors

        Returns:
            [N, hidden] aggregated representation
        """

        # [N, num_layers, hidden]
        stacked = torch.stack(
            layer_outputs,
            dim=1
        )

        # [N, num_layers, 1] -> [N, num_layers]
        scores = self.jump_attention_layer(
            stacked
        ).squeeze(-1)

        weights = torch.softmax(
            scores,
            dim=1
        )

        # [N, hidden]
        output = (
            stacked
            *
            weights.unsqueeze(-1)
        ).sum(dim=1)

        return output

    # ==============================================================
    # FORWARD
    # ==============================================================

    def forward(
        self,
        x,
        relation_edges,
        transaction_map,
        attribute_map,
        transaction_indices,
        hybrid_edge_index=None,
        hybrid_edge_weight=None
    ):
        """
        Forward pass with dual-pathway message passing.

        Args:
            x: [N, input_channels] node features (batch)
            relation_edges: list of 12 [2, E_r] edge index tensors
            transaction_map: [N] batch node -> transaction index
                             (-1 if attribute node)
            attribute_map: [N] batch node -> attribute index
                           (-1 if transaction node)
            transaction_indices: [B] target transaction indices
                                 in the compact transaction tensor
            hybrid_edge_index: [2, E_h] hybrid txn-txn edges
                               (batch-local node indices)
            hybrid_edge_weight: [E_h] hybrid similarity scores
        """

        device = x.device

        # ==========================================================
        # LOCAL NODE INFORMATION
        # ==========================================================

        num_nodes = x.shape[0]

        transaction_nodes = torch.where(
            transaction_map >= 0
        )[0]

        attribute_nodes = torch.where(
            attribute_map >= 0
        )[0]

        # ==========================================================
        # SAFETY CHECK
        # ==========================================================

        if transaction_nodes.numel() == 0:

            raise RuntimeError(
                "No transaction nodes found in batch."
            )

        if attribute_nodes.numel() == 0:

            raise RuntimeError(
                "No attribute nodes found in batch."
            )

        # ==========================================================
        # EXTRACT AND PROJECT FEATURES
        # ==========================================================

        transaction_x = self.input_projection(
            x[transaction_nodes]
        )

        attribute_x = self.input_projection(
            x[attribute_nodes]
        )

        # ==========================================================
        # LOCAL INDEX MAPPINGS
        # batch node index -> compact feature tensor index
        # ==========================================================

        transaction_local_map = torch.full(
            (num_nodes,),
            -1,
            dtype=torch.long,
            device=device
        )

        transaction_local_map[
            transaction_nodes
        ] = torch.arange(
            transaction_nodes.shape[0],
            device=device
        )

        attribute_local_map = torch.full(
            (num_nodes,),
            -1,
            dtype=torch.long,
            device=device
        )

        attribute_local_map[
            attribute_nodes
        ] = torch.arange(
            attribute_nodes.shape[0],
            device=device
        )

        # ==========================================================
        # REMAP HYBRID EDGES TO COMPACT TRANSACTION INDICES
        # ==========================================================

        has_hybrid = (
            hybrid_edge_index is not None
            and hybrid_edge_index.numel() > 0
            and hybrid_edge_index.shape[1] > 0
        )

        local_hybrid_edges = None
        local_hybrid_weight = None

        if has_hybrid:

            h_src = hybrid_edge_index[0]
            h_tgt = hybrid_edge_index[1]

            # Both endpoints must be transaction nodes
            src_valid = (
                transaction_map[h_src] >= 0
            )
            tgt_valid = (
                transaction_map[h_tgt] >= 0
            )
            valid_mask = src_valid & tgt_valid

            if valid_mask.any():

                h_src_local = transaction_local_map[
                    h_src[valid_mask]
                ]

                h_tgt_local = transaction_local_map[
                    h_tgt[valid_mask]
                ]

                local_hybrid_edges = torch.stack(
                    [h_src_local, h_tgt_local],
                    dim=0
                )

                if hybrid_edge_weight is not None:
                    local_hybrid_weight = (
                        hybrid_edge_weight[valid_mask]
                    )

            else:
                has_hybrid = False

        # ==========================================================
        # JUMP REPRESENTATIONS
        # ==========================================================

        jump_representations = []

        # ==========================================================
        # MESSAGE PASSING LAYERS
        # ==========================================================

        for layer_index in range(
            self.num_layers
        ):

            # ======================================================
            # ATTRIBUTE UPDATE
            # transaction -> attribute
            # ======================================================

            attribute_relation_outputs = []

            for relation_index in range(
                self.num_relations
            ):

                edge_index = relation_edges[
                    relation_index
                ]

                if edge_index.shape[1] == 0:
                    continue

                source_global = edge_index[0]
                target_global = edge_index[1]

                # Keep only: transaction -> attribute
                valid_source = (
                    transaction_map[
                        source_global
                    ] >= 0
                )

                valid_target = (
                    attribute_map[
                        target_global
                    ] >= 0
                )

                valid = (
                    valid_source
                    &
                    valid_target
                )

                if not valid.any():
                    continue

                source_global = source_global[valid]
                target_global = target_global[valid]

                source_local = transaction_local_map[
                    source_global
                ]

                target_local = attribute_local_map[
                    target_global
                ]

                local_edges = torch.stack(
                    [source_local, target_local],
                    dim=0
                )

                # Safety checks
                if (
                    source_local.min() < 0
                    or
                    source_local.max()
                    >= transaction_x.shape[0]
                ):
                    raise RuntimeError(
                        f"Invalid transaction source "
                        f"in relation {relation_index}"
                    )

                if (
                    target_local.min() < 0
                    or
                    target_local.max()
                    >= attribute_x.shape[0]
                ):
                    raise RuntimeError(
                        f"Invalid attribute target "
                        f"in relation {relation_index}"
                    )

                # Attention
                output = self.attribute_layers[
                    layer_index
                ][
                    relation_index
                ](
                    transaction_x,
                    attribute_x,
                    local_edges
                )

                attribute_relation_outputs.append(
                    output
                )

            # Aggregate relation outputs
            if len(attribute_relation_outputs) > 0:

                attribute_message = torch.stack(
                    attribute_relation_outputs,
                    dim=0
                ).mean(dim=0)

                attribute_message = (
                    self.attribute_relation_projection(
                        attribute_message
                    )
                )

            else:

                attribute_message = torch.zeros_like(
                    attribute_x
                )

            # Residual + normalization
            attribute_x = (
                attribute_x
                +
                attribute_message
            )

            attribute_x = self.attribute_norms[
                layer_index
            ](attribute_x)

            attribute_x = F.relu(attribute_x)

            attribute_x = self.dropout(attribute_x)

            # ======================================================
            # BIPARTITE TRANSACTION UPDATE
            # attribute -> transaction
            # ======================================================

            transaction_relation_outputs = []

            for relation_index in range(
                self.num_relations
            ):

                edge_index = relation_edges[
                    relation_index
                ]

                if edge_index.shape[1] == 0:
                    continue

                source_global = edge_index[0]
                target_global = edge_index[1]

                # Keep only: attribute -> transaction
                valid_source = (
                    attribute_map[
                        source_global
                    ] >= 0
                )

                valid_target = (
                    transaction_map[
                        target_global
                    ] >= 0
                )

                valid = (
                    valid_source
                    &
                    valid_target
                )

                if not valid.any():
                    continue

                source_global = source_global[valid]
                target_global = target_global[valid]

                source_local = attribute_local_map[
                    source_global
                ]

                target_local = transaction_local_map[
                    target_global
                ]

                local_edges = torch.stack(
                    [source_local, target_local],
                    dim=0
                )

                # Safety checks
                if (
                    source_local.min() < 0
                    or
                    source_local.max()
                    >= attribute_x.shape[0]
                ):
                    raise RuntimeError(
                        f"Invalid attribute source "
                        f"in relation {relation_index}"
                    )

                if (
                    target_local.min() < 0
                    or
                    target_local.max()
                    >= transaction_x.shape[0]
                ):
                    raise RuntimeError(
                        f"Invalid transaction target "
                        f"in relation {relation_index}"
                    )

                # Attention
                output = self.transaction_layers[
                    layer_index
                ][
                    relation_index
                ](
                    attribute_x,
                    transaction_x,
                    local_edges
                )

                transaction_relation_outputs.append(
                    output
                )

            # Aggregate bipartite messages
            if len(transaction_relation_outputs) > 0:

                bipartite_message = torch.stack(
                    transaction_relation_outputs,
                    dim=0
                ).mean(dim=0)

                bipartite_message = (
                    self.transaction_relation_projection(
                        bipartite_message
                    )
                )

            else:

                bipartite_message = torch.zeros_like(
                    transaction_x
                )

            # ======================================================
            # HYBRID TRANSACTION UPDATE
            # transaction -> transaction via similarity edges
            # ======================================================

            if has_hybrid:

                hybrid_message = self.hybrid_layers[
                    layer_index
                ](
                    transaction_x,
                    local_hybrid_edges,
                    local_hybrid_weight
                )

            else:

                hybrid_message = torch.zeros_like(
                    transaction_x
                )

            # ======================================================
            # COMBINE PATHWAYS
            # concat(bipartite, hybrid) -> projection -> hidden
            # ======================================================

            combined_message = self.combine_projections[
                layer_index
            ](
                torch.cat(
                    [bipartite_message, hybrid_message],
                    dim=1
                )
            )

            # ======================================================
            # RESIDUAL + NORMALIZATION
            # ======================================================

            transaction_x = (
                transaction_x
                +
                combined_message
            )

            transaction_x = self.transaction_norms[
                layer_index
            ](transaction_x)

            transaction_x = F.relu(transaction_x)

            transaction_x = self.dropout(transaction_x)

            # ======================================================
            # STORE FOR JUMP CONNECTION
            # ======================================================

            jump_representations.append(
                transaction_x
            )

        # ==========================================================
        # JUMP ATTENTION AGGREGATION
        # ==========================================================

        jump_output = self._jump_attention(
            jump_representations
        )

        # ==========================================================
        # FINAL REPRESENTATION
        # ==========================================================

        final_input = torch.cat(
            [transaction_x, jump_output],
            dim=1
        )

        final_representation = self.final_projection(
            final_input
        )

        final_representation = self.final_norm(
            final_representation
        )

        final_representation = F.relu(
            final_representation
        )

        final_representation = self.dropout(
            final_representation
        )

        # ==========================================================
        # CLASSIFICATION
        # ==========================================================

        all_logits = self.classifier(
            final_representation
        ).squeeze(-1)

        # ==========================================================
        # SELECT ONLY TARGET TRANSACTIONS
        # ==========================================================

        target_logits = all_logits[
            transaction_indices
        ]

        return target_logits