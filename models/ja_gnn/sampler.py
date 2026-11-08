import torch
import torch.nn as nn


class JumpAttention(nn.Module):

    def __init__(self, hidden_channels, num_layers):
        super().__init__()

        self.attention = nn.Linear(
            hidden_channels,
            1
        )

        self.num_layers = num_layers

    def forward(self, layer_outputs):

        # layer_outputs:
        # [h1, h2, h3, ...]

        stacked = torch.stack(
            layer_outputs,
            dim=1
        )

        attention_scores = self.attention(
            stacked
        ).squeeze(-1)

        attention_weights = torch.softmax(
            attention_scores,
            dim=1
        )

        weighted = (
            stacked *
            attention_weights.unsqueeze(-1)
        )

        output = weighted.sum(
            dim=1
        )

        return output