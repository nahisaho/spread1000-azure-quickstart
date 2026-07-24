"""
Transfer learning quickstart:
- Load ResNet18 with ImageNet weights (torchvision)
- Freeze backbone, replace fc head with N-class linear layer
- Train on Flowers102 subset or custom --data-root dataset
"""
from __future__ import annotations
import json
import math
import os
import random
import subprocess
import sys
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import balanced_accuracy_score, f1_score
from torch.utils.data import DataLoader, Subset, WeightedRandomSampler
from torchvision import datasets, models, transforms

# _argtypes is in the same package directory
sys.path.insert(0, str(Path(__file__).parent))
from _argtypes import bounded_float, bounded_int  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def setup_determinism() -> None:
    """Enable deterministic mode for reproducibility (MED 10)."""
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    torch.use_deterministic_algorithms(True, warn_only=True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def build_transforms(train: bool) -> transforms.Compose:
    normalize = transforms.Normalize(
        mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
    )
    if train:
        # Train: RandomResizedCrop + RandomHorizontalFlip for augmentation
        return transforms.Compose([
            transforms.Resize(256),
            transforms.RandomResizedCrop(224, scale=(0.7, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            normalize,
        ])
    # Val/Test: deterministic CenterCrop
    return transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        normalize,
    ])


def filter_by_classes(dataset, class_ids: list[int]) -> tuple[Subset, dict[int, int]]:
    """Filter Flowers102 to the given class IDs and remap labels 0..K-1."""
    labels = getattr(dataset, "_labels", None)
    if labels is None:
        labels = [dataset[i][1] for i in range(len(dataset))]
    id_map = {orig: new for new, orig in enumerate(class_ids)}
    keep = [i for i, lab in enumerate(labels) if lab in id_map]
    return Subset(dataset, keep), id_map


class RemappedDataset(torch.utils.data.Dataset):
    """Wraps a Subset and remaps original labels via id_map."""
    def __init__(self, subset: Subset, id_map: dict[int, int]) -> None:
        self.subset = subset
        self.id_map = id_map

    def __len__(self) -> int:
        return len(self.subset)

    def __getitem__(self, idx: int):
        x, y = self.subset[idx]
        return x, self.id_map[int(y)]


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


def assert_finite(t: torch.Tensor, name: str) -> None:
    """Raise RuntimeError if tensor contains NaN or Inf (HIGH 4)."""
    if not torch.isfinite(t).all():
        raise RuntimeError(
            f"Non-finite values in {name}: min={t.min().item():.4g} max={t.max().item():.4g}"
        )


def compute_class_weights(labels: list[int], n_classes: int) -> torch.Tensor:
    counts = Counter(labels)
    total = len(labels)
    w = torch.zeros(n_classes)
    for c in range(n_classes):
        w[c] = total / (n_classes * max(counts.get(c, 1), 1))
    return w


def get_all_labels(ds: torch.utils.data.Dataset) -> list[int]:
    return [ds[i][1] for i in range(len(ds))]


def parse_args():
    import argparse
    p = argparse.ArgumentParser(
        description="Transfer learning quickstart — ResNet18 head-only or fine-tune"
    )
    p.add_argument("--device", choices=("cpu", "cuda", "mps"), default="cpu")
    p.add_argument(
        "--epochs",
        type=bounded_int("epochs", 1, 100),
        default=8,
        help="Training epochs [1, 100]",
    )
    p.add_argument(
        "--allow-long-run",
        action="store_true",
        help="Required when --epochs > 30 (safeguard for long CPU runs)",
    )
    p.add_argument(
        "--lr",
        type=bounded_float("lr", 0.0, 1.0, inclusive_min=False, inclusive_max=True),
        default=1e-3,
        help="Learning rate, (0, 1]",
    )
    p.add_argument(
        "--batch-size",
        type=bounded_int("batch-size", 1, 256),
        default=16,
        help="Batch size [1, 256]",
    )
    p.add_argument(
        "--n-classes",
        type=bounded_int("n-classes", 2, 102),
        default=5,
        help="Number of Flowers102 classes [2, 102] (ignored with --data-root)",
    )
    p.add_argument(
        "--seed",
        type=bounded_int("seed", 0, 2**32 - 1),
        default=42,
        help="Random seed [0, 2^32-1]",
    )
    p.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help=(
            "Custom dataset root with train/, val/, test/ subfolders "
            "(ImageFolder-compatible). Overrides Flowers102."
        ),
    )
    p.add_argument(
        "--balance",
        choices=("none", "weighted-loss", "weighted-sampler"),
        default="none",
        help="Class imbalance strategy (HIGH 7). Do not combine.",
    )
    p.add_argument(
        "--best-metric",
        choices=("val_acc", "val_macro_f1"),
        default="val_acc",
        help="Metric for checkpoint selection. Prefer val_macro_f1 on imbalanced data.",
    )
    p.add_argument(
        "--fine-tune",
        action="store_true",
        help="Unfreeze layer4 with lower lr (HIGH 8). Default: head-only.",
    )
    p.add_argument(
        "--bn-train",
        action="store_true",
        help="(--fine-tune only) keep layer4 BatchNorm in train mode.",
    )
    p.add_argument(
        "--scheduler",
        choices=("none", "cosine", "step"),
        default="none",
        help="LR scheduler (HIGH 8).",
    )
    p.add_argument(
        "--patience",
        type=int,
        default=None,
        help="Early stopping patience (epochs without improvement). None = disabled.",
    )
    return p.parse_args()


