"""
Transfer learning quickstart:
- Load ResNet18 with ImageNet weights (torchvision)
- Freeze backbone, replace fc head with 5-class linear layer
- Train on Flowers102 subset (5 classes)
"""
from __future__ import annotations
import argparse
import json
import os
import random
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, models, transforms

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"


def set_seed(seed: int) -> None:
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)


def build_transforms(train: bool):
    normalize = transforms.Normalize(
        mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
    )
    if train:
        return transforms.Compose([
            transforms.Resize(256),
            transforms.RandomResizedCrop(224, scale=(0.7, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            normalize,
        ])
    return transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        normalize,
    ])


def filter_by_classes(dataset, class_ids: list[int]) -> Subset:
    """Filter to only include samples of specified class IDs and remap labels 0..K-1."""
    # torchvision Flowers102 stores labels in `_labels`.
    labels = getattr(dataset, "_labels", None)
    if labels is None:
        # fallback via iterating (slow but robust)
        labels = [dataset[i][1] for i in range(len(dataset))]
    id_map = {orig: new for new, orig in enumerate(class_ids)}
    keep = [i for i, lab in enumerate(labels) if lab in id_map]
    # remap in-place is not possible with Subset; wrap with a mapping dataset
    return Subset(dataset, keep), id_map


class RemappedDataset(torch.utils.data.Dataset):
    """Wraps a Subset and remaps labels via id_map."""
    def __init__(self, subset: Subset, id_map: dict[int, int]):
        self.subset = subset
        self.id_map = id_map

    def __len__(self):
        return len(self.subset)

    def __getitem__(self, idx):
        x, y = self.subset[idx]
        return x, self.id_map[int(y)]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    p.add_argument("--epochs", type=int, default=8)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--n-classes", type=int, default=5)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def main():
    a = parse_args()
    if a.device == "cpu":
        torch.set_num_threads(min(8, os.cpu_count() or 1))
    set_seed(a.seed)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    device = torch.device(a.device)

    print(f"[data] downloading Flowers102 to {DATA_DIR} (~330MB, only first time)")
    train_full = datasets.Flowers102(str(DATA_DIR), split="train", download=True,
                                     transform=build_transforms(train=True))
    val_full = datasets.Flowers102(str(DATA_DIR), split="val", download=True,
                                   transform=build_transforms(train=False))
    test_full = datasets.Flowers102(str(DATA_DIR), split="test", download=True,
                                    transform=build_transforms(train=False))

    # 先頭 n_classes クラスを選ぶ (0..n_classes-1)
    class_ids = list(range(a.n_classes))
    train_sub, id_map = filter_by_classes(train_full, class_ids)
    val_sub, _ = filter_by_classes(val_full, class_ids)
    test_sub, _ = filter_by_classes(test_full, class_ids)
    train_ds = RemappedDataset(train_sub, id_map)
    val_ds = RemappedDataset(val_sub, id_map)
    test_ds = RemappedDataset(test_sub, id_map)
    print(f"[data] classes={class_ids}  train={len(train_ds)} val={len(val_ds)} test={len(test_ds)}")

    tr_loader = DataLoader(train_ds, batch_size=a.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=a.batch_size, shuffle=False, num_workers=0)

    # Model: ResNet18 backbone frozen, replace fc
    weights = models.ResNet18_Weights.IMAGENET1K_V1
    model = models.resnet18(weights=weights)
    for p in model.parameters():
        p.requires_grad = False
    model.fc = nn.Linear(model.fc.in_features, a.n_classes)  # trainable
    model = model.to(device)
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"[model] ResNet18 (backbone frozen) | trainable={trainable:,} / total={total:,}")

    opt = torch.optim.Adam(model.fc.parameters(), lr=a.lr)
    ce = nn.CrossEntropyLoss()

    history = {"train_loss": [], "val_loss": [], "val_acc": []}
    best_val_acc = -1.0
    ckpt_path = OUT_DIR / "best_model.pt"

    for epoch in range(1, a.epochs + 1):
        # train
        model.train()
        # ResNet18 backbone は eval() 相当で BN 統計を凍結
        for m in model.modules():
            if isinstance(m, nn.BatchNorm2d):
                m.eval()
        tr_loss = 0.0; n = 0
        for x, y in tr_loader:
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            logits = model(x)
            loss = ce(logits, y)
            loss.backward()
            opt.step()
            tr_loss += loss.item() * x.size(0)
            n += x.size(0)
        tr_loss /= n

        # val
        model.eval()
        val_loss = 0.0; n = 0; correct = 0
        with torch.no_grad():
            for x, y in val_loader:
                x, y = x.to(device), y.to(device)
                logits = model(x)
                val_loss += ce(logits, y).item() * x.size(0)
                correct += (logits.argmax(dim=1) == y).sum().item()
                n += x.size(0)
        val_loss /= n
        val_acc = correct / n

        history["train_loss"].append(tr_loss)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)

        marker = ""
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save({
                "model_state_dict": model.state_dict(),
                "n_classes": a.n_classes,
                "class_ids": class_ids,
                "val_acc": val_acc,
            }, ckpt_path)
            marker = "  *best*"
        print(f"[epoch {epoch:2d}/{a.epochs}] train_loss={tr_loss:.4f}  "
              f"val_loss={val_loss:.4f}  val_acc={val_acc:.3f}{marker}")

    # プロット
    fig, ax1 = plt.subplots(figsize=(7, 4))
    ax1.plot(history["train_loss"], label="train_loss")
    ax1.plot(history["val_loss"], label="val_loss")
    ax1.set_xlabel("epoch"); ax1.set_ylabel("loss"); ax1.legend(loc="upper left")
    ax2 = ax1.twinx()
    ax2.plot(history["val_acc"], color="green", linestyle="--", label="val_acc")
    ax2.set_ylabel("val accuracy"); ax2.legend(loc="upper right")
    plt.title(f"Transfer learning ResNet18 → {a.n_classes} classes  (best val acc {best_val_acc:.3f})")
    plt.tight_layout(); plt.savefig(OUT_DIR / "loss_acc.png", dpi=120); plt.close()

    with (OUT_DIR / "train_metrics.json").open("w", encoding="utf-8") as f:
        json.dump({"best_val_acc": round(best_val_acc, 4),
                   "trainable_params": trainable, "total_params": total,
                   "epochs": a.epochs, "class_ids": class_ids, "seed": a.seed}, f, indent=2)
    print(f"[train] saved → {ckpt_path}, loss_acc.png, train_metrics.json")


if __name__ == "__main__":
    main()
