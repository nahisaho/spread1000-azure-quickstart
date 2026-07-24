"""Small 1D CNN for AAMI 5-class ECG heartbeat classification.

~9.5k trainable params. Input shape (B, 1, 180) → output (B, 5) logits.
"""
from __future__ import annotations

import torch
from torch import nn


class ECG1DCNN(nn.Module):
    def __init__(self, n_classes: int = 5) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv1d(1, 16, kernel_size=7, padding=3),
            nn.BatchNorm1d(16),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(2),
            nn.Conv1d(16, 32, kernel_size=5, padding=2),
            nn.BatchNorm1d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(2),
            nn.Conv1d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm1d(64),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool1d(1),
        )
        self.head = nn.Linear(64, n_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:  # (B, 1, 180) → (B, 5)
        z = self.features(x).squeeze(-1)
        return self.head(z)


def num_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
