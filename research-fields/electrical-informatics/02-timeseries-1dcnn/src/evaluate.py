"""
公式 test (2,947 窓, 未知 9 被験者) で 1 回だけ評価.

train.py で計算した mean/std を必ず再利用 (train に fit した統計を test に適用).
成果物: metrics.json, classification_report.json, confusion_matrix.png
"""
from __future__ import annotations

import argparse
import hmac
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from torch.utils.data import DataLoader, TensorDataset

from _argtypes import positive_int
from model import BiosignalCNN

ROOT = Path(__file__).resolve().parents[1]
NPZ_PATH = ROOT / "data" / "har_windows.npz"
OUT_DIR = ROOT / "outputs"
N_CLASSES = 6


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _warn_if_hash_mismatch(name: str, expected: str | None, actual: str) -> None:
    if not expected:
        print(f"[eval] note: checkpoint does not contain {name} metadata (older checkpoint?)")
        return
    if not hmac.compare_digest(expected, actual):
        print(
            f"[eval] WARNING: {name} mismatch. checkpoint={expected}, current={actual}",
        )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    p.add_argument("--batch-size", type=positive_int, default=256)
    p.add_argument("--output-dir", type=Path, default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.device == "cuda" and not torch.cuda.is_available():
        raise SystemExit(
            "CUDA requested but not available. "
            f"torch.cuda.is_available()=False; torch built with CUDA: {torch.version.cuda}; "
            f"detected devices: {torch.cuda.device_count()}"
        )

    out_dir = args.output_dir or OUT_DIR
    ckpt_path = out_dir / "best_model.pt"
    norm_path = out_dir / "normalization.npz"

    if not ckpt_path.exists() or not norm_path.exists():
        raise FileNotFoundError(
            "best_model.pt または normalization.npz が見つかりません。"
            " 先に train.py を実行してください。"
        )
    if not NPZ_PATH.exists():
        raise FileNotFoundError(f"dataset not found: {NPZ_PATH}")

    device = torch.device(args.device)
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=True)
    activities = list(ckpt["activities"])

    current_dataset_sha256 = _sha256(NPZ_PATH)
    current_normalization_sha256 = _sha256(norm_path)
    _warn_if_hash_mismatch("dataset_sha256", ckpt.get("dataset_sha256"), current_dataset_sha256)
    _warn_if_hash_mismatch(
        "normalization_sha256",
        ckpt.get("normalization_sha256"),
        current_normalization_sha256,
    )
    if ckpt.get("split_uuid"):
        print(f"[eval] split_uuid = {ckpt['split_uuid']}")
    if ckpt.get("run_uuid"):
        print(f"[eval] run_uuid   = {ckpt['run_uuid']}")

    model = BiosignalCNN(
        n_channels=ckpt.get("n_channels", 9),
        n_classes=ckpt.get("n_classes", N_CLASSES),
        dropout=ckpt.get("dropout", 0.30),
    ).to(device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    data = np.load(NPZ_PATH, allow_pickle=False)
    X_test = data["X_test"]
    y_test = data["y_test"]
    subj_test = data["subj_test"]

    norm = np.load(norm_path, allow_pickle=False)
    mean = norm["mean"]
    std = norm["std"]
    X_test = ((X_test - mean) / std).astype(np.float32)
    if not np.isfinite(X_test).all():
        raise RuntimeError("normalized X_test contains non-finite values")
    print(f"[eval] test: X={X_test.shape}, subjects={sorted(set(subj_test.tolist()))}")

    loader = DataLoader(
        TensorDataset(torch.from_numpy(X_test), torch.from_numpy(y_test)),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=0,
    )

    preds: list[np.ndarray] = []
    with torch.no_grad():
        for batch_idx, (xb, _) in enumerate(loader, start=1):
            xb = xb.to(device)
            if not bool(torch.isfinite(xb).all().item()):
                raise RuntimeError(f"non-finite inputs during evaluation at batch={batch_idx}")
            logits = model(xb)
            if not bool(torch.isfinite(logits).all().item()):
                raise RuntimeError(f"non-finite logits during evaluation at batch={batch_idx}")
            preds.append(logits.argmax(-1).cpu().numpy())
    y_pred = np.concatenate(preds)
    y_true = y_test

    accuracy = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(
        f1_score(
            y_true,
            y_pred,
            labels=np.arange(N_CLASSES),
            average="macro",
            zero_division=0,
        )
    )
    report = classification_report(
        y_true,
        y_pred,
        labels=list(range(len(activities))),
        target_names=activities,
        output_dict=True,
        zero_division=0,
    )
    per_class_f1 = {name: float(report[name]["f1-score"]) for name in activities}
    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(activities))))

    metrics = {
        "test_accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "per_class_f1": {k: round(v, 4) for k, v in per_class_f1.items()},
        "checkpoint_epoch": int(ckpt.get("epoch", -1)),
        "checkpoint_val_macro_f1": round(float(ckpt.get("val_macro_f1", -1.0)), 4),
        "split": "official_subject_independent_test",
        "n_test_windows": int(len(y_true)),
        "test_subjects": sorted(set(subj_test.tolist())),
        "dataset_sha256": current_dataset_sha256,
        "normalization_sha256": current_normalization_sha256,
        "split_uuid": ckpt.get("split_uuid"),
        "run_uuid": ckpt.get("run_uuid"),
    }
    with (out_dir / "metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2, ensure_ascii=False)
    with (out_dir / "classification_report.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)

    print("[eval] test accuracy = {:.4f}".format(accuracy))
    print("[eval] test macro-F1 = {:.4f}".format(macro_f1))
    for name, val in per_class_f1.items():
        print(f"[eval]   {name:20s} F1 = {val:.4f}")

    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(activities)))
    ax.set_yticks(range(len(activities)))
    ax.set_xticklabels(activities, rotation=40, ha="right")
    ax.set_yticklabels(activities)
    ax.set_xlabel("predicted")
    ax.set_ylabel("true")
    ax.set_title("UCI HAR test — confusion matrix")
    for i in range(len(activities)):
        for j in range(len(activities)):
            color = "white" if cm[i, j] > cm.max() / 2 else "black"
            ax.text(j, i, str(cm[i, j]), ha="center", va="center", color=color, fontsize=9)
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    plt.tight_layout()
    plt.savefig(out_dir / "confusion_matrix.png", dpi=120)
    plt.close()

    print(
        f"[eval] saved → {out_dir}/metrics.json, classification_report.json, confusion_matrix.png"
    )


if __name__ == "__main__":
    main()
