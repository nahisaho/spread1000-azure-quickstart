"""Tiny U-Net + Sinusoidal timestep embedding for DDPM (16x16 images)."""
from __future__ import annotations

import math
import torch
import torch.nn as nn


def timestep_embedding(t: torch.Tensor, dim: int) -> torch.Tensor:
    """Sinusoidal position embedding for scalar timestep t (B,) -> (B, dim)."""
    half = dim // 2
    freqs = torch.exp(
        -math.log(10000.0) * torch.arange(0, half, device=t.device).float() / half
    )
    args = t.float().unsqueeze(-1) * freqs.unsqueeze(0)
    emb = torch.cat([torch.sin(args), torch.cos(args)], dim=-1)
    if dim % 2 == 1:
        emb = torch.cat([emb, torch.zeros_like(emb[:, :1])], dim=-1)
    return emb


class ResBlock(nn.Module):
    def __init__(self, in_ch: int, out_ch: int, t_dim: int):
        super().__init__()
        self.conv1 = nn.Conv2d(in_ch, out_ch, 3, padding=1)
        self.conv2 = nn.Conv2d(out_ch, out_ch, 3, padding=1)
        self.gn1 = nn.GroupNorm(4, out_ch)
        self.gn2 = nn.GroupNorm(4, out_ch)
        self.t_proj = nn.Linear(t_dim, out_ch)
        self.skip = nn.Conv2d(in_ch, out_ch, 1) if in_ch != out_ch else nn.Identity()

    def forward(self, x, t_emb):
        h = torch.nn.functional.silu(self.gn1(self.conv1(x)))
        h = h + self.t_proj(t_emb).unsqueeze(-1).unsqueeze(-1)
        h = torch.nn.functional.silu(self.gn2(self.conv2(h)))
        return h + self.skip(x)


class TinyUNet(nn.Module):
    """
    16x16 grayscale U-Net. ~40K params.
    down: 16 -> 8 -> 4  (with 32, 64 channels)
    up:   4 -> 8 -> 16
    """

    def __init__(self, base_ch: int = 32, t_dim: int = 64):
        super().__init__()
        self.t_dim = t_dim
        self.t_mlp = nn.Sequential(
            nn.Linear(t_dim, t_dim), nn.SiLU(), nn.Linear(t_dim, t_dim)
        )
        # Encoder
        self.in_conv = nn.Conv2d(1, base_ch, 3, padding=1)         # 16x16
        self.enc1 = ResBlock(base_ch, base_ch, t_dim)
        self.down1 = nn.Conv2d(base_ch, base_ch * 2, 3, stride=2, padding=1)  # 8x8
        self.enc2 = ResBlock(base_ch * 2, base_ch * 2, t_dim)
        self.down2 = nn.Conv2d(base_ch * 2, base_ch * 2, 3, stride=2, padding=1)  # 4x4
        # Mid
        self.mid = ResBlock(base_ch * 2, base_ch * 2, t_dim)
        # Decoder
        self.up1 = nn.ConvTranspose2d(base_ch * 2, base_ch * 2, 4, stride=2, padding=1)  # 8x8
        self.dec1 = ResBlock(base_ch * 4, base_ch * 2, t_dim)
        self.up2 = nn.ConvTranspose2d(base_ch * 2, base_ch, 4, stride=2, padding=1)  # 16x16
        self.dec2 = ResBlock(base_ch * 2, base_ch, t_dim)
        self.out_conv = nn.Conv2d(base_ch, 1, 3, padding=1)

    def forward(self, x: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
        t_emb = self.t_mlp(timestep_embedding(t, self.t_dim))
        h0 = self.in_conv(x)               # 16
        h1 = self.enc1(h0, t_emb)          # 16
        h2 = self.down1(h1)                # 8
        h2 = self.enc2(h2, t_emb)          # 8
        h3 = self.down2(h2)                # 4
        h3 = self.mid(h3, t_emb)           # 4
        u1 = self.up1(h3)                  # 8
        u1 = self.dec1(torch.cat([u1, h2], dim=1), t_emb)
        u2 = self.up2(u1)                  # 16
        u2 = self.dec2(torch.cat([u2, h1], dim=1), t_emb)
        return self.out_conv(u2)


class DDPMScheduler:
    """Linear beta schedule, precomputed alphas."""

    def __init__(self, T: int = 200, beta_start: float = 1e-4, beta_end: float = 0.02,
                 device: torch.device = torch.device("cpu")):
        self.T = T
        self.betas = torch.linspace(beta_start, beta_end, T, device=device)
        self.alphas = 1.0 - self.betas
        self.alpha_bars = torch.cumprod(self.alphas, dim=0)
        self.sqrt_alpha_bars = torch.sqrt(self.alpha_bars)
        self.sqrt_one_minus_alpha_bars = torch.sqrt(1.0 - self.alpha_bars)

    def q_sample(self, x0: torch.Tensor, t: torch.Tensor, noise: torch.Tensor) -> torch.Tensor:
        """Forward: x_t = sqrt(a_bar_t) x_0 + sqrt(1 - a_bar_t) noise."""
        sab = self.sqrt_alpha_bars[t].view(-1, 1, 1, 1)
        sombab = self.sqrt_one_minus_alpha_bars[t].view(-1, 1, 1, 1)
        return sab * x0 + sombab * noise

    @torch.no_grad()
    def p_sample_loop(self, model: nn.Module, shape: tuple, device: torch.device) -> torch.Tensor:
        """Reverse: start from x_T ~ N(0,I), iterate p_theta(x_{t-1} | x_t)."""
        x = torch.randn(shape, device=device)
        for t in reversed(range(self.T)):
            t_tensor = torch.full((shape[0],), t, device=device, dtype=torch.long)
            eps_pred = model(x, t_tensor)
            alpha_t = self.alphas[t]
            alpha_bar_t = self.alpha_bars[t]
            beta_t = self.betas[t]
            coef1 = 1.0 / torch.sqrt(alpha_t)
            coef2 = beta_t / torch.sqrt(1.0 - alpha_bar_t)
            mean = coef1 * (x - coef2 * eps_pred)
            if t > 0:
                x = mean + torch.sqrt(beta_t) * torch.randn_like(x)
            else:
                x = mean
        return x
