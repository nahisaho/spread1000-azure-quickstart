"""Train MONAI U-Net on synthetic Voronoi grain / particle segmentation.

Uses:
  monai.networks.nets.UNet    — 3-level U-Net (channels 16/32/64, 2 res-units)
  monai.losses.DiceCELoss     — Dice + binary-CE fused loss with pos-weight
  monai.metrics.DiceMetric    — MONAI Dice metric with per-epoch reset
  monai.data.CacheDataset     — cache all samples in RAM (fast epochs)
  monai.data.DataLoader       — MONAI-compatible DataLoader
  monai.transforms.Compose    — dict-based augmentation pipeline

Usage:
    python src/train.py --task grains --image-size 128 \
        --n-train 200 --n-val 50 --epochs 10 --device cpu --output data/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


# ── Argument validators ────────────────────────────────────────────────────


def _positive_int(value: str) -> int:
    try:
        v = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected integer, got {value!r}")
    if v <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive integer (got {v})")
    return v


def _positive_float(value: str) -> float:
    try:
        v = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected float, got {value!r}")
    if not math.isfinite(v) or v <= 0:
        raise argparse.ArgumentTypeError(
            f"must be a finite positive float (got {value!r})"
        )
    return v


# ── CLI ────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--task", default="grains", choices=["grains", "particles"])
    p.add_argument(
        "--image-size", type=_positive_int, default=128,
        help="Must be divisible by 4 (default: 128)",
    )
    p.add_argument("--n-train", type=_positive_int, default=200)
    p.add_argument("--n-val", type=_positive_int, default=50)
    p.add_argument("--batch-size", type=_positive_int, default=8)
    p.add_argument(
        "--epochs", type=_positive_int, default=10,
        help="Training epochs. >50 requires --allow-long-run (default: 10)",
    )
    p.add_argument("--lr", type=_positive_float, default=1e-3)
    p.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    p.add_argument(
        "--num-workers", type=int, default=0,
        help="DataLoader workers (0 for WSL2/Windows compatibility)",
    )
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--pos-weight", type=_positive_float, default=9.0,
        help="BCE pos_weight for class-imbalance (grain boundaries ~12%% of pixels)",
    )
    p.add_argument("--n-montage", type=_positive_int, default=6)
    p.add_argument(
        "--max-training-hours", type=_positive_float, default=2.0,
        help="Wall-clock limit in hours; abort gracefully if exceeded. "
             ">4.0 requires --allow-long-run (default: 2.0)",
    )
    p.add_argument(
        "--allow-long-run", action="store_true",
        help="Required when --max-training-hours > 4.0 or --epochs > 50",
    )
    p.add_argument("--output", type=Path, default=Path("data"))
    return p.parse_args()


# ── Data ───────────────────────────────────────────────────────────────────


def _make_datasets(args):
    """Generate synthetic images in-memory, wrap in MONAI CacheDatasets."""
    import numpy as np
    import torch
    from monai.data import CacheDataset
    from monai.transforms import (
        Compose,
        EnsureTyped,
        RandFlipd,
        RandRotate90d,
    )

    sys.path.insert(0, str(Path(__file__).parent))
    from generate_data import generate_batch

    print(
        f"[data] generating {args.n_train} train / {args.n_val} val "
        f"{args.image_size}×{args.image_size} images, task={args.task} ..."
    )
    train_imgs, train_masks = generate_batch(
        args.task, args.n_train, args.image_size, seed=args.seed
    )
    # Different seed so val samples are independent of train
    val_imgs, val_masks = generate_batch(
        args.task, args.n_val, args.image_size, seed=args.seed + 10_000
    )

    positive_frac = float(np.mean(train_masks))
    print(f"[data] positive pixel fraction (train): {positive_frac:.4f}")

    train_data = [
        {"image": train_imgs[i], "label": train_masks[i]}
        for i in range(args.n_train)
    ]
    val_data = [
        {"image": val_imgs[i], "label": val_masks[i]}
        for i in range(args.n_val)
    ]

    train_transforms = Compose([
        EnsureTyped(keys=["image", "label"], dtype=torch.float32, track_meta=False),
        RandFlipd(keys=["image", "label"], prob=0.5, spatial_axis=0),
        RandFlipd(keys=["image", "label"], prob=0.5, spatial_axis=1),
        RandRotate90d(keys=["image", "label"], prob=0.25, max_k=3),
    ])
    val_transforms = Compose([
        EnsureTyped(keys=["image", "label"], dtype=torch.float32, track_meta=False),
    ])

    train_ds = CacheDataset(
        data=train_data, transform=train_transforms,
        cache_rate=1.0, num_workers=0,
    )
    val_ds = CacheDataset(
        data=val_data, transform=val_transforms,
        cache_rate=1.0, num_workers=0,
    )
    return train_ds, val_ds, positive_frac


# ── Training ───────────────────────────────────────────────────────────────


def main() -> int:  # noqa: C901  (intentionally long — training loop)
    args = parse_args()

    # ── Pre-flight validation ──────────────────────────────────────────────
    if args.image_size % 4 != 0:
        raise SystemExit(
            f"ERROR: --image-size must be divisible by 4 (got {args.image_size})."
        )
    if args.num_workers < 0:
        raise SystemExit("ERROR: --num-workers must be >= 0.")
    if args.max_training_hours > 4.0 and not args.allow_long_run:
        raise SystemExit(
            f"ERROR: --max-training-hours={args.max_training_hours} exceeds 4.0 h. "
            "Pass --allow-long-run to proceed."
        )
    if args.epochs > 50 and not args.allow_long_run:
        raise SystemExit(
            f"ERROR: --epochs={args.epochs} > 50. Pass --allow-long-run to proceed."
        )

    import numpy as np
    import torch
    import monai
    from monai.data import DataLoader
    from monai.losses import DiceCELoss
    from monai.metrics import DiceMetric
    from torchmetrics.functional.classification import binary_jaccard_index

    sys.path.insert(0, str(Path(__file__).parent))
    from model import build_model, count_parameters

    if args.device == "cuda" and not torch.cuda.is_available():
        raise SystemExit(
            "ERROR: --device cuda requested but torch.cuda.is_available() is False.\n"
            "  GPU install:\n"
            "    pip install torch==2.7.1 torchvision==0.22.1 "
            "--index-url https://download.pytorch.org/whl/cu126"
        )

    # ── Reproducibility ────────────────────────────────────────────────────
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    torch.use_deterministic_algorithms(True, warn_only=True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

    # ── Output directories ─────────────────────────────────────────────────
    args.output.mkdir(parents=True, exist_ok=True)
    ckpt_dir = args.output / "checkpoints"
    pred_dir = args.output / "predictions"
    ckpt_dir.mkdir(exist_ok=True)
    pred_dir.mkdir(exist_ok=True)

    device = torch.device(args.device)

    # ── Data ───────────────────────────────────────────────────────────────
    train_ds, val_ds, pos_frac = _make_datasets(args)
    train_loader = DataLoader(
        train_ds, batch_size=args.batch_size, shuffle=True,
        num_workers=args.num_workers, pin_memory=(args.device == "cuda"),
    )
    val_loader = DataLoader(
        val_ds, batch_size=args.batch_size, shuffle=False,
        num_workers=args.num_workers, pin_memory=(args.device == "cuda"),
    )

    # ── Model ──────────────────────────────────────────────────────────────
    model = build_model(in_channels=1, out_channels=1).to(device)
    n_params = count_parameters(model)
    print(f"[model] MONAI UNet: {n_params:,} parameters, device={device}")
    print(f"[env]   MONAI {monai.__version__}  PyTorch {torch.__version__}")

    # ── Loss & metric ──────────────────────────────────────────────────────
    # DiceCELoss applies sigmoid internally; ce_weight handles class imbalance.
    ce_weight = torch.tensor([args.pos_weight], device=device)
    criterion = DiceCELoss(
        sigmoid=True,
        lambda_dice=0.5,
        lambda_ce=0.5,
        ce_weight=ce_weight,
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    dice_metric = DiceMetric(
        include_background=True, reduction="mean", get_not_nans=False
    )

    train_losses: list[float] = []
    val_losses: list[float] = []
    val_ious: list[float] = []
    val_dices: list[float] = []
    best_iou = -1.0
    best_epoch = -1
    run_start = time.monotonic()

    for epoch in range(1, args.epochs + 1):
        # ── Wall-clock ceiling ─────────────────────────────────────────────
        elapsed_h = (time.monotonic() - run_start) / 3600.0
        if elapsed_h >= args.max_training_hours:
            print(
                f"[train] Wall-clock limit {args.max_training_hours:.1f}h reached "
                f"after epoch {epoch - 1}. Stopping early."
            )
            break

        # ── Train ──────────────────────────────────────────────────────────
        model.train()
        running = 0.0
        n_batches = 0
        for batch in train_loader:
            xb = batch["image"].to(device)
            yb = batch["label"].to(device)
            logits = model(xb)
            loss = criterion(logits, yb)
            if not torch.isfinite(loss):
                raise SystemExit(
                    f"ERROR: non-finite train loss {loss.item()!r} at epoch {epoch}. "
                    "Check inputs for NaN/Inf."
                )
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            running += float(loss.item())
            n_batches += 1
        train_loss = running / max(1, n_batches)
        train_losses.append(train_loss)

        # ── Validate ───────────────────────────────────────────────────────
        model.eval()
        dice_metric.reset()
        running = 0.0
        iou_sum = 0.0
        n_seen = 0
        with torch.no_grad():
            for batch in val_loader:
                xb = batch["image"].to(device)
                yb = batch["label"].to(device)
                logits = model(xb)
                loss = criterion(logits, yb)
                if not torch.isfinite(loss):
                    raise SystemExit(
                        f"ERROR: non-finite val loss {loss.item()!r} at epoch {epoch}."
                    )
                running += float(loss.item()) * xb.size(0)
                preds_bin = (torch.sigmoid(logits) > 0.5).float()
                dice_metric(y_pred=preds_bin, y=yb)
                iou_sum += (
                    float(binary_jaccard_index(preds_bin.long(), yb.long()))
                    * xb.size(0)
                )
                n_seen += xb.size(0)

        val_loss = running / max(1, n_seen)
        val_dice = float(dice_metric.aggregate())
        val_iou = iou_sum / max(1, n_seen)
        dice_metric.reset()

        if not math.isfinite(val_dice) or not math.isfinite(val_iou):
            raise SystemExit(
                f"ERROR: non-finite metric at epoch {epoch}: "
                f"dice={val_dice!r} iou={val_iou!r}"
            )

        val_losses.append(val_loss)
        val_ious.append(val_iou)
        val_dices.append(val_dice)

        marker = ""
        if val_iou > best_iou:
            best_iou = val_iou
            best_epoch = epoch
            torch.save(model.state_dict(), ckpt_dir / "best_model.pth")
            marker = " *best*"
        print(
            f"[epoch {epoch:>3d}/{args.epochs}] "
            f"train={train_loss:.4f}  val={val_loss:.4f}  "
            f"IoU={val_iou:.4f}  Dice={val_dice:.4f}{marker}"
        )

    if best_epoch < 0:
        raise SystemExit("ERROR: no completed epochs — nothing to save.")

    # ── Final montage & per-image metrics ──────────────────────────────────
    model.load_state_dict(
        torch.load(
            ckpt_dir / "best_model.pth",
            weights_only=True,
            map_location=device,
        )
    )
    model.eval()

    val_all_x = torch.stack([val_ds[i]["image"] for i in range(len(val_ds))])
    val_all_y = torch.stack([val_ds[i]["label"] for i in range(len(val_ds))])
    with torch.no_grad():
        preds_all = torch.sigmoid(model(val_all_x.to(device))).cpu()
    preds_bin_all = (preds_all > 0.5).float()

    per_image = []
    for i in range(len(val_all_y)):
        dm_single = DiceMetric(
            include_background=True, reduction="mean", get_not_nans=False
        )
        dm_single(
            y_pred=preds_bin_all[i : i + 1].float(),
            y=val_all_y[i : i + 1].float(),
        )
        per_image.append(
            {
                "index": int(i),
                "iou": float(
                    binary_jaccard_index(
                        preds_bin_all[i].long().unsqueeze(0),
                        val_all_y[i].long().unsqueeze(0),
                    )
                ),
                "dice": float(dm_single.aggregate()),
            }
        )
    (pred_dir / "per_image_metrics.json").write_text(
        json.dumps(per_image, indent=2, allow_nan=False)
    )

    import matplotlib.pyplot as plt

    n_show = min(args.n_montage, len(val_all_y))
    fig, axes = plt.subplots(n_show, 3, figsize=(9, 3 * n_show))
    titles = ["Input", "Ground Truth", "Prediction"]
    for i in range(n_show):
        row = axes[i] if n_show > 1 else axes
        for j, data in enumerate(
            [val_all_x[i, 0], val_all_y[i, 0], preds_bin_all[i, 0]]
        ):
            row[j].imshow(data.numpy(), cmap="gray", vmin=0, vmax=1)
            if i == 0:
                row[j].set_title(titles[j], fontsize=10)
            row[j].axis("off")
    plt.tight_layout()
    montage_path = pred_dir / f"montage_epoch{best_epoch:03d}.png"
    plt.savefig(montage_path, dpi=100)
    plt.close()

    # ── Checkpoint SHA-256 ─────────────────────────────────────────────────
    ckpt_path = ckpt_dir / "best_model.pth"
    ckpt_sha256 = hashlib.sha256(ckpt_path.read_bytes()).hexdigest()

    # ── Provenance metadata (best-effort) ─────────────────────────────────
    try:
        git_hash = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        git_hash = "unavailable"

    gpu_name = "N/A"
    if torch.cuda.is_available():
        try:
            gpu_name = torch.cuda.get_device_name(0)
        except Exception:
            pass

    # ── Write metrics.json ────────────────────────────────────────────────
    metrics = {
        "config": {
            "task": args.task,
            "image_size": args.image_size,
            "n_train": args.n_train,
            "n_val": args.n_val,
            "batch_size": args.batch_size,
            "epochs_requested": args.epochs,
            "epochs_completed": len(train_losses),
            "lr": args.lr,
            "device": args.device,
            "seed": args.seed,
            "pos_weight": args.pos_weight,
            "max_training_hours": args.max_training_hours,
        },
        "reproducibility": {
            "python_version": platform.python_version(),
            "torch_version": torch.__version__,
            "monai_version": monai.__version__,
            "cuda_version": torch.version.cuda,
            "cudnn_version": (
                torch.backends.cudnn.version()
                if torch.backends.cudnn.is_available()
                else None
            ),
            "gpu_name": gpu_name,
            "git_commit": git_hash,
            "deterministic_algorithms": True,
            "cudnn_deterministic": True,
            "cudnn_benchmark": False,
        },
        "positive_pixel_fraction_train": pos_frac,
        "n_parameters": n_params,
        "train_loss": train_losses,
        "val_loss": val_losses,
        "val_iou": val_ious,
        "val_dice": val_dices,
        "best_epoch": best_epoch,
        "best_val_iou": best_iou,
        "best_val_dice": val_dices[best_epoch - 1] if best_epoch > 0 else None,
        "checkpoint_sha256": ckpt_sha256,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "wall_clock_seconds": round(time.monotonic() - run_start, 1),
    }
    (args.output / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2, allow_nan=False)
    )
    print(f"[done] best val IoU = {best_iou:.4f} at epoch {best_epoch}")
    print(
        f"[done] checkpoint SHA-256: {ckpt_sha256[:16]}..."
        f"\n[done] wrote {args.output}/metrics.json, {montage_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
