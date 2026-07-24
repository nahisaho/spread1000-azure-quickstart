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
import platform
import random
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.utils.class_weight import compute_class_weight
from torch.utils.data import DataLoader, TensorDataset

from _argtypes import (
    bounded_probability,
    nonnegative_float,
    positive_float,
    positive_int,
)
from model import BiosignalCNN, num_parameters

ROOT = Path(__file__).resolve().parents[1]
NPZ_PATH = ROOT / "data" / "har_windows.npz"
OUT_DIR = ROOT / "outputs"
N_CHANNELS = 9
N_CLASSES = 6
WINDOW_LENGTH = 128


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _jsonify(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _jsonify(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonify(v) for v in value]
    return value


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _pip_freeze() -> list[str]:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            check=True,
            capture_output=True,
            text=True,
        )
        return [line for line in result.stdout.splitlines() if line.strip()]
    except (OSError, subprocess.SubprocessError):
        return ["unavailable"]


def _find_lockfile() -> Path | None:
    for candidate in [
        ROOT / "requirements.lock",
        ROOT / "requirements.txt",
        ROOT / "infra" / "environments" / "gpu" / "requirements-gpu.lock",
    ]:
        if candidate.exists():
            return candidate
    return None


def set_seed(seed: int) -> torch.Generator:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    return torch.Generator().manual_seed(seed)


