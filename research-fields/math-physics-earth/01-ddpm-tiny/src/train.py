"""Train tiny DDPM on Fashion-MNIST resized to 16x16."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import random
import subprocess
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms

from _argtypes import bounded_int
from model import TinyUNet, NoiseSchedule

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_info() -> tuple[str, bool]:
    """Return (commit_sha, is_dirty). Best-effort; returns ('unknown', False) on error."""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
        dirty = bool(subprocess.check_output(
            ["git", "status", "--porcelain"], stderr=subprocess.DEVNULL, text=True
        ).strip())
        return commit, dirty
    except Exception:
        return "unknown", False


def get_versions() -> dict[str, str]:
    import torchvision
    import matplotlib as mpl
    return {
        "python": platform.python_version(),
        "torch": torch.__version__,
        "torchvision": torchvision.__version__,
        "numpy": np.__version__,
        "matplotlib": mpl.__version__,
    }


def dataset_sha256s(data_dir: Path) -> dict[str, str]:
    raw_dir = data_dir / "FashionMNIST" / "raw"
    candidates = [
        "train-images-idx3-ubyte.gz",
        "train-labels-idx1-ubyte.gz",
        "t10k-images-idx3-ubyte.gz",
        "t10k-labels-idx1-ubyte.gz",
    ]
    result: dict[str, str] = {}
    for fname in candidates:
        p = raw_dir / fname
        if p.exists():
            result[fname] = sha256_file(p)
        else:
            p2 = raw_dir / fname.removesuffix(".gz")
            result[fname] = sha256_file(p2) if p2.exists() else "missing"
    return result


def compute_val_mse(
    model: nn.Module,
    scheduler: NoiseSchedule,
    val_loader: DataLoader,
    device: torch.device,
    seed: int,
) -> float:
    """Compute deterministic validation denoising MSE (same noise each epoch)."""
    model.eval()
    saved_rng = torch.get_rng_state()
    torch.manual_seed(seed)
    mse_fn = nn.MSELoss()
    total = 0.0
    n = 0
    with torch.no_grad():
        for x, _ in val_loader:
            x = x.to(device)
            b = x.size(0)
            t = torch.randint(0, scheduler.T, (b,), device=device)
            noise = torch.randn_like(x)
            xt = scheduler.q_sample(x, t, noise)
            eps_pred = model(xt, t)
            total += mse_fn(eps_pred, noise).item() * b
            n += b
    torch.set_rng_state(saved_rng)
    return total / n if n > 0 else float("nan")


def emit_manifest(out_dir: Path) -> None:
    """Write manifest.json listing full SHA-256 of every artifact in out_dir."""
    artifacts = {
        p.name: sha256_file(p)
        for p in sorted(out_dir.iterdir())
        if p.is_file() and p.name != "manifest.json"
    }
    with (out_dir / "manifest.json").open("w") as f:
        json.dump({"artifacts": artifacts}, f, indent=2)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train tiny DDPM on Fashion-MNIST (16×16)")
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    p.add_argument("--epochs", type=bounded_int("epochs", 1, 50), default=10)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--batch-size", type=bounded_int("batch-size", 1, 1024), default=64)
    p.add_argument("--T", type=bounded_int("T", 10, 1000), default=200)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-subset", type=bounded_int("n-subset", 1, 60000), default=4000,
                   help="Fashion-MNIST サブサンプル数 (CPU 前提)")
    p.add_argument("--schedule", choices=("cosine", "linear"), default="cosine",
                   help="Noise schedule (default: cosine)")
    p.add_argument("--beta-end", type=float, default=0.02,
                   help="Linear schedule の beta_end (--schedule linear 時のみ有効)")
    p.add_argument("--output-dir", type=Path, default=None)
    p.add_argument("--resume", type=Path, default=None,
                   help="再開するチェックポイントの PATH")
    p.add_argument("--allow-long-run", action="store_true",
                   help="epochs>10, T>500, または n_subset>10000 を超える場合に必要")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # Cost cap gate (HIGH 5)
    if (args.epochs > 10 or args.T > 500 or args.n_subset > 10000) and not args.allow_long_run:
        raise SystemExit(
            "ERROR: epochs>10, T>500, または n_subset>10000 には --allow-long-run が必要です。"
        )

    # Validation (MED 6)
    if args.lr <= 0:
        raise ValueError(f"--lr must be > 0, got {args.lr}")
    if args.n_subset < args.batch_size:
        raise ValueError(
            f"--n-subset ({args.n_subset}) must be >= --batch-size ({args.batch_size})."
        )

    if args.device == "cpu":
        torch.set_num_threads(min(8, os.cpu_count() or 1))
    set_seed(args.seed)

    out_dir = args.output_dir or OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    device = torch.device(args.device)

    tfm = transforms.Compose([
        transforms.Resize(16),
        transforms.ToTensor(),
        transforms.Normalize((0.5,), (0.5,)),
    ])
    print(f"[data] downloading Fashion-MNIST to {DATA_DIR} (~30MB)")
    full_ds = datasets.FashionMNIST(str(DATA_DIR), train=True, download=True, transform=tfm)

    # Deterministic subset + 90/10 val split (MED 7)
    rng_sub = torch.Generator().manual_seed(args.seed)
    all_idx = torch.randperm(len(full_ds), generator=rng_sub).tolist()
    subset_idx = all_idx[: args.n_subset]
    n_train = max(1, int(len(subset_idx) * 0.9))
    train_idx = subset_idx[:n_train]
    val_idx = subset_idx[n_train:] if len(subset_idx) > n_train else subset_idx[:1]

    # --resume: restore dataset split from saved checkpoint
    if args.resume is not None:
        ck_resume = torch.load(args.resume, map_location=device, weights_only=False)
        saved_prov = ck_resume.get("provenance", {})
        if "dataset_indices" in saved_prov:
            train_idx = saved_prov["dataset_indices"]["train"]
            val_idx = saved_prov["dataset_indices"]["val"]

    train_ds = Subset(full_ds, train_idx)
    val_ds = Subset(full_ds, val_idx)
    train_loader = DataLoader(
        train_ds, batch_size=args.batch_size, shuffle=True, num_workers=0, drop_last=False
    )
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)
    print(f"[data] train={len(train_ds)}, val={len(val_ds)} images (16x16 grayscale)")

    arch_config = {"base_ch": 32, "t_dim": 64}
    model = TinyUNet(**arch_config).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"[model] TinyUNet: {n_params:,} params")

    scheduler = NoiseSchedule(
        T=args.T,
        schedule=args.schedule,
        beta_end=args.beta_end,
        device=device,
    )
    schedule_config: dict = {
        "name": args.schedule,
        "T": args.T,
        "beta_end": args.beta_end if args.schedule == "linear" else None,
        "betas_min": float(scheduler.betas.min()),
        "betas_max": float(scheduler.betas.max()),
        "alpha_bars_last": float(scheduler.alpha_bars[-1]),
    }

    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    mse_fn = nn.MSELoss()

    start_epoch = 1
    history: list[float] = []
    val_history: list[float] = []

    # --resume: restore model + optimizer + RNG + epoch (MED 9)
    if args.resume is not None:
        model.load_state_dict(ck_resume["model_state_dict"])
        opt.load_state_dict(ck_resume["optimizer_state_dict"])
        start_epoch = ck_resume.get("epoch", 0) + 1
        history = ck_resume.get("history", [])
        val_history = ck_resume.get("val_history", [])
        if "rng_state" in ck_resume:
            torch.set_rng_state(ck_resume["rng_state"]["torch"])
            np.random.set_state(ck_resume["rng_state"]["numpy"])
        print(f"[resume] チェックポイント {args.resume} から再開 (epoch {start_epoch}〜)")

    ckpt_path = out_dir / "ddpm_model.pt"
    partial: list[Path] = []

    try:
        for epoch in range(start_epoch, args.epochs + 1):
            model.train()
            total_loss = 0.0
            n = 0
            for x, _ in train_loader:
                x = x.to(device)
                b = x.size(0)
                t = torch.randint(0, args.T, (b,), device=device)
                noise = torch.randn_like(x)
                xt = scheduler.q_sample(x, t, noise)
                eps_pred = model(xt, t)
                loss = mse_fn(eps_pred, noise)

                # NaN/Inf guard (HIGH 4)
                if not torch.isfinite(loss):
                    raise FloatingPointError(
                        f"Epoch {epoch}: non-finite loss {loss.item()!r}"
                    )

                opt.zero_grad()
                loss.backward()

                grad_norm_sq = sum(
                    p.grad.data.norm(2).item() ** 2
                    for p in model.parameters()
                    if p.grad is not None
                )
                if not math.isfinite(grad_norm_sq):
                    raise FloatingPointError(
                        f"Epoch {epoch}: non-finite gradient norm"
                    )

                opt.step()
                total_loss += loss.item() * b
                n += b

            avg = total_loss / n
            val_mse = compute_val_mse(model, scheduler, val_loader, device, seed=args.seed)
            history.append(avg)
            val_history.append(val_mse)
            print(f"[epoch {epoch:3d}/{args.epochs}] loss={avg:.5f}  val_mse={val_mse:.5f}")

        # Provenance (HIGH 3)
        git_commit, git_dirty = git_info()
        provenance = {
            "args_dict": {
                k: str(v) if isinstance(v, Path) else v
                for k, v in vars(args).items()
            },
            "arch_config": arch_config,
            "schedule_config": schedule_config,
            "dataset_indices": {"train": train_idx, "val": val_idx},
            "versions": get_versions(),
            "git_commit": git_commit,
            "git_dirty": git_dirty,
            "dataset_sha256": dataset_sha256s(DATA_DIR),
        }

        rng_state = {
            "torch": torch.get_rng_state(),
            "numpy": np.random.get_state(),
        }

        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": opt.state_dict(),
                "T": args.T,
                "history": history,
                "val_history": val_history,
                "epoch": args.epochs,
                "arch_config": arch_config,
                "schedule_config": schedule_config,
                "provenance": provenance,
                "rng_state": rng_state,
            },
            ckpt_path,
        )
        partial.append(ckpt_path)

        # Loss curve (train + val)
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(history, marker="o", label="train")
        ax.plot(val_history, marker="s", label="val")
        ax.set_xlabel("epoch")
        ax.set_ylabel("MSE loss")
        ax.grid(alpha=0.3)
        ax.legend()
        ax.set_title("DDPM training loss")
        fig.tight_layout()
        lc_path = out_dir / "loss_curve.png"
        fig.savefig(lc_path, dpi=120)
        plt.close(fig)
        partial.append(lc_path)

        # Inline sample grid
        print("[sample] generating 16 images by reverse diffusion (T steps)")
        model.eval()
        samples = scheduler.p_sample_loop(model, (16, 1, 16, 16), device=device)
        if not torch.isfinite(samples).all():
            raise FloatingPointError("Non-finite values in generated samples")
        samples = (samples.clamp(-1, 1) + 1.0) / 2.0

        fig, axes = plt.subplots(4, 4, figsize=(6, 6))
        for i, ax in enumerate(axes.flatten()):
            ax.imshow(samples[i, 0].cpu().numpy(), cmap="gray", vmin=0, vmax=1)
            ax.axis("off")
        plt.suptitle(f"DDPM samples after {args.epochs} epochs")
        plt.tight_layout()
        sp_path = out_dir / "samples.png"
        plt.savefig(sp_path, dpi=120)
        plt.close()
        partial.append(sp_path)

        metrics_path = out_dir / "train_metrics.json"
        with metrics_path.open("w") as f:
            json.dump(
                {
                    "final_train_loss": history[-1],
                    "final_val_mse": val_history[-1] if val_history else None,
                    "epochs": args.epochs,
                    "T": args.T,
                    "schedule": args.schedule,
                    "params": n_params,
                    "seed": args.seed,
                },
                f,
                indent=2,
                allow_nan=False,
            )
        partial.append(metrics_path)

        emit_manifest(out_dir)
        print(f"[train] saved → {ckpt_path}, samples.png, loss_curve.png, manifest.json")

    except Exception:
        for p in partial:
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass
        raise


if __name__ == "__main__":
    main()

