"""
UCI HAR コンパクト 1D-CNN の学習スクリプト.

- 公式 test は最後まで触らない (evaluate.py で使用)
- 公式 train (7,352 窓, 21 被験者) を被験者独立で 4:1 分割 (StratifiedGroupKFold)
- チャネル別 mean/std は train 被験者のみで fit
- val macro-F1 で早期停止 (patience=4)
- 成果物: outputs/best_model.pt, outputs/normalization.npz, outputs/loss_curve.png
"""
from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # ヘッドレス環境用
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedGroupKFold
from torch.utils.data import DataLoader, TensorDataset

from model import BiosignalCNN, num_parameters

ROOT = Path(__file__).resolve().parents[1]
NPZ_PATH = ROOT / "data" / "har_windows.npz"
OUT_DIR = ROOT / "outputs"


def set_seed(seed: int) -> torch.Generator:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    return torch.Generator().manual_seed(seed)


def compute_norm(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(N, C, T) → チャネル別 mean/std (train のみで fit)."""
    mean = X.mean(axis=(0, 2), keepdims=True).astype(np.float32)
    std = X.std(axis=(0, 2), keepdims=True).astype(np.float32).clip(min=1e-6)
    return mean, std


def apply_norm(X: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    return ((X - mean) / std).astype(np.float32)


def evaluate(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    criterion: nn.Module,
) -> tuple[float, float]:
    """returns (mean_loss, macro_f1)."""
    model.eval()
    losses, preds, targets = [], [], []
    with torch.no_grad():
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            logits = model(xb)
            loss = criterion(logits, yb)
            losses.append(loss.item() * yb.size(0))
            preds.append(logits.argmax(-1).cpu().numpy())
            targets.append(yb.cpu().numpy())
    n = sum(len(t) for t in targets)
    y_pred = np.concatenate(preds)
    y_true = np.concatenate(targets)
    return sum(losses) / n, float(f1_score(y_true, y_pred, average="macro"))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    p.add_argument("--epochs", type=int, default=15)
    p.add_argument("--batch-size", type=int, default=128)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--weight-decay", type=float, default=1e-4)
    p.add_argument("--dropout", type=float, default=0.30)
    p.add_argument("--patience", type=int, default=4, help="early-stopping patience (epochs)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="成果物ディレクトリ (省略時: <repo>/outputs)",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # CPU スレッド数を抑制 (educational 環境で安定化)
    if args.device == "cpu":
        torch.set_num_threads(min(8, os.cpu_count() or 1))

    generator = set_seed(args.seed)

    if not NPZ_PATH.exists():
        raise FileNotFoundError(
            f"{NPZ_PATH} が見つかりません。先に prepare_data.py を実行してください。"
        )
    data = np.load(NPZ_PATH, allow_pickle=True)
    X_all, y_all, subj_all = data["X_train"], data["y_train"], data["subj_train"]
    activities = [str(a) for a in data["activities"].tolist()]
    print(f"[data] official train: X={X_all.shape}, subjects={len(set(subj_all.tolist()))}")

    # 被験者独立 4:1 分割 (StratifiedGroupKFold, 1 fold のみを val として使用)
    skf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=args.seed)
    train_idx, val_idx = next(skf.split(X_all, y_all, groups=subj_all))
    train_subj = sorted(set(subj_all[train_idx].tolist()))
    val_subj = sorted(set(subj_all[val_idx].tolist()))
    assert not (set(train_subj) & set(val_subj)), "subject leak between train/val"
    print(f"[split] train subjects ({len(train_subj)}): {train_subj}")
    print(f"[split] val   subjects ({len(val_subj)}): {val_subj}")

    X_train, y_train = X_all[train_idx], y_all[train_idx]
    X_val, y_val = X_all[val_idx], y_all[val_idx]

    mean, std = compute_norm(X_train)
    X_train = apply_norm(X_train, mean, std)
    X_val = apply_norm(X_val, mean, std)

    train_ds = TensorDataset(torch.from_numpy(X_train), torch.from_numpy(y_train))
    val_ds = TensorDataset(torch.from_numpy(X_val), torch.from_numpy(y_val))

    # num_workers=0: Windows/教材環境で最も安定 (spawn オーバーヘッドも避ける)
    train_loader = DataLoader(
        train_ds, batch_size=args.batch_size, shuffle=True,
        num_workers=0, generator=generator,
    )
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)

    device = torch.device(args.device)
    model = BiosignalCNN(n_channels=9, n_classes=6, dropout=args.dropout).to(device)
    print(f"[model] BiosignalCNN, trainable params = {num_parameters(model):,}")

    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.lr, weight_decay=args.weight_decay
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    criterion = nn.CrossEntropyLoss()

    out_dir = args.output_dir or OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    history = {"train_loss": [], "val_loss": [], "val_macro_f1": []}
    best_f1, best_epoch, patience_left = -1.0, 0, args.patience
    best_ckpt = out_dir / "best_model.pt"

    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss, n = 0.0, 0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * yb.size(0)
            n += yb.size(0)
        train_loss = total_loss / n
        val_loss, val_f1 = evaluate(model, val_loader, device, criterion)
        scheduler.step()

        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["val_macro_f1"].append(val_f1)

        marker = ""
        if val_f1 > best_f1:
            best_f1, best_epoch, patience_left = val_f1, epoch, args.patience
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "epoch": epoch,
                    "val_macro_f1": val_f1,
                    "activities": activities,
                    "n_channels": 9,
                    "n_classes": 6,
                    "dropout": args.dropout,
                },
                best_ckpt,
            )
            marker = "  ★ (best, saved)"
        else:
            patience_left -= 1
        print(
            f"[epoch {epoch:2d}/{args.epochs}] train_loss={train_loss:.4f} "
            f"val_loss={val_loss:.4f} val_macro_F1={val_f1:.4f}{marker}"
        )
        if patience_left <= 0:
            print(f"[early-stop] no val macro-F1 improvement for {args.patience} epochs")
            break

    print(f"[train] best val macro-F1 = {best_f1:.4f} (epoch {best_epoch})")

    # 標準化統計を保存 (evaluate.py で train と同一を適用するため必須)
    np.savez(out_dir / "normalization.npz", mean=mean, std=std)

    # loss/F1 曲線
    fig, ax1 = plt.subplots(figsize=(7, 4))
    epochs_x = range(1, len(history["train_loss"]) + 1)
    ax1.plot(epochs_x, history["train_loss"], label="train loss", color="tab:blue")
    ax1.plot(epochs_x, history["val_loss"], label="val loss", color="tab:orange")
    ax1.set_xlabel("epoch")
    ax1.set_ylabel("loss")
    ax1.legend(loc="upper left")
    ax2 = ax1.twinx()
    ax2.plot(epochs_x, history["val_macro_f1"], label="val macro-F1",
             color="tab:green", linestyle="--")
    ax2.set_ylabel("macro-F1")
    ax2.legend(loc="lower right")
    plt.title("UCI HAR CompactCNN — train/val curves")
    plt.tight_layout()
    plt.savefig(out_dir / "loss_curve.png", dpi=120)
    plt.close()

    with (out_dir / "train_history.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "history": history,
                "best_val_macro_f1": best_f1,
                "best_epoch": best_epoch,
                "trained_epochs": len(history["train_loss"]),
                "train_subjects": train_subj,
                "val_subjects": val_subj,
                "n_train_windows": int(X_train.shape[0]),
                "n_val_windows": int(X_val.shape[0]),
                "seed": args.seed,
                "device": args.device,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    print(f"[train] saved → {best_ckpt}, {out_dir}/normalization.npz, loss_curve.png")


if __name__ == "__main__":
    main()
