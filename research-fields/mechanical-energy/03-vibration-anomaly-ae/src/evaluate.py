"""
テストセット (正常 + 異常混合) で AE の再構成 MSE 分布と評価指標を計算.
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
    roc_auc_score, precision_recall_curve, confusion_matrix, f1_score,
    precision_score, recall_score,
)

from model import Conv1DAE

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--output-dir", type=Path, default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = args.output_dir or OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device(args.device)

    data = np.load(args.data)
    X_test = data["X_test"].astype(np.float32)
    y_test = data["y_test"].astype(np.int64)
    seq_len = int(data["sample_len"])

    ck = torch.load(args.model, map_location=device, weights_only=True)
    mu, sigma = float(ck["mu"]), float(ck["sigma"])
    threshold = float(ck["threshold"])
    model = Conv1DAE(latent_dim=int(ck["latent_dim"]), seq_len=seq_len).to(device)
    model.load_state_dict(ck["model_state_dict"])
    model.eval()

    X_test_n = (X_test - mu) / sigma
    x_tensor = torch.from_numpy(X_test_n).unsqueeze(1)

    scores = np.zeros(len(X_test), dtype=np.float32)
    with torch.no_grad():
        for i in range(0, len(X_test), args.batch_size):
            xb = x_tensor[i:i + args.batch_size].to(device)
            xr = model(xb)
            err = ((xr - xb) ** 2).mean(dim=(1, 2)).cpu().numpy()
            scores[i:i + len(err)] = err

    # metrics
    auc = float(roc_auc_score(y_test, scores))
    y_pred = (scores > threshold).astype(np.int64)
    p = float(precision_score(y_test, y_pred, zero_division=0))
    r = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    cm = confusion_matrix(y_test, y_pred)

    print(f"[eval] threshold={threshold:.6f}")
    print(f"[eval] ROC-AUC = {auc:.4f}")
    print(f"[eval] precision={p:.3f}  recall={r:.3f}  F1={f1:.3f}")
    print(f"[eval] confusion matrix (rows=true, cols=pred):")
    print(f"        pred_neg  pred_pos")
    print(f" neg    {cm[0,0]:8d}  {cm[0,1]:8d}")
    print(f" pos    {cm[1,0]:8d}  {cm[1,1]:8d}")

    # スコア分布ヒスト
    plt.figure(figsize=(7, 4))
    plt.hist(scores[y_test == 0], bins=40, alpha=0.6, label="normal", color="tab:blue")
    plt.hist(scores[y_test == 1], bins=40, alpha=0.6, label="anomaly", color="tab:red")
    plt.axvline(threshold, color="black", linestyle="--", label=f"threshold={threshold:.4f}")
    plt.xlabel("reconstruction MSE")
    plt.ylabel("count")
    plt.title(f"AE score distribution  |  ROC-AUC={auc:.3f}  F1={f1:.3f}")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "score_distribution.png", dpi=120)
    plt.close()

    # PR-curve
    prec_arr, rec_arr, _ = precision_recall_curve(y_test, scores)
    plt.figure(figsize=(5, 4))
    plt.plot(rec_arr, prec_arr, linewidth=2)
    plt.xlabel("recall")
    plt.ylabel("precision")
    plt.title("Precision-Recall")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_dir / "pr_curve.png", dpi=120)
    plt.close()

    with (out_dir / "eval_metrics.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "roc_auc": round(auc, 4),
                "threshold": round(threshold, 6),
                "precision": round(p, 4),
                "recall": round(r, 4),
                "f1": round(f1, 4),
                "confusion_matrix": cm.tolist(),
                "n_test": int(len(y_test)),
                "n_positive": int(y_test.sum()),
            },
            f,
            indent=2,
        )
    print(f"[eval] saved → {out_dir}/score_distribution.png, pr_curve.png, eval_metrics.json")


if __name__ == "__main__":
    main()
