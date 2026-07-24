"""学習済み DDPM から新しいサンプルを生成."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch

from _argtypes import bounded_int
from model import TinyUNet, NoiseSchedule


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate samples from a trained DDPM checkpoint")
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--n-samples", type=bounded_int("n-samples", 1, 64), default=16)
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    p.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "outputs" / "new_samples.png",
    )
    p.add_argument("--seed", type=int, required=True, help="乱数シード (再現性のため必須)")
    p.add_argument("--allow-long-run", action="store_true",
                   help="n_samples > 32 の場合に必要")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # Cost cap gate (HIGH 5)
    if args.n_samples > 32 and not args.allow_long_run:
        raise SystemExit(
            "ERROR: --n-samples > 32 には --allow-long-run が必要です。"
        )

    torch.manual_seed(args.seed)
    device = torch.device(args.device)

    ck = torch.load(args.model, map_location=device, weights_only=False)
    T = int(ck["T"])

    # Verify architecture matches recorded config (HIGH 3)
    arch_config = ck.get("arch_config", {"base_ch": 32, "t_dim": 64})
    model = TinyUNet(**arch_config).to(device)
    model.load_state_dict(ck["model_state_dict"])
    model.eval()

    schedule_config = ck.get("schedule_config", {})
    schedule = schedule_config.get("name", "cosine")
    beta_end = schedule_config.get("beta_end") or 0.02

    scheduler = NoiseSchedule(T=T, schedule=schedule, beta_end=beta_end, device=device)
    samples = scheduler.p_sample_loop(model, (args.n_samples, 1, 16, 16), device=device)

    # NaN/Inf guard (HIGH 4)
    if not torch.isfinite(samples).all():
        raise FloatingPointError("Non-finite values in generated samples. Aborting save.")

    samples = (samples.clamp(-1, 1) + 1.0) / 2.0

    n = args.n_samples
    cols = int(n ** 0.5) or 1
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 1.5, rows * 1.5))
    axes = axes.flatten() if hasattr(axes, "flatten") else [axes]
    for i, ax in enumerate(axes):
        if i < n:
            ax.imshow(samples[i, 0].cpu().numpy(), cmap="gray", vmin=0, vmax=1)
        ax.axis("off")
    plt.tight_layout()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(args.out, dpi=120)
    plt.close()
    print(f"[sample] saved {n} images → {args.out}")


if __name__ == "__main__":
    main()

