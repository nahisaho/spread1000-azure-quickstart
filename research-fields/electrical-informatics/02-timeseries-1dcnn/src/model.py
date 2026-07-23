"""
コンパクト 1D-CNN for UCI HAR.

- 3 ブロック Conv1d + BN + ReLU + MaxPool + GAP + Dropout + Linear
- 学習可能パラメータ ~32K
- 入力: (batch, 9, 128) → 出力: (batch, 6) ロジット
"""
from __future__ import annotations

import torch
import torch.nn as nn


def _block(cin: int, cout: int, kernel: int) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv1d(cin, cout, kernel_size=kernel, padding=kernel // 2),
        nn.BatchNorm1d(cout),
        nn.ReLU(inplace=True),
        nn.MaxPool1d(2),
    )


class BiosignalCNN(nn.Module):
    """9 チャネル × 128 時点 → 6 クラスの軽量 CNN."""

    def __init__(self, n_channels: int = 9, n_classes: int = 6, dropout: float = 0.30):
        super().__init__()
        self.features = nn.Sequential(
            _block(n_channels, 32, 7),   # 128 → 64
            _block(32, 64, 5),           # 64 → 32
            _block(64, 96, 3),           # 32 → 16
        )
        self.gap = nn.AdaptiveAvgPool1d(1)
        self.dropout = nn.Dropout(dropout)
        self.head = nn.Linear(96, n_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, 9, 128)
        x = self.features(x)              # (B, 96, 16)
        x = self.gap(x).squeeze(-1)       # (B, 96)
        return self.head(self.dropout(x)) # (B, 6)


def num_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
