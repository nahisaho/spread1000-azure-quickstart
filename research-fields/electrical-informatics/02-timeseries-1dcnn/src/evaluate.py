"""
公式 test (2,947 窓, 未知 9 被験者) で 1 回だけ評価.

train.py で計算した mean/std を必ず再利用 (train に fit した統計を test に適用).
成果物: metrics.json, classification_report.json, confusion_matrix.png
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
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from torch.utils.data import DataLoader, TensorDataset

from model import BiosignalCNN

ROOT = Path(__file__).resolve().parents[1]
NPZ_PATH = ROOT / "data" / "har_windows.npz"
OUT_DIR = ROOT / "outputs"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    p.add_argument("--batch-size", type=int, default=256)
    p.add_argument("--output-dir", type=Path, default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = args.output_dir or OUT_DIR
    ckpt_path = out_dir / "best_model.pt"
    norm_path = out_dir / "normalization.npz"

    if not ckpt_path.exists() or not norm_path.exists():
        raise FileNotFoundError(
            "best_model.pt または normalization.npz が見つかりません。"
            " 先に train.py を実行してください。"
        )

    device = torch.device(args.device)
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=True)
    activities = list(ckpt["activities"])

    model = BiosignalCNN(
        n_channels=ckpt.get("n_channels", 9),
        n_classes=ckpt.get("n_classes", 6),
        dropout=ckpt.get("dropout", 0.30),
    ).to(device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    data = np.load(NPZ_PATH, allow_pickle=True)
    X_test, y_test = data["X_test"], data["y_test"]
    subj_test = data["subj_test"]

    norm = np.load(norm_path)
    mean, std = norm["mean"], norm["std"]
    X_test = ((X_test - mean) / std).astype(np.float32)
    print(f"[eval] test: X={X_test.shape}, subjects={sorted(set(subj_test.tolist()))}")

    loader = DataLoader(
        TensorDataset(torch.from_numpy(X_test), torch.from_numpy(y_test)),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=0,
    )

    preds = []
    with torch.no_grad():
        for xb, _ in loader:
            preds.append(model(xb.to(device)).argmax(-1).cpu().numpy())
    y_pred = np.concatenate(preds)
    y_true = y_test

    accuracy = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro"))
    report = classification_report(
        y_true,
        y_pred,
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
    }
    with (out_dir / "metrics.json").open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    with (out_dir / "classification_report.json").open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("[eval] test accuracy = {:.4f}".format(accuracy))
    print("[eval] test macro-F1 = {:.4f}".format(macro_f1))
    for name, val in per_class_f1.items():
        print(f"[eval]   {name:20s} F1 = {val:.4f}")

    # Confusion matrix PNG
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
