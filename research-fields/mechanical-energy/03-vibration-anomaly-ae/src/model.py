"""1D Conv Autoencoder モデル定義."""
from __future__ import annotations

import torch
import torch.nn as nn


class Conv1DAE(nn.Module):
    """
    入力: (B, 1, 2048)  出力: (B, 1, 2048)
    Encoder:  2048 -> conv/2 -> 1024 -> conv/2 -> 512 -> conv/2 -> 256 -> fc -> 32
    Decoder:  32 -> fc -> 256 -> upsample -> 512 -> up -> 1024 -> up -> 2048
    """

    def __init__(self, latent_dim: int = 32, seq_len: int = 2048):
        super().__init__()
        self.seq_len = seq_len

        # Encoder: 3 blocks of (Conv1d + BN + ReLU + MaxPool1d)
        self.enc = nn.Sequential(
            nn.Conv1d(1, 16, kernel_size=7, padding=3),
            nn.BatchNorm1d(16),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(2),  # 2048 -> 1024

            nn.Conv1d(16, 32, kernel_size=5, padding=2),
            nn.BatchNorm1d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(2),  # 1024 -> 512

            nn.Conv1d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm1d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(2),  # 512 -> 256
        )
        self.enc_flat_dim = 64 * (seq_len // 8)
        self.to_latent = nn.Linear(self.enc_flat_dim, latent_dim)

        # Decoder mirror
        self.from_latent = nn.Linear(latent_dim, self.enc_flat_dim)
        self.dec = nn.Sequential(
            nn.Upsample(scale_factor=2, mode="linear", align_corners=False),  # 256 -> 512
            nn.Conv1d(64, 32, kernel_size=3, padding=1),
            nn.BatchNorm1d(32),
            nn.ReLU(inplace=True),

            nn.Upsample(scale_factor=2, mode="linear", align_corners=False),  # 512 -> 1024
            nn.Conv1d(32, 16, kernel_size=5, padding=2),
            nn.BatchNorm1d(16),
            nn.ReLU(inplace=True),

            nn.Upsample(scale_factor=2, mode="linear", align_corners=False),  # 1024 -> 2048
            nn.Conv1d(16, 1, kernel_size=7, padding=3),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b = x.size(0)
        h = self.enc(x)
        z = self.to_latent(h.view(b, -1))
        h2 = self.from_latent(z).view(b, 64, self.seq_len // 8)
        return self.dec(h2)
