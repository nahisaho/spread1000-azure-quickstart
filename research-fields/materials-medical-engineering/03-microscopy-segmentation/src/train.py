"""Train MiniUNet on synthetic Voronoi grain / particle segmentation.

Usage:
    python src/train.py --task grains --image-size 128 \
        --n-train 200 --n-val 50 --epochs 10 --device cpu --output data/
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--task", default="grains", choices=["grains", "particles"])
    p.add_argument("--image-size", type=int, default=128,
                   help="Must be divisible by 4 (default: 128)")
    p.add_argument("--n-train", type=int, default=200)
    p.add_argument("--n-val", type=int, default=50)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--epochs", type=int, default=10)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    p.add_argument("--num-workers", type=int, default=0,
                   help="DataLoader workers (0 for WSL2/Windows safety)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--pos-weight", type=float, default=9.0,
                   help="BCE pos_weight for class-imbalance handling")
    p.add_argument("--n-montage", type=int, default=6,
                   help="Number of val images to save in the final montage")
    p.add_argument("--output", type=Path, default=Path("data"))
    return p.parse_args()


def _make_loaders(args):
    import numpy as np
    import torch
    from torch.utils.data import DataLoader, TensorDataset

    if args.image_size % 4 != 0:
        raise SystemExit(
            f"ERROR: --image-size must be divisible by 4 (got {args.image_size})."
        )

    sys.path.insert(0, str(Path(__file__).parent))
    from generate_data import generate_batch

    print(f"[data] generating {args.n_train} train / {args.n_val} val "
          f"{args.image_size}×{args.image_size} images for task={args.task} ...")
    train_imgs, train_masks = generate_batch(args.task, args.n_train,
                                             args.image_size, seed=args.seed)
    # Use a different seed for val so it doesn't overlap the train distribution.
    val_imgs, val_masks = generate_batch(args.task, args.n_val,
                                         args.image_size, seed=args.seed + 10_000)

    tr_x = torch.from_numpy(train_imgs).float()
    tr_y = torch.from_numpy(train_masks).float()
    va_x = torch.from_numpy(val_imgs).float()
    va_y = torch.from_numpy(val_masks).float()

    positive_frac = float(tr_y.mean())
    print(f"[data] boundary/positive pixel fraction (train): {positive_frac:.4f}")

    train_loader = DataLoader(
        TensorDataset(tr_x, tr_y),
        batch_size=args.batch_size, shuffle=True,
        num_workers=args.num_workers, pin_memory=(args.device == "cuda"),
    )
    val_loader = DataLoader(
        TensorDataset(va_x, va_y),
        batch_size=args.batch_size, shuffle=False,
        num_workers=args.num_workers, pin_memory=(args.device == "cuda"),
    )
    return train_loader, val_loader, va_x, va_y, positive_frac


def main() -> int:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    ckpt_dir = args.output / "checkpoints"
    pred_dir = args.output / "predictions"
    ckpt_dir.mkdir(exist_ok=True)
    pred_dir.mkdir(exist_ok=True)

    import numpy as np
    import torch
    from torch import nn, optim
    from torchmetrics.functional.classification import (
        binary_f1_score, binary_jaccard_index,
    )

    sys.path.insert(0, str(Path(__file__).parent))
    from model import MiniUNet, count_parameters

    if args.device == "cuda" and not torch.cuda.is_available():
        raise SystemExit(
            "ERROR: --device cuda requested but torch.cuda.is_available() is False. "
            "Install GPU PyTorch:\n"
            "  pip install torch==2.7.1 torchvision==0.22.1 "
            "--index-url https://download.pytorch.org/whl/cu126"
        )

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    device = torch.device(args.device)
    train_loader, val_loader, va_x, va_y, pos_frac = _make_loaders(args)

    model = MiniUNet(in_channels=1, out_channels=1).to(device)
    print(f"[model] MiniUNet: {count_parameters(model):,} parameters, device={device}")

    pos_weight = torch.tensor([args.pos_weight], device=device)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = optim.Adam(model.parameters(), lr=args.lr)

    train_losses: list[float] = []
    val_losses: list[float] = []
    val_ious: list[float] = []
    val_dices: list[float] = []
    best_iou = -1.0
    best_epoch = -1

    for epoch in range(1, args.epochs + 1):
        # ---- train ----
        model.train()
        running = 0.0
        n_batches = 0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            logits = model(xb)
            loss = criterion(logits, yb)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            running += float(loss.item())
            n_batches += 1
        train_loss = running / max(1, n_batches)
        train_losses.append(train_loss)

        # ---- validate ----
        model.eval()
        running = 0.0
        iou_sum = 0.0
        dice_sum = 0.0
        n_seen = 0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                logits = model(xb)
                loss = criterion(logits, yb)
                running += float(loss.item()) * xb.size(0)
                preds_bin = (torch.sigmoid(logits) > 0.5).long()
                target_int = yb.long()
                # Per-batch metric (aggregate as micro-average by batch size)
                iou_sum += float(binary_jaccard_index(preds_bin, target_int)) * xb.size(0)
                dice_sum += float(binary_f1_score(preds_bin, target_int)) * xb.size(0)
                n_seen += xb.size(0)
        val_loss = running / max(1, n_seen)
        val_iou = iou_sum / max(1, n_seen)
        val_dice = dice_sum / max(1, n_seen)
        val_losses.append(val_loss)
        val_ious.append(val_iou)
        val_dices.append(val_dice)

        marker = ""
        if val_iou > best_iou:
            best_iou = val_iou
            best_epoch = epoch
            torch.save(model.state_dict(), ckpt_dir / "best_model.pth")
            marker = " *best*"
        print(f"[epoch {epoch:>3d}/{args.epochs}] "
              f"train={train_loss:.4f}  val={val_loss:.4f}  "
              f"IoU={val_iou:.4f}  Dice={val_dice:.4f}{marker}")

    # ---- final montage + per-image metrics using best model ----
    model.load_state_dict(torch.load(ckpt_dir / "best_model.pth", map_location=device))
    model.eval()

    import matplotlib.pyplot as plt
    with torch.no_grad():
        preds_all = torch.sigmoid(model(va_x.to(device))).cpu()
    preds_bin_all = (preds_all > 0.5).float()

    per_image = []
    for i in range(len(va_y)):
        p = preds_bin_all[i].long().unsqueeze(0)
        t = va_y[i].long().unsqueeze(0)
        per_image.append({
            "index": int(i),
            "iou": float(binary_jaccard_index(p, t)),
            "dice": float(binary_f1_score(p, t)),
        })
    (pred_dir / "per_image_metrics.json").write_text(
        json.dumps(per_image, indent=2)
    )

    n_show = min(args.n_montage, len(va_y))
    fig, axes = plt.subplots(n_show, 3, figsize=(9, 3 * n_show))
    titles = ["Input", "Ground Truth", "Prediction"]
    for i in range(n_show):
        row = axes[i] if n_show > 1 else axes
        for j, data in enumerate([va_x[i, 0], va_y[i, 0], preds_bin_all[i, 0]]):
            row[j].imshow(data.numpy(), cmap="gray", vmin=0, vmax=1)
            if i == 0:
                row[j].set_title(titles[j], fontsize=10)
            row[j].axis("off")
    plt.tight_layout()
    montage_path = pred_dir / f"montage_epoch{args.epochs:03d}.png"
    plt.savefig(montage_path, dpi=100)
    plt.close()

    # ---- metrics.json ----
    metrics = {
        "config": {
            "task": args.task,
            "image_size": args.image_size,
            "n_train": args.n_train,
            "n_val": args.n_val,
            "batch_size": args.batch_size,
            "epochs": args.epochs,
            "lr": args.lr,
            "device": args.device,
            "seed": args.seed,
            "pos_weight": args.pos_weight,
        },
        "positive_pixel_fraction_train": pos_frac,
        "n_parameters": count_parameters(model),
        "train_loss": train_losses,
        "val_loss": val_losses,
        "val_iou": val_ious,
        "val_dice": val_dices,
        "best_epoch": best_epoch,
        "best_val_iou": best_iou,
        "best_val_dice": val_dices[best_epoch - 1] if best_epoch > 0 else None,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    (args.output / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2)
    )
    print(f"[done] best val IoU = {best_iou:.4f} at epoch {best_epoch}")
    print(f"[done] wrote {args.output}/metrics.json, {montage_path}, "
          f"{pred_dir}/per_image_metrics.json, {ckpt_dir}/best_model.pth")
    return 0


if __name__ == "__main__":
    sys.exit(main())
