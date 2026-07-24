"""
テストセット (正常 + 異常混合) で AE の再構成 MSE 分布と評価指標を計算.

閾値はチェックポイント (キャリブレーションセットで決定済み) から読み取る。
テストセットは閾値選択には一切使用しない。
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from sklearn.metrics import (
    roc_auc_score, precision_recall_curve, confusion_matrix, f1_score,
    precision_score, recall_score, ConfusionMatrixDisplay,
)

from model import Conv1DAE

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _validate_test_data(X_test: np.ndarray, y_test: np.ndarray,
                         seq_len: int) -> None:
    if X_test.ndim != 2:
        raise ValueError(f"X_test must be 2-D, got shape {X_test.shape}")
    if X_test.shape[0] == 0:
        raise ValueError("X_test is empty (0 windows)")
    if X_test.shape[1] != seq_len:
        raise ValueError(
            f"X_test has seq_len={X_test.shape[1]}, expected {seq_len} from checkpoint"
        )
    if not np.isfinite(X_test).all():
        raise ValueError("X_test contains NaN or Inf values")
    unique_labels = np.unique(y_test)
    if not set(unique_labels).issubset({0, 1}):
        raise ValueError(f"y_test must be binary (0/1), found labels: {unique_labels}")
    if len(unique_labels) < 2:
        raise ValueError(
            f"Both normal (0) and anomaly (1) classes must be present in y_test. "
            f"Found only: {unique_labels}"
        )
    if y_test.shape[0] != X_test.shape[0]:
        raise RuntimeError(
            f"Shape mismatch: X_test has {X_test.shape[0]} rows "
            f"but y_test has {y_test.shape[0]} entries"
        )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Evaluate the trained AE on the held-out test set."
    )
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--output-dir", type=Path, default=None)
    p.add_argument(
        "--min-roc-auc", type=float, default=0.95,
        help="Minimum acceptable ROC-AUC (exit 2 if unmet).",
    )
    p.add_argument(
        "--min-f1", type=float, default=0.85,
        help="Minimum acceptable F1 (exit 2 if unmet).",
    )
    p.add_argument(
        "--force-mismatch", action="store_true",
        help="Skip data_sha256 / fs mismatch check (use only when intentional).",
    )
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
    threshold  = float(ck["threshold"])
    model_seq_len = int(ck.get("seq_len", seq_len))

    # Provenance check: data SHA-256 and sampling rate (HIGH 6)
    ck_sha = ck.get("data_sha256")
    if ck_sha and not args.force_mismatch:
        actual_sha = _sha256_file(args.data)
        if actual_sha != ck_sha:
            raise SystemExit(
                f"[eval] ERROR: data SHA-256 mismatch!\n"
                f"  checkpoint recorded: {ck_sha}\n"
                f"  current file:        {actual_sha}\n"
                f"Pass --force-mismatch to override (only if intentional)."
            )
    ck_fs = ck.get("fs")
    npz_fs = float(data.get("fs", 5000.0))
    if ck_fs is not None and abs(float(ck_fs) - npz_fs) > 1e-3 and not args.force_mismatch:
        raise SystemExit(
            f"[eval] ERROR: sampling rate mismatch! "
            f"checkpoint fs={ck_fs}, data fs={npz_fs}. "
            f"Pass --force-mismatch to override."
        )

    # Data validation (MED 8)
    _validate_test_data(X_test, y_test, model_seq_len)

    model = Conv1DAE(latent_dim=int(ck["latent_dim"]), seq_len=model_seq_len).to(device)
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

    # Metrics
    auc  = float(roc_auc_score(y_test, scores))
    y_pred = (scores > threshold).astype(np.int64)
    p  = float(precision_score(y_test, y_pred, zero_division=0))
    r  = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    cm = confusion_matrix(y_test, y_pred)

    print(f"[eval] threshold={threshold:.6f}")
    print(f"[eval] ROC-AUC = {auc:.4f}")
    print(f"[eval] precision={p:.3f}  recall={r:.3f}  F1={f1:.3f}")
    print(f"[eval] confusion matrix (rows=true, cols=pred):")
    print(f"        pred_neg  pred_pos")
    print(f" neg    {cm[0,0]:8d}  {cm[0,1]:8d}")
    print(f" pos    {cm[1,0]:8d}  {cm[1,1]:8d}")

    # ── スコア分布ヒスト ──────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(scores[y_test == 0], bins=40, alpha=0.6, label="normal", color="tab:blue")
    ax.hist(scores[y_test == 1], bins=40, alpha=0.6, label="anomaly", color="tab:red")
    ax.axvline(threshold, color="black", linestyle="--",
               label=f"threshold={threshold:.4f}")
    ax.set_xlabel("reconstruction MSE")
    ax.set_ylabel("count")
    ax.set_title(f"AE score distribution  |  ROC-AUC={auc:.3f}  F1={f1:.3f}")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "score_distribution.png", dpi=120)
    plt.close(fig)

    # ── PR-curve ──────────────────────────────────────────────────────
    prec_arr, rec_arr, _ = precision_recall_curve(y_test, scores)
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(rec_arr, prec_arr, linewidth=2)
    ax.set_xlabel("recall")
    ax.set_ylabel("precision")
    ax.set_title("Precision-Recall")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "pr_curve.png", dpi=120)
    plt.close(fig)

    # ── 混同行列 PNG (MED 11) ─────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(4, 4))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["normal", "anomaly"])
    disp.plot(ax=ax, colorbar=False)
    ax.set_title("Confusion Matrix")
    fig.tight_layout()
    fig.savefig(out_dir / "confusion_matrix.png", dpi=120)
    plt.close(fig)

    # ── Threshold vs Metrics カーブ (MED 11) ─────────────────────────
    thresholds = np.linspace(scores.min(), scores.max(), 200)
    th_f1    = []
    th_prec  = []
    th_rec   = []
    for th in thresholds:
        yp = (scores > th).astype(np.int64)
        th_f1.append(f1_score(y_test, yp, zero_division=0))
        th_prec.append(precision_score(y_test, yp, zero_division=0))
        th_rec.append(recall_score(y_test, yp, zero_division=0))
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(thresholds, th_f1,   label="F1",        linewidth=2)
    ax.plot(thresholds, th_prec, label="precision",  linewidth=1.5, linestyle="--")
    ax.plot(thresholds, th_rec,  label="recall",     linewidth=1.5, linestyle=":")
    ax.axvline(threshold, color="black", linestyle="--",
               label=f"selected threshold={threshold:.4f}")
    ax.set_xlabel("threshold (reconstruction MSE)")
    ax.set_ylabel("metric value")
    ax.set_title("Threshold vs F1 / Precision / Recall")
    ax.legend(loc="lower left")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "threshold_vs_metrics.png", dpi=120)
    plt.close(fig)

    output_files = [
        "score_distribution.png",
        "pr_curve.png",
        "confusion_matrix.png",
        "threshold_vs_metrics.png",
        "eval_metrics.json",
    ]
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
                "output_files": output_files,
            },
            f,
            indent=2,
        )
    print(f"[eval] saved → {', '.join(output_files)}")

    # Pass/Fail gate (HIGH 2)
    failures = []
    if auc < args.min_roc_auc:
        failures.append(
            f"ROC-AUC={auc:.4f} < --min-roc-auc={args.min_roc_auc}"
        )
    if f1 < args.min_f1:
        failures.append(
            f"F1={f1:.4f} < --min-f1={args.min_f1}"
        )
    if failures:
        print("\n[eval] FAIL — quality gate not met:")
        for msg in failures:
            print(f"  ✗ {msg}")
        print("  Possible causes: too few epochs, wrong data, threshold mismatch.")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
