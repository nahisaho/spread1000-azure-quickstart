"""病理組織画像分類 (MedMNIST PathMNIST, 大腸組織 9 class)

- データ: 大腸組織 28×28 RGB × 9 クラス (adipose, background, debris,
  lymphocytes, mucus, smooth muscle, normal, cancer-stroma, adenocarcinoma)
- モデル: 軽量 CNN (Conv3+FC), ~95K params
- 学習: 5-10 epoch で val_acc ~0.85-0.90 (MedMNIST ベンチマーク上)
- 注意: 研究・教育目的のみ。診断・治療には使用不可。
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
import torch.nn.functional as F
from sklearn.metrics import classification_report, confusion_matrix
from torch.utils.data import DataLoader
from torchvision import transforms

from medmnist import PathMNIST


CLASS_NAMES = [
    "adipose", "background", "debris", "lymphocytes",
    "mucus", "smooth_muscle", "normal_colon", "cancer_stroma",
    "adenocarcinoma_epi",
]


class PathoCNN(nn.Module):
    def __init__(self, n_classes: int = 9):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
            nn.MaxPool2d(2),                                         # 14×14
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
            nn.MaxPool2d(2),                                         # 7×7
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),
        )
        self.head = nn.Sequential(
            nn.Flatten(), nn.Dropout(0.3), nn.Linear(128, n_classes)
        )

    def forward(self, x):
        return self.head(self.features(x))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--batch-size", type=int, default=128)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--train-frac", type=float, default=0.2, help="train データを高速化のため縮小 (0-1)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    if not (0.0 < args.train_frac <= 1.0):
        raise SystemExit(f"[error] --train-frac must be in (0, 1] (got {args.train_frac})")
    if args.epochs < 1:
        raise SystemExit(f"[error] --epochs must be >= 1 (got {args.epochs})")
    if args.batch_size < 1:
        raise SystemExit(f"[error] --batch-size must be >= 1 (got {args.batch_size})")

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = torch.device("cpu")

    data_dir = Path(__file__).resolve().parent.parent / "data"
    outputs = Path(__file__).resolve().parent.parent / "outputs"
    data_dir.mkdir(exist_ok=True); outputs.mkdir(exist_ok=True)

    tf = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
    ])

    print("[data] loading MedMNIST PathMNIST (auto-download ~205MB on first run)")
    train_ds = PathMNIST(split="train", transform=tf, download=True, root=str(data_dir))
    val_ds   = PathMNIST(split="val",   transform=tf, download=True, root=str(data_dir))
    test_ds  = PathMNIST(split="test",  transform=tf, download=True, root=str(data_dir))
    print(f"[data] train={len(train_ds)} val={len(val_ds)} test={len(test_ds)}")

    if args.train_frac < 1.0:
        n = int(len(train_ds) * args.train_frac)
        rng = np.random.default_rng(args.seed)
        idx = rng.choice(len(train_ds), n, replace=False).tolist()
        train_ds = torch.utils.data.Subset(train_ds, idx)
        print(f"[data] subsampled train to {len(train_ds)} (frac={args.train_frac})")

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    val_loader   = DataLoader(val_ds,   batch_size=args.batch_size, shuffle=False)
    test_loader  = DataLoader(test_ds,  batch_size=args.batch_size, shuffle=False)

    model = PathoCNN(n_classes=9).to(device)
    n_param = sum(p.numel() for p in model.parameters())
    print(f"[model] PathoCNN | params={n_param:,}")

    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    ce = nn.CrossEntropyLoss()
    hist = {"train_loss": [], "val_loss": [], "val_acc": []}
    best = 0.0

    for ep in range(1, args.epochs + 1):
        model.train()
        tl = 0.0
        for xb, yb in train_loader:
            yb = yb.squeeze(-1).long().to(device)
            xb = xb.to(device)
            opt.zero_grad()
            loss = ce(model(xb), yb)
            loss.backward(); opt.step()
            tl += loss.item() * yb.size(0)
        tl /= len(train_loader.dataset)

        model.eval()
        vl = 0.0; correct = 0
        with torch.no_grad():
            for xb, yb in val_loader:
                yb = yb.squeeze(-1).long().to(device); xb = xb.to(device)
                out = model(xb)
                vl += ce(out, yb).item() * yb.size(0)
                correct += (out.argmax(1) == yb).sum().item()
        vl /= len(val_ds); va = correct / len(val_ds)
        hist["train_loss"].append(tl); hist["val_loss"].append(vl); hist["val_acc"].append(va)
        mark = ""
        if va > best:
            best = va
            torch.save(model.state_dict(), outputs / "best_model.pt")
            mark = " *best*"
        print(f"[epoch {ep:2d}/{args.epochs}] train_loss={tl:.4f} val_loss={vl:.4f} val_acc={va:.3f}{mark}")

    # test
    model.load_state_dict(torch.load(outputs / "best_model.pt", map_location=device))
    model.eval()
    y_true, y_pred = [], []
    with torch.no_grad():
        for xb, yb in test_loader:
            yb_l = yb.squeeze(-1).long()
            out = model(xb.to(device))
            y_pred.extend(out.argmax(1).cpu().tolist()); y_true.extend(yb_l.tolist())
    test_acc = float(np.mean(np.array(y_true) == np.array(y_pred)))
    print(f"[test] acc={test_acc:.3f}")

    report = classification_report(y_true, y_pred, target_names=CLASS_NAMES, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_true, y_pred)

    fig, ax1 = plt.subplots(figsize=(7, 4))
    ax1.plot(hist["train_loss"], label="train_loss"); ax1.plot(hist["val_loss"], label="val_loss")
    ax1.set_xlabel("epoch"); ax1.set_ylabel("loss"); ax1.legend(loc="upper left")
    ax2 = ax1.twinx(); ax2.plot(hist["val_acc"], "g--", label="val_acc"); ax2.set_ylabel("val_acc"); ax2.legend(loc="lower right")
    fig.tight_layout(); fig.savefig(outputs / "loss_acc.png", dpi=120); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(9)); ax.set_yticks(range(9))
    ax.set_xticklabels(CLASS_NAMES, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(CLASS_NAMES, fontsize=8)
    ax.set_xlabel("predicted"); ax.set_ylabel("true"); ax.set_title(f"test acc={test_acc:.3f}")
    for i in range(9):
        for j in range(9):
            ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=6, color="black" if cm[i, j] < cm.max()/2 else "white")
    fig.colorbar(im); fig.tight_layout(); fig.savefig(outputs / "confusion_matrix.png", dpi=120); plt.close(fig)

    metrics = {"n_params": n_param, "best_val_acc": best, "test_acc": test_acc,
               "per_class": {k: report[k] for k in CLASS_NAMES}}
    (outputs / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False))
    print("[done] outputs/ written")


if __name__ == "__main__":
    main()
