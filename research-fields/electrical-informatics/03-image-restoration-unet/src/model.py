"""Small 3-level U-Net for image restoration (regression).

~117K parameters. 1-channel input → 1-channel output (residual noise prediction OFF;
the head predicts the clean image directly).

Design choice: predict the clean image directly (NOT residual noise), and
clamp to [0, 1] only at inference. This keeps the pipeline symmetric with
D-3 (materials segmentation) so learners can compare the two tasks:

    segmentation: same MiniUNet, BCEWithLogitsLoss, output = binary mask (0/1)
    restoration : same MiniUNet, L1 loss,          output = clean image [0,1]
"""
from __future__ import annotations

import torch
from torch import nn


class DoubleConv(nn.Module):
    """(Conv3x3 → BN → ReLU) × 2."""

    def __init__(self, in_ch: int, out_ch: int) -> None:
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class MiniUNet(nn.Module):
    """3-level U-Net: encoder 16→32→64, decoder 64→32→16, ~117K params.

    Input spatial size must be divisible by 4 (two max-pool 2×2 layers).
    Output has NO activation; caller can clamp to [0, 1] for display.
    """

    def __init__(self, in_channels: int = 1, out_channels: int = 1, base: int = 16) -> None:
        super().__init__()
        b = base
        self.enc1 = DoubleConv(in_channels, b)
        self.pool1 = nn.MaxPool2d(2)
        self.enc2 = DoubleConv(b, b * 2)
        self.pool2 = nn.MaxPool2d(2)
        self.bot = DoubleConv(b * 2, b * 4)
        self.up2 = nn.ConvTranspose2d(b * 4, b * 2, kernel_size=2, stride=2)
        self.dec2 = DoubleConv(b * 4, b * 2)
        self.up1 = nn.ConvTranspose2d(b * 2, b, kernel_size=2, stride=2)
        self.dec1 = DoubleConv(b * 2, b)
        self.head = nn.Conv2d(b, out_channels, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool1(e1))
        bt = self.bot(self.pool2(e2))
        d2 = self.dec2(torch.cat([self.up2(bt), e2], dim=1))
        d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))
        return self.head(d1)  # raw output (no activation)


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


if __name__ == "__main__":
    m = MiniUNet()
    x = torch.zeros(1, 1, 128, 128)
    y = m(x)
    print(f"MiniUNet: {count_parameters(m):,} parameters")
    print(f"Input:  {tuple(x.shape)}")
    print(f"Output: {tuple(y.shape)}")
