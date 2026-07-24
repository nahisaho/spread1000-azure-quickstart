"""テストセットで転移学習モデルを評価し、混同行列を保存する."""
from __future__ import annotations
import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import (
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, models, transforms

sys.path.insert(0, str(Path(__file__).parent))
from _argtypes import bounded_int  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"


def build_transforms_eval() -> transforms.Compose:
    return transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


def assert_finite(t: torch.Tensor, name: str) -> None:
    """Raise RuntimeError if tensor contains NaN or Inf (HIGH 4)."""
    if not torch.isfinite(t).all():
        raise RuntimeError(
            f"Non-finite values in {name}: min={t.min().item():.4g} max={t.max().item():.4g}"
        )


def parse_args():
    import argparse
    p = argparse.ArgumentParser(description="Evaluate a saved transfer-learning checkpoint")
    p.add_argument("--model", type=Path, required=True, help="Path to best_model.pt")
    p.add_argument("--device", choices=("cpu", "cuda", "mps"), default="cpu")
    p.add_argument(
        "--batch-size", type=bounded_int("batch-size", 1, 256), default=16
    )
    p.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help=(
            "Custom dataset root with test/ subfolder (ImageFolder-compatible). "
            "If omitted, uses Flowers102 test split (class_ids from checkpoint)."
        ),
    )
    return p.parse_args()


class RemappedSubset(torch.utils.data.Dataset):
    def __init__(self, subset: Subset, id_map: dict[int, int]) -> None:
        self.s = subset
        self.m = id_map

    def __len__(self) -> int:
        return len(self.s)

    def __getitem__(self, i: int):
        x, y = self.s[i]
        return x, self.m[int(y)]


def main() -> None:
    a = parse_args()

    # --- Preflights (HIGH 3) ---
    if not a.model.exists():
        raise SystemExit(f"Model file not found: {a.model}")
    if a.device == "cuda" and not torch.cuda.is_available():
        raise SystemExit("--device cuda: CUDA is not available on this machine")
    if a.device == "mps" and not (
        hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
    ):
        raise SystemExit("--device mps: MPS is not available on this machine")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    device = torch.device(a.device)

    # --- Load checkpoint ---
    ck = torch.load(a.model, map_location=device, weights_only=True)

    # NaN guard on loaded weights (HIGH 4)
    for k, v in ck["model_state_dict"].items():
        if isinstance(v, torch.Tensor) and not torch.isfinite(v).all():
            raise RuntimeError(f"Non-finite value in checkpoint tensor '{k}'")

    n_classes = int(ck["n_classes"])

    # HIGH 5: read class_names from checkpoint; do NOT hardcode Flowers102
    if "class_names" in ck:
        class_names: list[str] = list(ck["class_names"])
    else:
        # Legacy checkpoint fallback
        class_ids = list(ck.get("class_ids", range(n_classes)))
        class_names = [f"flower_{i}" for i in class_ids]

    # --- Test dataset (HIGH 5) ---
    if a.data_root is not None:
        test_dir = (a.data_root / "test").resolve()
        if not test_dir.is_dir():
            raise SystemExit(f"--data-root: missing test/ subfolder: {test_dir}")
        test_ds: torch.utils.data.Dataset = datasets.ImageFolder(
            str(test_dir), transform=build_transforms_eval()
        )
        print(f"[data] custom test set: {len(test_ds)} samples from {test_dir}")
    else:
        # Use Flowers102 test split, filtered by class_ids from checkpoint
        if "class_ids" in ck:
            class_ids_orig = list(ck["class_ids"])
        else:
            class_ids_orig = list(range(n_classes))
        id_map = {orig: new for new, orig in enumerate(class_ids_orig)}
        test_full = datasets.Flowers102(
            str(DATA_DIR), split="test", download=False,
            transform=build_transforms_eval()
        )
        labels = getattr(test_full, "_labels", None)
        if labels is None:
            labels = [test_full[i][1] for i in range(len(test_full))]
        keep_idx = [i for i, lab in enumerate(labels) if lab in id_map]
        test_ds = RemappedSubset(Subset(test_full, keep_idx), id_map)
        print(f"[data] Flowers102 test samples: {len(test_ds)}")

    loader = DataLoader(test_ds, batch_size=a.batch_size, shuffle=False, num_workers=0)

    # --- Model ---
    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, n_classes)
    model.load_state_dict(ck["model_state_dict"])
    model = model.to(device)
    model.eval()

    # --- Inference ---
    all_y: list[int] = []
    all_pred: list[int] = []
    with torch.no_grad():
        for x, y in loader:
            assert_finite(x, "input batch")  # HIGH 4
            x, y = x.to(device), y.to(device)
            logits = model(x)
            assert_finite(logits, "logits")  # HIGH 4
            if not math.isfinite(logits.max().item()):
                raise RuntimeError("Non-finite logits during evaluation")
            pred = logits.argmax(dim=1)
            all_y.extend(y.cpu().tolist())
            all_pred.extend(pred.cpu().tolist())

    # --- Metrics ---
    acc = float(np.mean(np.array(all_y) == np.array(all_pred)))
    macro_f1 = float(f1_score(all_y, all_pred, average="macro", zero_division=0))
    bal_acc = float(balanced_accuracy_score(all_y, all_pred))
    cm = confusion_matrix(all_y, all_pred)
    report = classification_report(all_y, all_pred, output_dict=True, zero_division=0)
    print(f"[eval] test accuracy = {acc:.4f}  macro-F1 = {macro_f1:.4f}  "
          f"balanced_accuracy = {bal_acc:.4f}")
    print(classification_report(all_y, all_pred, target_names=class_names[:n_classes], zero_division=0))

    # --- Confusion matrix plot ---
    fig, ax = plt.subplots(figsize=(max(5, n_classes), max(5, n_classes)))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(n_classes))
    ax.set_yticks(range(n_classes))
    ax.set_xticklabels(class_names[:n_classes], rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(class_names[:n_classes], fontsize=8)
    ax.set_xlabel("predicted")
    ax.set_ylabel("true")
    ax.set_title(f"Confusion matrix (acc={acc:.3f}, macro-F1={macro_f1:.3f})")
    for i in range(n_classes):
        for j in range(n_classes):
            ax.text(
                j, i, cm[i, j], ha="center", va="center",
                color="white" if cm.max() > 0 and cm[i, j] > cm.max() / 2 else "black",
                fontsize=7,
            )
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "confusion_matrix.png", dpi=120)
    plt.close()

    # --- Save metrics (HIGH 4: allow_nan=False) ---
    with (OUT_DIR / "eval_metrics.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "test_accuracy": round(acc, 4),
                "test_macro_f1": round(macro_f1, 4),
                "test_balanced_accuracy": round(bal_acc, 4),
                "class_names": class_names,
                "confusion_matrix": cm.tolist(),
                "classification_report": report,
            },
            f,
            indent=2,
            allow_nan=False,  # HIGH 4
        )
    print(f"[eval] saved → {OUT_DIR}/confusion_matrix.png, eval_metrics.json")


if __name__ == "__main__":
    main()