def main() -> None:
    a = parse_args()

    # --- Guards (HIGH 3) ---
    if a.epochs > 30 and not a.allow_long_run:
        raise SystemExit(
            f"--epochs {a.epochs} > 30 requires --allow-long-run "
            "(long CPU run safeguard; pass the flag to confirm)"
        )
    if a.device == "cuda" and not torch.cuda.is_available():
        raise SystemExit("--device cuda: CUDA is not available on this machine")
    if a.device == "mps" and not (
        hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
    ):
        raise SystemExit("--device mps: MPS is not available on this machine")

    setup_determinism()
    set_seed(a.seed)

    if a.device == "cpu":
        torch.set_num_threads(min(8, os.cpu_count() or 1))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    device = torch.device(a.device)

    # --- Data (HIGH 5) ---
    if a.data_root is not None:
        data_root = a.data_root.resolve()
        for split in ("train", "val", "test"):
            sp = data_root / split
            if not sp.is_dir():
                raise SystemExit(f"--data-root: missing subfolder: {sp}")
        train_ds = datasets.ImageFolder(str(data_root / "train"), transform=build_transforms(True))
        val_ds = datasets.ImageFolder(str(data_root / "val"), transform=build_transforms(False))
        test_ds = datasets.ImageFolder(str(data_root / "test"), transform=build_transforms(False))
        # Validate class consistency across splits
        train_cls = set(train_ds.class_to_idx)
        for sname, sds in (("val", val_ds), ("test", test_ds)):
            extra = set(sds.class_to_idx) - train_cls
            if extra:
                raise SystemExit(
                    f"--data-root {sname}/ contains classes not in train/: {extra}"
                )
        class_names: list[str] = list(train_ds.classes)
        n_classes = len(class_names)
        print(f"[data] custom --data-root: {n_classes} classes from {data_root}")
        print(f"[data] class_to_idx: {train_ds.class_to_idx}")
    else:
        print(f"[data] downloading Flowers102 to {DATA_DIR} (~330MB, only first time)")
        train_full = datasets.Flowers102(
            str(DATA_DIR), split="train", download=True, transform=build_transforms(True)
        )
        val_full = datasets.Flowers102(
            str(DATA_DIR), split="val", download=True, transform=build_transforms(False)
        )
        test_full = datasets.Flowers102(
            str(DATA_DIR), split="test", download=True, transform=build_transforms(False)
        )
        class_ids = list(range(a.n_classes))
        train_sub, id_map = filter_by_classes(train_full, class_ids)
        val_sub, _ = filter_by_classes(val_full, class_ids)
        test_sub, _ = filter_by_classes(test_full, class_ids)
        train_ds = RemappedDataset(train_sub, id_map)  # type: ignore[assignment]
        val_ds = RemappedDataset(val_sub, id_map)      # type: ignore[assignment]
        test_ds = RemappedDataset(test_sub, id_map)    # type: ignore[assignment]
        class_names = [f"flower_{i}" for i in class_ids]
        n_classes = a.n_classes

    print(f"[data] train={len(train_ds)} val={len(val_ds)} test={len(test_ds)}")

    # Log class counts pre-training (HIGH 7)
    train_labels = get_all_labels(train_ds)
    class_counts = dict(sorted(Counter(train_labels).items()))
    print(f"[data] class counts (train): {class_counts}")

    # --- Imbalance strategy (HIGH 7; do not combine) ---
    class_weight_tensor: torch.Tensor | None = None
    sampler: WeightedRandomSampler | None = None
    if a.balance == "weighted-loss":
        class_weight_tensor = compute_class_weights(train_labels, n_classes).to(device)
        print(f"[balance] weighted-loss weights: {class_weight_tensor.tolist()}")
    elif a.balance == "weighted-sampler":
        cw = compute_class_weights(train_labels, n_classes)
        sample_w = torch.tensor([cw[y] for y in train_labels])
        sampler = WeightedRandomSampler(sample_w, len(train_labels), replacement=True)
        print("[balance] weighted-sampler enabled")

    tr_loader = DataLoader(
        train_ds,
        batch_size=a.batch_size,
        shuffle=(sampler is None),
        sampler=sampler,
        num_workers=0,
    )
    val_loader = DataLoader(val_ds, batch_size=a.batch_size, shuffle=False, num_workers=0)

    # --- Model (HIGH 8: fine-tune flag) ---
    weights_enum = models.ResNet18_Weights.IMAGENET1K_V1
    model = models.resnet18(weights=weights_enum)
    for p in model.parameters():
        p.requires_grad = False

    if a.fine_tune:
        for p in model.layer4.parameters():
            p.requires_grad = True
        if not a.bn_train:
            # Keep layer4 BN frozen unless --bn-train
            for m in model.layer4.modules():
                if isinstance(m, nn.BatchNorm2d):
                    for p in m.parameters():
                        p.requires_grad = False

    model.fc = nn.Linear(model.fc.in_features, n_classes)
    model = model.to(device)

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"[model] ResNet18 (backbone frozen) | trainable={trainable:,} / total={total:,}")

    # --- Optimizer with param groups for fine-tune (HIGH 8) ---
    if a.fine_tune:
        param_groups = [
            {"params": model.layer4.parameters(), "lr": a.lr * 0.1},
            {"params": model.fc.parameters(), "lr": a.lr},
        ]
        opt = torch.optim.Adam(param_groups)
    else:
        opt = torch.optim.Adam(model.fc.parameters(), lr=a.lr)

    ce = nn.CrossEntropyLoss(weight=class_weight_tensor)

    # --- Scheduler (HIGH 8) ---
    scheduler: torch.optim.lr_scheduler.LRScheduler | None = None
    if a.scheduler == "cosine":
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=a.epochs)
    elif a.scheduler == "step":
        scheduler = torch.optim.lr_scheduler.StepLR(
            opt, step_size=max(1, a.epochs // 3), gamma=0.1
        )

    history: dict[str, list[float]] = {
        "train_loss": [], "val_loss": [], "val_acc": [], "val_macro_f1": [],
    }
    best_metric_val = -1.0
    best_epoch = 1
    patience_counter = 0
    ckpt_path = OUT_DIR / "best_model.pt"

    # Record transform pipeline strings for reproducibility (MED 10)
    transform_train_str = repr(build_transforms(True))
    transform_val_str = repr(build_transforms(False))

    for epoch in range(1, a.epochs + 1):
        # --- Train ---
        model.train()
        # Keep BN layers frozen (in backbone and unfrozen layer4 unless --bn-train)
        for m in model.modules():
            if isinstance(m, nn.BatchNorm2d):
                in_layer4 = any(m is lm for lm in model.layer4.modules())
                if not in_layer4 or not a.bn_train:
                    m.eval()

        tr_loss = 0.0
        n = 0
        for x, y in tr_loader:
            assert_finite(x, "input batch")  # HIGH 4
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            logits = model(x)
            assert_finite(logits, "logits")  # HIGH 4
            loss = ce(logits, y)
            if not math.isfinite(loss.item()):
                raise RuntimeError(f"Non-finite loss at epoch {epoch}: {loss.item()}")
            loss.backward()
            nn.utils.clip_grad_norm_(
                model.parameters(), max_norm=5.0, error_if_nonfinite=True  # HIGH 4
            )
            opt.step()
            tr_loss += loss.item() * x.size(0)
            n += x.size(0)
        tr_loss /= n

        # --- Val ---
        model.eval()
        val_loss = 0.0
        n = 0
        all_y: list[int] = []
        all_pred: list[int] = []
        with torch.no_grad():
            for x, y in val_loader:
                x, y = x.to(device), y.to(device)
                logits = model(x)
                assert_finite(logits, "val logits")  # HIGH 4
                val_loss += ce(logits, y).item() * x.size(0)
                preds = logits.argmax(dim=1)
                all_y.extend(y.cpu().tolist())
                all_pred.extend(preds.cpu().tolist())
                n += x.size(0)
        val_loss /= n
        val_acc = float(np.mean(np.array(all_y) == np.array(all_pred)))
        val_macro_f1 = float(f1_score(all_y, all_pred, average="macro", zero_division=0))

        history["train_loss"].append(tr_loss)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)
        history["val_macro_f1"].append(val_macro_f1)

        if scheduler is not None:
            scheduler.step()

        current_metric = val_acc if a.best_metric == "val_acc" else val_macro_f1
        marker = ""
        if current_metric > best_metric_val:
            best_metric_val = current_metric
            best_epoch = epoch
            patience_counter = 0
            # NaN guard before saving checkpoint (HIGH 4)
            state = model.state_dict()
            for k, v in state.items():
                if not torch.isfinite(v).all():
                    raise RuntimeError(f"Non-finite value in checkpoint tensor '{k}'")
            torch.save(
                {
                    "model_state_dict": state,
                    "n_classes": n_classes,
                    "class_names": class_names,  # HIGH 5: store names in ckpt
                    "val_acc": val_acc,
                    "val_macro_f1": val_macro_f1,
                    "fine_tune": a.fine_tune,
                },
                ckpt_path,
            )
            marker = "  *best*"
        else:
            patience_counter += 1

        print(
            f"[epoch {epoch:2d}/{a.epochs}] train_loss={tr_loss:.4f}  "
            f"val_loss={val_loss:.4f}  val_acc={val_acc:.3f}  "
            f"val_macro_f1={val_macro_f1:.3f}{marker}"
        )

        if a.patience is not None and patience_counter >= a.patience:
            print(f"[early stop] no improvement for {a.patience} epochs; stopped at epoch {epoch}")
            break

    # --- Plot ---
    fig, ax1 = plt.subplots(figsize=(7, 4))
    ax1.plot(history["train_loss"], label="train_loss")
    ax1.plot(history["val_loss"], label="val_loss")
    ax1.set_xlabel("epoch")
    ax1.set_ylabel("loss")
    ax1.legend(loc="upper left")
    ax2 = ax1.twinx()
    ax2.plot(history["val_acc"], color="green", linestyle="--", label="val_acc")
    ax2.plot(history["val_macro_f1"], color="orange", linestyle=":", label="val_macro_f1")
    ax2.set_ylabel("metric")
    ax2.legend(loc="upper right")
    plt.title(
        f"Transfer learning ResNet18 → {n_classes} classes  "
        f"(best {a.best_metric} {best_metric_val:.3f})"
    )
    plt.tight_layout()
    plt.savefig(OUT_DIR / "loss_acc.png", dpi=120)
    plt.close()

    # --- Metrics JSON (MED 10: full reproducibility record) ---
    import torchvision

    # Serialize args (Path objects → str)
    args_dict = {
        k: str(v) if isinstance(v, Path) else v for k, v in vars(a).items()
    }
    metrics = {
        "best_val_acc": round(history["val_acc"][best_epoch - 1], 4),
        "best_val_macro_f1": round(history["val_macro_f1"][best_epoch - 1], 4),
        "best_epoch": best_epoch,
        "trainable_params": trainable,
        "total_params": total,
        "python_version": sys.version,
        "torch_version": torch.__version__,
        "torchvision_version": torchvision.__version__,
        "args": args_dict,
        "device": str(device),
        "weights_enum": "ResNet18_Weights.IMAGENET1K_V1",
        "transform_train": transform_train_str,
        "transform_val": transform_val_str,
        "git_sha": git_sha(),
        "class_names": class_names,
        "class_counts_train": class_counts,
        "history": history,
    }
    with (OUT_DIR / "train_metrics.json").open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, allow_nan=False)  # HIGH 4: no NaN in JSON
    print(f"[train] saved → {ckpt_path}, loss_acc.png, train_metrics.json")


if __name__ == "__main__":
    main()
