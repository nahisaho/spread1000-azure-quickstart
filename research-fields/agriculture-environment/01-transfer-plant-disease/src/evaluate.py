"""テストセットで転移学習モデルを評価し、混同行列を保存する."""
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
from sklearn.metrics import confusion_matrix, classification_report
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"


def build_transforms_eval():
    return transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    p.add_argument("--batch-size", type=int, default=16)
    return p.parse_args()


def main():
    a = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    device = torch.device(a.device)

    ck = torch.load(a.model, map_location=device, weights_only=True)
    class_ids = list(ck["class_ids"])
    n_classes = int(ck["n_classes"])
    id_map = {orig: new for new, orig in enumerate(class_ids)}

    test_ds_full = datasets.Flowers102(str(DATA_DIR), split="test", download=False,
                                       transform=build_transforms_eval())
    labels = getattr(test_ds_full, "_labels", None)
    keep_idx = [i for i, lab in enumerate(labels) if lab in id_map]
    from torch.utils.data import Subset

    class Remapped(torch.utils.data.Dataset):
        def __init__(self, subset, id_map): self.s = subset; self.m = id_map
        def __len__(self): return len(self.s)
        def __getitem__(self, i):
            x, y = self.s[i]
            return x, self.m[int(y)]

    test_ds = Remapped(Subset(test_ds_full, keep_idx), id_map)
    loader = DataLoader(test_ds, batch_size=a.batch_size, shuffle=False, num_workers=0)
    print(f"[data] test samples: {len(test_ds)}")

    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, n_classes)
    model.load_state_dict(ck["model_state_dict"])
    model = model.to(device); model.eval()

    all_y, all_pred = [], []
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            pred = model(x).argmax(dim=1)
            all_y.extend(y.cpu().tolist())
            all_pred.extend(pred.cpu().tolist())

    acc = float(np.mean(np.array(all_y) == np.array(all_pred)))
    cm = confusion_matrix(all_y, all_pred)
    report = classification_report(all_y, all_pred, output_dict=True, zero_division=0)
    print(f"[eval] test accuracy = {acc:.4f}")
    print(classification_report(all_y, all_pred, zero_division=0))

    fig, ax = plt.subplots(figsize=(5, 5))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(n_classes)); ax.set_yticks(range(n_classes))
    ax.set_xlabel("predicted"); ax.set_ylabel("true")
    ax.set_title(f"Confusion matrix (acc={acc:.3f})")
    for i in range(n_classes):
        for j in range(n_classes):
            ax.text(j, i, cm[i, j], ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    plt.tight_layout(); plt.savefig(OUT_DIR / "confusion_matrix.png", dpi=120); plt.close()

    with (OUT_DIR / "eval_metrics.json").open("w", encoding="utf-8") as f:
        json.dump({"test_accuracy": round(acc, 4), "confusion_matrix": cm.tolist(),
                   "classification_report": report}, f, indent=2)
    print(f"[eval] saved → {OUT_DIR}/confusion_matrix.png, eval_metrics.json")


if __name__ == "__main__":
    main()