def configure_determinism() -> bool:
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    torch.use_deterministic_algorithms(True, warn_only=True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    return True


def compute_norm(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = X.mean(axis=(0, 2), keepdims=True).astype(np.float32)
    std = X.std(axis=(0, 2), keepdims=True).astype(np.float32).clip(min=1e-6)
    if mean.shape != (1, N_CHANNELS, 1) or std.shape != (1, N_CHANNELS, 1):
        raise ValueError(f"unexpected normalization shapes: mean={mean.shape}, std={std.shape}")
    if not np.isfinite(mean).all() or not np.isfinite(std).all():
        raise ValueError("normalization statistics contain non-finite values")
    return mean, std


def apply_norm(X: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    X_norm = ((X - mean) / std).astype(np.float32)
    if not np.isfinite(X_norm).all():
        raise ValueError("normalized features contain non-finite values")
    return X_norm


def validate_dataset_arrays(
    X_all: np.ndarray,
    y_all: np.ndarray,
    subj_all: np.ndarray,
    activities: list[str],
) -> None:
    if X_all.dtype != np.float32:
        raise ValueError(f"expected X_train dtype float32, got {X_all.dtype}")
    if y_all.dtype != np.int64:
        raise ValueError(f"expected y_train dtype int64, got {y_all.dtype}")
    if subj_all.dtype != np.int64:
        raise ValueError(f"expected subj_train dtype int64, got {subj_all.dtype}")
    if X_all.ndim != 3 or X_all.shape[1:] != (N_CHANNELS, WINDOW_LENGTH):
        raise ValueError(f"unexpected X_train shape: {X_all.shape}")
    if y_all.ndim != 1 or subj_all.ndim != 1:
        raise ValueError(f"expected 1D labels/subjects, got y={y_all.shape}, subj={subj_all.shape}")
    if not (X_all.shape[0] == y_all.shape[0] == subj_all.shape[0]):
        raise ValueError(
            f"sample count mismatch: X={X_all.shape[0]}, y={y_all.shape[0]}, subj={subj_all.shape[0]}"
        )
    if not np.isfinite(X_all).all():
        raise ValueError("training data contains non-finite values")
    label_set = set(np.unique(y_all).tolist())
    expected = set(range(N_CLASSES))
    if label_set != expected:
        raise ValueError(f"expected label set {sorted(expected)}, got {sorted(label_set)}")
    if np.any(subj_all <= 0):
        raise ValueError("subject IDs must be positive")
    if len(activities) != N_CLASSES:
        raise ValueError(f"expected {N_CLASSES} activities, got {len(activities)}")


def validate_split(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    train_subj: list[int],
    val_subj: list[int],
) -> None:
    if set(train_subj) & set(val_subj):
        raise RuntimeError("subject leak between train and val")
    for name, X_part, y_part in (("train", X_train, y_train), ("val", X_val, y_val)):
        if X_part.ndim != 3 or X_part.shape[1:] != (N_CHANNELS, WINDOW_LENGTH):
            raise ValueError(f"unexpected {name} feature shape: {X_part.shape}")
        if y_part.ndim != 1:
            raise ValueError(f"unexpected {name} label shape: {y_part.shape}")
        if X_part.shape[0] != y_part.shape[0]:
            raise ValueError(f"sample count mismatch in {name}: X={X_part.shape[0]}, y={y_part.shape[0]}")
        if not np.isfinite(X_part).all():
            raise ValueError(f"{name} features contain non-finite values")
        label_set = set(np.unique(y_part).tolist())
        missing = set(range(N_CLASSES)) - label_set
        if missing:
            raise RuntimeError(f"{name} split is missing classes {sorted(missing)}")


def evaluate(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    criterion: nn.Module,
    epoch: int,
) -> tuple[float, float]:
    model.eval()
    losses: list[float] = []
    preds: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    with torch.no_grad():
        for batch_idx, (xb, yb) in enumerate(loader, start=1):
            xb, yb = xb.to(device), yb.to(device)
            logits = model(xb)
            if not bool(torch.isfinite(logits).all().item()):
                raise RuntimeError(f"non-finite logits during evaluation at epoch={epoch}, batch={batch_idx}")
            loss = criterion(logits, yb)
            losses.append(loss.item() * yb.size(0))
            preds.append(logits.argmax(-1).cpu().numpy())
            targets.append(yb.cpu().numpy())
    n = sum(len(t) for t in targets)
    if n == 0:
        raise RuntimeError("validation loader produced zero samples")
    y_pred = np.concatenate(preds)
    y_true = np.concatenate(targets)
    macro_f1 = float(
        f1_score(
            y_true,
            y_pred,
            labels=np.arange(N_CLASSES),
            average="macro",
            zero_division=0,
        )
    )
    if not np.isfinite(macro_f1):
        raise RuntimeError(f"non-finite macro-F1 during evaluation at epoch={epoch}")
    return sum(losses) / n, macro_f1


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    p.add_argument("--epochs", type=positive_int, default=15)
    p.add_argument("--batch-size", type=positive_int, default=128)
    p.add_argument("--lr", type=positive_float, default=1e-3)
    p.add_argument("--weight-decay", type=nonnegative_float, default=1e-4)
    p.add_argument("--dropout", type=bounded_probability, default=0.30)
    p.add_argument("--patience", type=positive_int, default=4, help="early-stopping patience (epochs)")
    p.add_argument("--seed", type=positive_int, default=42)
    p.add_argument("--class-weights", action="store_true", help="use train-split class weights")
    p.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="成果物ディレクトリ (省略時: <repo>/outputs)",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.device == "cuda" and not torch.cuda.is_available():
        raise SystemExit(
            "CUDA requested but not available. "
            f"torch.cuda.is_available()=False; torch built with CUDA: {torch.version.cuda}; "
            f"detected devices: {torch.cuda.device_count()}"
        )

    if args.device == "cpu":
        torch.set_num_threads(min(8, os.cpu_count() or 1))

    generator = set_seed(args.seed)
    deterministic_mode_enabled = configure_determinism()
    run_uuid = str(uuid.uuid4())
    split_uuid = str(uuid.uuid4())

    if not NPZ_PATH.exists():
        raise FileNotFoundError(
            f"{NPZ_PATH} が見つかりません。先に prepare_data.py を実行してください。"
        )

    data = np.load(NPZ_PATH, allow_pickle=False)
    X_all = data["X_train"]
    y_all = data["y_train"]
    subj_all = data["subj_train"]
    activities = [str(a) for a in data["activities"].tolist()]
    validate_dataset_arrays(X_all, y_all, subj_all, activities)
    dataset_sha256 = _sha256(NPZ_PATH)
    class_mapping = {idx: activity for idx, activity in enumerate(activities)}

    print(f"[data] official train: X={X_all.shape}, subjects={len(set(subj_all.tolist()))}")
    print(f"[data] dataset sha256 = {dataset_sha256}")

    skf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=args.seed)
    train_idx, val_idx = next(skf.split(X_all, y_all, groups=subj_all))
    train_subj = sorted(set(subj_all[train_idx].tolist()))
    val_subj = sorted(set(subj_all[val_idx].tolist()))

    X_train = X_all[train_idx]
    y_train = y_all[train_idx]
    X_val = X_all[val_idx]
    y_val = y_all[val_idx]
    validate_split(X_train, y_train, X_val, y_val, train_subj, val_subj)

    print(f"[split] train subjects ({len(train_subj)}): {train_subj}")
    print(f"[split] val   subjects ({len(val_subj)}): {val_subj}")

    class_counts = np.bincount(y_train, minlength=N_CLASSES)
    print("[data] train class counts:")
    for idx, count in enumerate(class_counts.tolist()):
        print(f"[data]   class {idx} ({activities[idx]}): {count}")

    mean, std = compute_norm(X_train)
    X_train = apply_norm(X_train, mean, std)
    X_val = apply_norm(X_val, mean, std)

    train_ds = TensorDataset(torch.from_numpy(X_train), torch.from_numpy(y_train))
    val_ds = TensorDataset(torch.from_numpy(X_val), torch.from_numpy(y_val))

    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=0,
        generator=generator,
    )
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)

    device = torch.device(args.device)
    model = BiosignalCNN(n_channels=N_CHANNELS, n_classes=N_CLASSES, dropout=args.dropout).to(device)
    trainable_params = num_parameters(model)
    print(f"[model] BiosignalCNN, trainable params = {trainable_params:,}")

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    class_weight_tensor = None
    if args.class_weights:
        class_weights = compute_class_weight(
            class_weight="balanced",
            classes=np.arange(N_CLASSES),
            y=y_train,
        ).astype(np.float32)
        class_weight_tensor = torch.tensor(class_weights, dtype=torch.float32, device=device)
        print(f"[train] class weights enabled: {class_weights.tolist()}")
    criterion = nn.CrossEntropyLoss(weight=class_weight_tensor)

    out_dir = args.output_dir or OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    history: dict[str, list[float]] = {"train_loss": [], "val_loss": [], "val_macro_f1": []}
    best_f1, best_epoch, patience_left = -1.0, 0, args.patience
    best_ckpt = out_dir / "best_model.pt"

    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss, n = 0.0, 0
        for batch_idx, (xb, yb) in enumerate(train_loader, start=1):
            xb, yb = xb.to(device), yb.to(device)
            if not bool(torch.isfinite(xb).all().item()):
                raise RuntimeError(f"non-finite inputs at epoch={epoch}, batch={batch_idx}")
            optimizer.zero_grad()
            logits = model(xb)
            if not bool(torch.isfinite(logits).all().item()):
                raise RuntimeError(f"non-finite logits at epoch={epoch}, batch={batch_idx}")
            loss = criterion(logits, yb)
            if not bool(torch.isfinite(loss).item()):
                raise RuntimeError(f"non-finite loss at epoch={epoch}, batch={batch_idx}")
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * yb.size(0)
            n += yb.size(0)
        if n == 0:
            raise RuntimeError("training loader produced zero samples")

        train_loss = total_loss / n
        val_loss, val_f1 = evaluate(model, val_loader, device, criterion, epoch)
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
                    "n_channels": N_CHANNELS,
                    "n_classes": N_CLASSES,
                    "dropout": args.dropout,
                    "dataset_sha256": dataset_sha256,
                    "normalization_sha256": None,
                    "class_mapping": class_mapping,
                    "split_uuid": split_uuid,
                    "run_uuid": run_uuid,
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

    if not best_ckpt.exists():
        raise RuntimeError("best_model.pt was not created")

    print(f"[train] best val macro-F1 = {best_f1:.4f} (epoch {best_epoch})")

    normalization_path = out_dir / "normalization.npz"
    np.savez(normalization_path, mean=mean, std=std)
    normalization_sha256 = _sha256(normalization_path)

    checkpoint = torch.load(best_ckpt, map_location="cpu", weights_only=True)
    checkpoint["normalization_sha256"] = normalization_sha256
    checkpoint["dataset_sha256"] = dataset_sha256
    checkpoint["class_mapping"] = class_mapping
    checkpoint["split_uuid"] = split_uuid
    checkpoint["run_uuid"] = run_uuid
    torch.save(checkpoint, best_ckpt)
    checkpoint_sha256 = _sha256(best_ckpt)

    fig, ax1 = plt.subplots(figsize=(7, 4))
    epochs_x = range(1, len(history["train_loss"]) + 1)
    ax1.plot(epochs_x, history["train_loss"], label="train loss", color="tab:blue")
    ax1.plot(epochs_x, history["val_loss"], label="val loss", color="tab:orange")
    ax1.set_xlabel("epoch")
    ax1.set_ylabel("loss")
    ax1.legend(loc="upper left")
    ax2 = ax1.twinx()
    ax2.plot(
        epochs_x,
        history["val_macro_f1"],
        label="val macro-F1",
        color="tab:green",
        linestyle="--",
    )
    ax2.set_ylabel("macro-F1")
    ax2.legend(loc="lower right")
    plt.title("UCI HAR CompactCNN — train/val curves")
    plt.tight_layout()
    plt.savefig(out_dir / "loss_curve.png", dpi=120)
    plt.close()

    cli_args = {key: _jsonify(value) for key, value in vars(args).items()}
    train_history = {
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
        "deterministic_mode": deterministic_mode_enabled,
        "split_uuid": split_uuid,
        "run_uuid": run_uuid,
        "dataset_sha256": dataset_sha256,
        "normalization_sha256": normalization_sha256,
        "checkpoint_sha256": checkpoint_sha256,
        "class_weights_enabled": args.class_weights,
        "cli_args": cli_args,
    }
    with (out_dir / "train_history.json").open("w", encoding="utf-8") as handle:
        json.dump(train_history, handle, indent=2, ensure_ascii=False)

    lockfile = _find_lockfile()
    lockfile_sha256 = _sha256(lockfile) if lockfile is not None else None
    manifest = {
        "run_uuid": run_uuid,
        "split_uuid": split_uuid,
        "checkpoint_path": str(best_ckpt),
        "checkpoint_sha256": checkpoint_sha256,
        "normalization_path": str(normalization_path),
        "normalization_sha256": normalization_sha256,
        "dataset_path": str(NPZ_PATH),
        "dataset_sha256": dataset_sha256,
        "lockfile_path": str(lockfile) if lockfile is not None else None,
        "lockfile_sha256": lockfile_sha256,
        "git_commit": _git_commit(),
        "cli_args": cli_args,
        "python_version": platform.python_version(),
        "pip_freeze": _pip_freeze(),
        "torch_version": torch.__version__,
        "torch_cuda_version": torch.version.cuda,
        "cudnn_version": str(torch.backends.cudnn.version()),
        "gpu_model": torch.cuda.get_device_name(0) if args.device == "cuda" and torch.cuda.is_available() else None,
        "deterministic_flags": {
            "deterministic_mode": deterministic_mode_enabled,
            "torch_use_deterministic_algorithms": True,
            "torch_warn_only": True,
            "cudnn_deterministic": torch.backends.cudnn.deterministic,
            "cudnn_benchmark": torch.backends.cudnn.benchmark,
            "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
        },
        "model": {
            "name": "BiosignalCNN",
            "trainable_params": trainable_params,
            "n_channels": N_CHANNELS,
            "n_classes": N_CLASSES,
            "dropout": args.dropout,
        },
    }
    with (out_dir / "reproducibility_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)

    print(
        f"[train] saved → {best_ckpt}, {normalization_path}, "
        f"{out_dir / 'loss_curve.png'}, {out_dir / 'train_history.json'}, "
        f"{out_dir / 'reproducibility_manifest.json'}"
    )


if __name__ == "__main__":
    main()
