"""1D-CNN ハイパースペクトル分類 — 学習スクリプト

モード:
  synthetic     合成 6-class データ (デフォルト; オフライン可)
  indianpines   実 Indian Pines .mat (要インターネット初回 or --data-root 指定)
  custom        ユーザー CSV/NPY (--data-root に X.npy + y.npy + class_names.txt)

モデル: Conv1d(1→16,k7)→BN→ReLU→MaxPool→Conv1d(16→32,k5)→BN→ReLU→MaxPool
        →Conv1d(32→64,k3)→BN→ReLU→GAP→Linear(64→n_classes)
        実パラメータ数は n_classes 依存 (synthetic 6 class → 9,606)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import platform
import subprocess
import sys
import warnings
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import (
    balanced_accuracy_score,
    classification_report,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from torch.utils.data import DataLoader, TensorDataset, WeightedRandomSampler

_SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(_SRC))
from _argtypes import bounded_float, bounded_int, positive_int
from dataset import CLASS_NAMES as _SYNTH_CLASS_NAMES
from dataset import generate

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class HSICNN(nn.Module):
    """1D-CNN for per-pixel hyperspectral classification."""

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
        return self.head(self.features(x).squeeze(-1))


# ---------------------------------------------------------------------------
# NaN / Inf guard (HIGH 4)
# ---------------------------------------------------------------------------

_nan_batch_counter = 0


def assert_finite(t: torch.Tensor, name: str) -> bool:
    """Return True if all finite; log warning otherwise."""
    if not torch.isfinite(t).all():
        n = int((~torch.isfinite(t)).sum().item())
        log.warning("Non-finite values (%d) in %s — skipping batch", n, name)
        return False
    return True


# ---------------------------------------------------------------------------
# Normalisation (HIGH 5)
# ---------------------------------------------------------------------------

def compute_stats(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = X.mean(axis=0, keepdims=True).astype(np.float32)
    std = (X.std(axis=0, keepdims=True) + 1e-8).astype(np.float32)
    return mean, std


def apply_norm(X: np.ndarray, method: str,
               mean: Optional[np.ndarray] = None,
               std: Optional[np.ndarray] = None) -> np.ndarray:
    if method == "per_band_zscore":
        return (X - mean) / std
    elif method == "per_spectrum_snv":
        mu = X.mean(axis=1, keepdims=True)
        sigma = X.std(axis=1, keepdims=True) + 1e-8
        return (X - mu) / sigma
    elif method == "none":
        return X.copy()
    raise ValueError(f"Unknown --norm-method: {method!r}")


# ---------------------------------------------------------------------------
# Focal loss (HIGH 3)
# ---------------------------------------------------------------------------

class FocalLoss(nn.Module):
    def __init__(self, gamma: float = 2.0, weight: Optional[torch.Tensor] = None):
        super().__init__()
        self.gamma = gamma
        self.ce = nn.CrossEntropyLoss(weight=weight, reduction="none")

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        ce_loss = self.ce(logits, targets)
        pt = torch.exp(-ce_loss)
        return ((1 - pt) ** self.gamma * ce_loss).mean()


# ---------------------------------------------------------------------------
# Spatial split (BLOCKING 2)
# ---------------------------------------------------------------------------

def disjoint_patch_split(
    coords: np.ndarray, labels: np.ndarray,
    patch_size: int = 8, exclusion_radius: int = 5,
    test_size: float = 0.2, val_size: float = 0.25, seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Split pixels by spatial patch — prevents spatial autocorrelation leakage."""
    rows, cols = coords[:, 0], coords[:, 1]
    max_col_patches = int(cols.max()) // patch_size + 1
    patch_id = (rows // patch_size) * (max_col_patches + 1) + (cols // patch_size)
    unique_patches = np.unique(patch_id)

    patch_dominant = np.array([
        int(np.bincount(labels[patch_id == p]).argmax()) for p in unique_patches
    ])

    gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    tv_i, te_i = next(gss.split(unique_patches, patch_dominant, groups=unique_patches))
    tv_patches, tv_dom = unique_patches[tv_i], patch_dominant[tv_i]
    te_patches = unique_patches[te_i]

    gss2 = GroupShuffleSplit(n_splits=1, test_size=val_size, random_state=seed + 1)
    tr_i, va_i = next(gss2.split(tv_patches, tv_dom, groups=tv_patches))
    tr_patches = tv_patches[tr_i]
    va_patches = tv_patches[va_i]

    def pixels_of(patches):
        return np.where(np.isin(patch_id, patches))[0]

    train_idx = pixels_of(tr_patches)
    val_idx = pixels_of(va_patches)
    test_idx = pixels_of(te_patches)

    if exclusion_radius > 0:
        try:
            from scipy.spatial import cKDTree
            def exclude_border(keep_idx, *other_sets):
                others = np.concatenate([s for s in other_sets if len(s) > 0])
                if len(others) == 0:
                    return keep_idx
                tree = cKDTree(coords[others].astype(float))
                dists, _ = tree.query(coords[keep_idx].astype(float), k=1)
                return keep_idx[dists > exclusion_radius]
            train_idx = exclude_border(train_idx, val_idx, test_idx)
            val_idx   = exclude_border(val_idx,   train_idx, test_idx)
            test_idx  = exclude_border(test_idx,  train_idx, val_idx)
        except ImportError:
            log.warning("scipy not available; skipping exclusion-radius border removal")

    return train_idx, val_idx, test_idx


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def load_synthetic(args) -> tuple[np.ndarray, np.ndarray, list[str], None]:
    log.info("synthetic: %d samples/class × %d classes × 200 bands",
             args.n_per_class, len(_SYNTH_CLASS_NAMES))
    X, y, class_names = generate(n_per_class=args.n_per_class, seed=args.seed)
    if not np.all(np.isfinite(X)):
        raise ValueError("Synthetic generator produced non-finite values")
    return X, y, class_names, None


def load_real_indianpines(args) -> tuple[np.ndarray, np.ndarray, list[str], np.ndarray]:
    from load_indianpines import load_indianpines
    data_dir = Path(args.data_root) if args.data_root else (
        Path(__file__).resolve().parent.parent / "data"
    )
    log.info("indianpines: loading from %s", data_dir)
    return load_indianpines(data_dir, auto_download=True)


def load_custom(args) -> tuple[np.ndarray, np.ndarray, list[str], Optional[np.ndarray]]:
    if not args.data_root:
        raise ValueError("--data-root required for --mode custom")
    root = Path(args.data_root)
    X = np.load(root / "X.npy").astype(np.float32)
    y = np.load(root / "y.npy").astype(np.int64)
    names_path = root / "class_names.txt"
    class_names = (
        [l.strip() for l in names_path.read_text().splitlines() if l.strip()]
        if names_path.exists()
        else [f"class_{i}" for i in range(int(y.max()) + 1)]
    )
    coords_path = root / "coords.npy"
    coords = np.load(str(coords_path)).astype(np.int32) if coords_path.exists() else None
    log.info("custom: X=%s y=%s classes=%s coords=%s",
             X.shape, y.shape, class_names, coords.shape if coords is not None else None)
    return X, y, class_names, coords


# ---------------------------------------------------------------------------
# Split dispatcher
# ---------------------------------------------------------------------------

def make_splits(X, y, coords, mode, strategy, args):
    if strategy == "random_pixel":
        if mode != "synthetic" and not args.allow_random_pixel_split:
            log.warning(
                "⚠  --split-strategy random_pixel on real hyperspectral data introduces "
                "spatial autocorrelation leakage → optimistically inflated metrics. "
                "Use --split-strategy disjoint_patch, or pass --allow-random-pixel-split."
            )
        X_tv, X_te, y_tv, y_te = train_test_split(
            X, y, test_size=0.2, stratify=y, random_state=args.seed)
        X_tr, X_va, y_tr, y_va = train_test_split(
            X_tv, y_tv, test_size=0.25, stratify=y_tv, random_state=args.seed)
        return X_tr, X_va, X_te, y_tr, y_va, y_te

    if strategy in ("disjoint_patch", "disjoint_class_stratified"):
        if coords is None:
            log.warning("disjoint_patch requires coords; falling back to random_pixel")
            return make_splits(X, y, coords, mode, "random_pixel", args)
        tr_i, va_i, te_i = disjoint_patch_split(
            coords, y,
            patch_size=args.patch_grid,
            exclusion_radius=args.exclusion_radius,
            test_size=0.2, val_size=0.25, seed=args.seed,
        )
        return X[tr_i], X[va_i], X[te_i], y[tr_i], y[va_i], y[te_i]

    raise ValueError(f"Unknown split strategy: {strategy!r}")


# ---------------------------------------------------------------------------
# Class-balance helpers (HIGH 3)
# ---------------------------------------------------------------------------

def class_weights(y: np.ndarray, n_classes: int) -> torch.Tensor:
    """w_c = N / (C × count_c)  (inverse-frequency weighting)."""
    counts = np.maximum(np.bincount(y, minlength=n_classes).astype(np.float32), 1)
    return torch.tensor(len(y) / (n_classes * counts), dtype=torch.float32)


def make_weighted_sampler(y_train: np.ndarray, n_classes: int) -> WeightedRandomSampler:
    w = class_weights(y_train, n_classes)
    sw = w[y_train]
    return WeightedRandomSampler(sw.tolist(), num_samples=len(y_train), replacement=True)


# ---------------------------------------------------------------------------
# Device selection (MED 10)
# ---------------------------------------------------------------------------

def resolve_device(requested: str) -> torch.device:
    if requested == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda")
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")
    dev = torch.device(requested)
    if dev.type == "cuda" and not torch.cuda.is_available():
        log.warning("CUDA unavailable; falling back to CPU")
        return torch.device("cpu")
    if dev.type == "mps" and not (
        hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
    ):
        log.warning("MPS unavailable; falling back to CPU")
        return torch.device("cpu")
    return dev


# ---------------------------------------------------------------------------
# Reproducibility (HIGH 6)
# ---------------------------------------------------------------------------

def set_repro(seed: int, deterministic: bool) -> None:
    torch.manual_seed(seed)
    np.random.seed(seed)
    if deterministic:
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        try:
            torch.use_deterministic_algorithms(True)
        except RuntimeError as exc:
            log.warning("use_deterministic_algorithms: %s", exc)


# ---------------------------------------------------------------------------
# Plots (HIGH 7)
# ---------------------------------------------------------------------------

def save_cm(cm: np.ndarray, class_names: list[str], out_dir: Path, title: str = "") -> None:
    import csv
    n = len(class_names)
    fig, ax = plt.subplots(figsize=(max(6, n), max(5, n - 1)))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(n)); ax.set_yticks(range(n))
    ax.set_xticklabels(class_names, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(class_names, fontsize=8)
    ax.set_xlabel("Predicted"); ax.set_ylabel("True")
    if title:
        ax.set_title(title, fontsize=9)
    for i in range(n):
        for j in range(n):
            ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=7,
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    fig.colorbar(im); fig.tight_layout()
    fig.savefig(out_dir / "confusion_matrix.png", dpi=120); plt.close(fig)

    with open(out_dir / "confusion_matrix.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["true\\pred"] + class_names)
        for i, row in enumerate(cm):
            w.writerow([class_names[i]] + row.tolist())


def save_prediction_map(y_pred, coords, H, W, class_names, out_dir, y_true=None):
    from matplotlib.patches import Patch
    cmap = plt.get_cmap("tab20", max(len(class_names), 1))
    pred_map = np.full((H, W), -1, dtype=np.int32)
    pred_map[coords[:, 0], coords[:, 1]] = y_pred

    ncols = 2 if y_true is not None else 1
    fig, axes = plt.subplots(1, ncols, figsize=(5 * ncols + 2, 5))
    if ncols == 1:
        axes = [axes]
    axes[0].imshow(pred_map, cmap=cmap, vmin=0, vmax=len(class_names) - 1)
    axes[0].set_title("Prediction Map"); axes[0].axis("off")
    if y_true is not None:
        gt_map = np.full((H, W), -1, dtype=np.int32)
        gt_map[coords[:, 0], coords[:, 1]] = y_true
        axes[1].imshow(gt_map, cmap=cmap, vmin=0, vmax=len(class_names) - 1)
        axes[1].set_title("Ground Truth"); axes[1].axis("off")

    legend = [Patch(color=cmap(i), label=f"{i}: {n}") for i, n in enumerate(class_names)]
    fig.legend(handles=legend, loc="lower center", ncol=4, fontsize=7,
               bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout()
    fig.savefig(out_dir / "prediction_map.png", dpi=120, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sha256_prefix(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()[:16]


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


def compute_metrics(y_true, y_pred, class_names):
    report = classification_report(
        y_true, y_pred, target_names=class_names,
        output_dict=True, zero_division=0,
    )
    pf1 = {c: report[c]["f1-score"] for c in class_names}
    return {
        "overall_accuracy": float(np.mean(np.array(y_true) == np.array(y_pred))),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "cohen_kappa": float(cohen_kappa_score(y_true, y_pred)),
        "per_class_f1": pf1,
        "per_class_f1_sorted": dict(sorted(pf1.items(), key=lambda kv: kv[1])),
    }


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Train 1D-CNN on hyperspectral data",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--mode",
                    choices=["synthetic", "indianpines", "custom"], default="synthetic")
    ap.add_argument("--data-root", default=None,
                    help="Data directory (indianpines: .mat location; custom: X/y.npy)")
    ap.add_argument("--n-per-class", type=bounded_int(5, 100_000), default=200,
                    help="Samples per class (synthetic only)")
    ap.add_argument("--split-strategy",
                    choices=["random_pixel", "disjoint_patch", "disjoint_class_stratified"],
                    default="disjoint_patch")
    ap.add_argument("--patch-grid", type=bounded_int(2, 256), default=8,
                    help="Patch size for disjoint_patch split")
    ap.add_argument("--exclusion-radius", type=bounded_int(0, 100), default=5,
                    help="Pixel buffer at patch boundaries (0=disabled)")
    ap.add_argument("--allow-random-pixel-split", action="store_true")
    ap.add_argument("--norm-method",
                    choices=["per_band_zscore", "per_spectrum_snv", "none"],
                    default="per_band_zscore")
    ap.add_argument("--balance",
                    choices=["none", "weighted_ce", "weighted_sampler", "focal"],
                    default="weighted_ce")
    ap.add_argument("--epochs",     type=bounded_int(1, 1000), default=20)
    ap.add_argument("--batch-size", type=bounded_int(1, 65536), default=32)
    ap.add_argument("--lr",         type=bounded_float(0, 1, inclusive_lo=False), default=1e-3)
    ap.add_argument("--device",     choices=["cpu", "cuda", "mps", "auto"], default="auto")
    ap.add_argument("--amp",        action="store_true",
                    help="AMP (CUDA only; auto-disabled on CPU/MPS)")
    ap.add_argument("--deterministic", action="store_true")
    ap.add_argument("--seed",       type=bounded_int(0, 2**31 - 1), default=42)
    ap.add_argument("--best-metric",
                    choices=["macro_f1", "val_acc", "balanced_acc"],
                    default="macro_f1")
    return ap


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    args = build_parser().parse_args()
    set_repro(args.seed, args.deterministic)

    outputs = Path(__file__).resolve().parent.parent / "outputs"
    outputs.mkdir(exist_ok=True)

    # --- Load data ---
    loaders = {
        "synthetic":   load_synthetic,
        "indianpines": load_real_indianpines,
        "custom":      load_custom,
    }
    X, y, class_names, coords = loaders[args.mode](args)
    n_classes = len(class_names)
    n_bands   = X.shape[1]
    log.info("X=%s  y=%s  classes=%d  bands=%d", X.shape, y.shape, n_classes, n_bands)

    if not np.all(np.isfinite(X)):
        n_bad = int(np.sum(~np.isfinite(X)))
        raise ValueError(f"{n_bad} non-finite values in input spectra")

    # --- Split ---
    effective_strategy = args.split_strategy
    if args.mode == "synthetic" and effective_strategy != "random_pixel":
        log.info("Synthetic mode: switching to random_pixel split (no spatial coords)")
        effective_strategy = "random_pixel"

    X_train, X_val, X_test, y_train, y_val, y_test = make_splits(
        X, y, coords, args.mode, effective_strategy, args
    )

    # --- Normalise (fit on train only) ---
    norm_mean = norm_std = None
    if args.norm_method == "per_band_zscore":
        norm_mean, norm_std = compute_stats(X_train)
    X_train = apply_norm(X_train, args.norm_method, norm_mean, norm_std)
    X_val   = apply_norm(X_val,   args.norm_method, norm_mean, norm_std)
    X_test  = apply_norm(X_test,  args.norm_method, norm_mean, norm_std)
    for split_name, Xs in [("train", X_train), ("val", X_val), ("test", X_test)]:
        if not np.all(np.isfinite(Xs)):
            raise ValueError(f"Non-finite values in {split_name} after normalization")
    log.info("norm=%s  train=%d  val=%d  test=%d",
             args.norm_method, len(y_train), len(y_val), len(y_test))

    # --- Device & AMP ---
    device = resolve_device(args.device)
    log.info("device=%s", device)
    if device.type == "mps":
        log.warning("MPS backend: reduced precision may affect metrics")
    use_amp = args.amp and device.type == "cuda"
    if args.amp and not use_amp:
        log.warning("--amp ignored on %s", device.type)
    scaler = torch.cuda.amp.GradScaler(enabled=use_amp) if use_amp else None

    # --- DataLoaders ---
    def mk_ds(Xa, ya):
        return TensorDataset(
            torch.from_numpy(Xa).unsqueeze(1).float(),
            torch.from_numpy(ya).long(),
        )

    sampler = None
    shuffle_train = True
    if args.balance == "weighted_sampler":
        sampler = make_weighted_sampler(y_train, n_classes)
        shuffle_train = False

    train_loader = DataLoader(mk_ds(X_train, y_train),
                              batch_size=args.batch_size,
                              shuffle=shuffle_train, sampler=sampler)
    val_loader   = DataLoader(mk_ds(X_val,   y_val),
                              batch_size=args.batch_size, shuffle=False)
    test_loader  = DataLoader(mk_ds(X_test,  y_test),
                              batch_size=args.batch_size, shuffle=False)

    # --- Model ---
    model = HSICNN(n_bands=n_bands, n_classes=n_classes).to(device)
    if device.type == "mps":
        model = model.float()
    n_param = sum(p.numel() for p in model.parameters())
    log.info("HSI-CNN  bands=%d  classes=%d  params=%s", n_bands, n_classes, f"{n_param:,}")

    # --- Loss ---
    cw_tensor = None
    if args.balance in ("weighted_ce", "focal"):
        cw_tensor = class_weights(y_train, n_classes).to(device)
        log.info("class weights: %s",
                 {c: round(float(w), 3) for c, w in zip(class_names, cw_tensor.cpu())})
    criterion = (FocalLoss(gamma=2.0, weight=cw_tensor)
                 if args.balance == "focal"
                 else nn.CrossEntropyLoss(weight=cw_tensor))
    val_ce = nn.CrossEntropyLoss()  # unweighted for val loss display

    opt = torch.optim.Adam(model.parameters(), lr=args.lr)

    # --- Training loop ---
    hist = {"train_loss": [], "val_loss": [], "val_acc": [], "val_macro_f1": []}
    best_score = -float("inf")
    best_epoch = 0
    global _nan_batch_counter

    for ep in range(1, args.epochs + 1):
        model.train()
        tl = 0.0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            if not assert_finite(xb, "input"):
                _nan_batch_counter += 1; continue
            opt.zero_grad()
            if use_amp:
                with torch.cuda.amp.autocast():
                    logits = model(xb)
                    loss   = criterion(logits, yb)
                if not assert_finite(loss, "loss"):
                    _nan_batch_counter += 1; continue
                scaler.scale(loss).backward()
                scaler.unscale_(opt)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(opt); scaler.update()
            else:
                logits = model(xb)
                if not assert_finite(logits, "logits"):
                    _nan_batch_counter += 1; continue
                loss = criterion(logits, yb)
                if not assert_finite(loss, "loss"):
                    _nan_batch_counter += 1; continue
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                opt.step()
            tl += loss.item() * yb.size(0)
        tl /= max(len(train_loader.dataset), 1)

        model.eval()
        vl, vp_all, vt_all = 0.0, [], []
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                out = model(xb)
                vl += val_ce(out, yb).item() * yb.size(0)
                vp_all.extend(out.argmax(1).cpu().tolist())
                vt_all.extend(yb.cpu().tolist())
        vl /= max(len(val_loader.dataset), 1)
        va   = float(np.mean(np.array(vt_all) == np.array(vp_all)))
        vmf1 = float(f1_score(vt_all, vp_all, average="macro", zero_division=0))
        vbal = float(balanced_accuracy_score(vt_all, vp_all))

        hist["train_loss"].append(tl)
        hist["val_loss"].append(vl)
        hist["val_acc"].append(va)
        hist["val_macro_f1"].append(vmf1)

        score = {"macro_f1": vmf1, "val_acc": va, "balanced_acc": vbal}[args.best_metric]
        star = ""
        if score > best_score:
            best_score = score; best_epoch = ep
            ckpt = {
                "model_state": model.state_dict(),
                "class_names": class_names,
                "n_bands": n_bands, "n_classes": n_classes,
                "stats": {
                    "mean":   norm_mean.tolist() if norm_mean is not None else None,
                    "std":    norm_std.tolist()  if norm_std  is not None else None,
                    "method": args.norm_method,
                },
                "args": vars(args), "epoch": ep,
            }
            torch.save(ckpt, outputs / "best_model.pt")
            star = " *best*"

        log.info("[ep %2d/%d] loss=%.4f|%.4f  acc=%.3f  mF1=%.3f%s",
                 ep, args.epochs, tl, vl, va, vmf1, star)

    if _nan_batch_counter > 0:
        log.warning("Skipped %d NaN/Inf batches total", _nan_batch_counter)

    # --- Test ---
    ckpt = torch.load(outputs / "best_model.pt", map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    yp_all, yt_all = [], []
    with torch.no_grad():
        for xb, yb in test_loader:
            out = model(xb.to(device))
            yp_all.extend(out.argmax(1).cpu().tolist())
            yt_all.extend(yb.tolist())

    metrics = compute_metrics(yt_all, yp_all, class_names)
    cm = confusion_matrix(yt_all, yp_all, labels=list(range(n_classes)))
    log.info("[test] acc=%.3f  mF1=%.3f  bal_acc=%.3f  kappa=%.3f  best_ep=%d",
             metrics["overall_accuracy"], metrics["macro_f1"],
             metrics["balanced_accuracy"], metrics["cohen_kappa"], best_epoch)
    log.info("Per-class F1 (low→high):")
    for cls, f1v in metrics["per_class_f1_sorted"].items():
        log.info("  %-35s %.3f", cls, f1v)

    # --- Plots ---
    fig, ax1 = plt.subplots(figsize=(7, 4))
    ax1.plot(hist["train_loss"], label="train_loss")
    ax1.plot(hist["val_loss"],   label="val_loss")
    ax1.set_xlabel("epoch"); ax1.set_ylabel("loss"); ax1.legend(loc="upper left")
    ax2 = ax1.twinx()
    ax2.plot(hist["val_acc"],      "g--", label="val_acc")
    ax2.plot(hist["val_macro_f1"], "m:",  label="val_mF1")
    ax2.set_ylabel("metric"); ax2.legend(loc="lower right")
    fig.tight_layout(); fig.savefig(outputs / "loss_acc.png", dpi=120); plt.close(fig)

    save_cm(cm, class_names, outputs,
            title=f"Test acc={metrics['overall_accuracy']:.3f}  mF1={metrics['macro_f1']:.3f}")

    fig, ax = plt.subplots(figsize=(9, 4))
    for c in range(min(n_classes, 16)):
        idxs = np.where(y == c)[0]
        if len(idxs) > 0:
            ax.plot(X[idxs[0]], label=class_names[c], alpha=0.85)
    ax.set_xlabel("Band index"); ax.set_ylabel("Reflectance (raw)"); ax.legend(fontsize=7, ncol=2)
    fig.tight_layout(); fig.savefig(outputs / "sample_spectra.png", dpi=120); plt.close(fig)

    # Prediction map for real data
    if coords is not None and args.mode != "synthetic":
        H = int(coords[:, 0].max()) + 1
        W = int(coords[:, 1].max()) + 1
        X_all_norm = apply_norm(X, args.norm_method, norm_mean, norm_std)
        all_loader = DataLoader(
            TensorDataset(torch.from_numpy(X_all_norm).unsqueeze(1).float(),
                          torch.from_numpy(y).long()),
            batch_size=args.batch_size, shuffle=False,
        )
        yp_full = []
        with torch.no_grad():
            for xb, _ in all_loader:
                yp_full.extend(model(xb.to(device)).argmax(1).cpu().tolist())
        save_prediction_map(np.array(yp_full), coords, H, W,
                            class_names, outputs, y_true=y)

    # --- metrics.json ---
    full_metrics = {
        "mode": args.mode,
        "split_strategy": effective_strategy,
        "norm_method": args.norm_method,
        "balance": args.balance,
        "dataset_sha256_prefix": sha256_prefix(X),
        "n_samples": int(len(y)),
        "n_bands": int(n_bands),
        "n_classes": int(n_classes),
        "class_names": class_names,
        "n_params": int(n_param),
        "hyperparams": {
            "epochs": args.epochs, "batch_size": args.batch_size,
            "lr": args.lr, "seed": args.seed,
        },
        "best_epoch": best_epoch,
        "best_val_metric": float(best_score),
        "best_metric_name": args.best_metric,
        "test_metrics": metrics,
        "training_history": hist,
        "nan_batches_skipped": _nan_batch_counter,
        "git_commit": git_sha(),
        "python_version": platform.python_version(),
        "torch_version": torch.__version__,
        "note": (
            "⚠ Synthetic data — accuracy is NOT a benchmark of real-world performance"
            if args.mode == "synthetic" else None
        ),
    }
    (outputs / "metrics.json").write_text(
        json.dumps(full_metrics, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )
    log.info("outputs/ written — confusion_matrix.csv, metrics.json, loss_acc.png, …")


if __name__ == "__main__":
    main()
