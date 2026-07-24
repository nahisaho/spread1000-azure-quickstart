"""MONAI U-Net for 1-channel input, 1-channel output segmentation.

Uses monai.networks.nets.UNet (3 resolution levels, channels 16/32/64,
2 residual units per level).  The forward pass returns RAW LOGITS (no
sigmoid).  Apply sigmoid+threshold at inference; use DiceCELoss (which
applies sigmoid internally) during training.

License: MONAI is Apache-2.0.
  https://github.com/Project-MONAI/MONAI/blob/dev/LICENSE
"""
from __future__ import annotations

import torch
from torch import nn


def build_model(in_channels: int = 1, out_channels: int = 1) -> nn.Module:
    """Return a MONAI UNet (3 levels, channels 16/32/64, 2 res-units each).

    Input spatial size must be divisible by 4 (two stride-2 conv layers).
    Run ``python src/model.py`` to print the actual parameter count.
    """
    from monai.networks.nets import UNet

    return UNet(
        spatial_dims=2,
        in_channels=in_channels,
        out_channels=out_channels,
        channels=(16, 32, 64),
        strides=(2, 2),
        num_res_units=2,
    )


def count_parameters(model: nn.Module) -> int:
    """Count trainable parameters."""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


if __name__ == "__main__":
    m = build_model()
    x = torch.zeros(1, 1, 128, 128)
    y = m(x)
    n = count_parameters(m)
    print(f"MONAI UNet: {n:,} parameters")
    print(f"Input:  {tuple(x.shape)}")
    print(f"Output: {tuple(y.shape)}")
    # Regenerate parameter count snippet for docs:
    print(f'\npython -c "import sys; sys.path.insert(0,\'src\'); '
          f'from model import build_model, count_parameters; '
          f'print(count_parameters(build_model()))"')
    print(f"# → {n}")
