"""1D-CNN でハイパースペクトル分類 (合成 Indian Pines 相当)

- 入力: (N, 1, 200) 反射率スペクトル
- モデル: Conv1d(1→16, k=7) → MaxPool → Conv1d(16→32, k=5) → MaxPool →
         Conv1d(32→64, k=3) → GAP → Linear(64→n_classes)
- 学習/評価: 6:2:2 split、CrossEntropy、Adam
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, TensorDataset

from dataset import CLASS_NAMES, generate


class HSICNN(nn.Module):
    def __init__(self, n_bands: int = 200, n_classes: int = 6):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv1d(1, 16, kernel_size=7, padding=3),
            nn.BatchNorm1d(16), nn.ReLU(),
            nn.MaxPool1d(2),
            nn.Conv1d(16, 32, kernel_size=5, padding=2),
            nn.BatchNorm1d(32), nn.ReLU(),
            nn.MaxPool1d(2),
            nn.Conv1d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm1d(64), nn.ReLU(),
            nn.AdaptiveAvgPool1d(1),
        )
        self.head = nn.Linear(64, n_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.features(x).squeeze(-1)
        return self.head(h)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--n-per-class", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    outputs = Path(__file__).resolve().parent.parent / "outputs"
    outputs.mkdir(exist_ok=True)

    print(f"[data] generating synthetic HSI: {args.n_per_class}/class × 6 classes × 200 bands")
    X, y, class_names = generate(n_per_class=args.n_per_class, seed=args.seed)
    print(f"[data] X.shape={X.shape} y.shape={y.shape}")

    X_tv, X_test, y_tv, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=args.seed)
    X_train, X_val, y_train, y_val = train_test_split(X_tv, y_tv, test_size=0.25, stratify=y_tv, random_state=args.seed)
    print(f"[data] train={len(y_train)} val={len(y_val)} test={len(y_test)}")

    def to_loader(Xa, ya, shuffle):
        ds = TensorDataset(torch.from_numpy(Xa).unsqueeze(1), torch.from_numpy(ya))
        return DataLoader(ds, batch_size=args.batch_size, shuffle=shuffle)

    train_loader = to_loader(X_train, y_train, True)
    val_loader = to_loader(X_val, y_val, False)
    test_loader = to_loader(X_test, y_test, False)

    device = torch.device("cpu")
    model = HSICNN(n_bands=200, n_classes=len(class_names)).to(device)
    n_param = sum(p.numel() for p in model.parameters())
    print(f"[model] HSI-CNN | params={n_param:,}")

    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    ce = nn.CrossEntropyLoss()

    hist = {"train_loss": [], "val_loss": [], "val_acc": []}
    best_val = 0.0
    for ep in range(1, args.epochs + 1):
        model.train()
        # BN OK to train since we're training end-to-end
        tl = 0.0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            loss = ce(model(xb), yb)
            loss.backward()
            opt.step()
            tl += loss.item() * yb.size(0)
        tl /= len(train_loader.dataset)

        model.eval()
        vl = 0.0
        correct = 0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                out = model(xb)
                vl += ce(out, yb).item() * yb.size(0)
                correct += (out.argmax(1) == yb).sum().item()
        vl /= len(val_loader.dataset)
        va = correct / len(val_loader.dataset)
        hist["train_loss"].append(tl)
        hist["val_loss"].append(vl)
        hist["val_acc"].append(va)
        star = ""
        if va > best_val:
            best_val = va
            torch.save(model.state_dict(), outputs / "best_model.pt")
            star = " *best*"
        print(f"[epoch {ep:2d}/{args.epochs}] train_loss={tl:.4f} val_loss={vl:.4f} val_acc={va:.3f}{star}")

    # test with best
    model.load_state_dict(torch.load(outputs / "best_model.pt", map_location=device))
    model.eval()
    y_true_all, y_pred_all = [], []
    with torch.no_grad():
        for xb, yb in test_loader:
            out = model(xb)
            y_pred_all.extend(out.argmax(1).cpu().tolist())
            y_true_all.extend(yb.tolist())
    test_acc = float(np.mean(np.array(y_true_all) == np.array(y_pred_all)))
    print(f"[test] acc={test_acc:.3f}")
    report = classification_report(y_true_all, y_pred_all, target_names=class_names, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_true_all, y_pred_all)

    # plots
    fig, ax1 = plt.subplots(figsize=(7, 4))
    ax1.plot(hist["train_loss"], label="train_loss")
    ax1.plot(hist["val_loss"], label="val_loss")
    ax1.set_xlabel("epoch"); ax1.set_ylabel("loss"); ax1.legend(loc="upper left")
    ax2 = ax1.twinx(); ax2.plot(hist["val_acc"], "g--", label="val_acc"); ax2.set_ylabel("val_acc"); ax2.legend(loc="lower right")
    fig.tight_layout(); fig.savefig(outputs / "loss_acc.png", dpi=120); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(class_names))); ax.set_yticks(range(len(class_names)))
    ax.set_xticklabels(class_names, rotation=45, ha="right"); ax.set_yticklabels(class_names)
    ax.set_xlabel("predicted"); ax.set_ylabel("true"); ax.set_title(f"test acc={test_acc:.3f}")
    for i in range(len(class_names)):
        for j in range(len(class_names)):
            ax.text(j, i, cm[i, j], ha="center", va="center", color="black" if cm[i, j] < cm.max() / 2 else "white")
    fig.colorbar(im); fig.tight_layout(); fig.savefig(outputs / "confusion_matrix.png", dpi=120); plt.close(fig)

    # sample spectra plot
    fig, ax = plt.subplots(figsize=(8, 4))
    for c in range(len(class_names)):
        idx = np.where(y == c)[0][0]
        ax.plot(X[idx], label=class_names[c])
    ax.set_xlabel("band"); ax.set_ylabel("reflectance"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(outputs / "sample_spectra.png", dpi=120); plt.close(fig)

    metrics = {
        "n_params": n_param,
        "best_val_acc": best_val,
        "test_acc": test_acc,
        "per_class": {k: report[k] for k in class_names},
    }
    (outputs / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False))
    print("[done] outputs/ written")


if __name__ == "__main__":
    main()
