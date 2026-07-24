"""評価スクリプト — チェックポイントから指定データを評価する。

Usage:
  # 合成データで再評価
  python src/evaluate.py --mode synthetic

  # 実 Indian Pines (チェックポイントの stats を使って正規化)
  python src/evaluate.py --mode indianpines --data-root data/

  # カスタム
  python src/evaluate.py --mode custom --data-root /path/to/data
  python src/evaluate.py --checkpoint /path/to/model.pt --mode synthetic
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import torch

_SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(_SRC))
from train import (
    HSICNN,
    apply_norm,
    compute_metrics,
    load_custom,
    load_real_indianpines,
    load_synthetic,
    save_cm,
    save_prediction_map,
    sha256_prefix,
)
from sklearn.metrics import confusion_matrix

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Evaluate a saved HSI-CNN checkpoint",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--checkpoint", default=None,
                    help="Path to .pt checkpoint (default: outputs/best_model.pt)")
    ap.add_argument("--mode",
                    choices=["synthetic", "indianpines", "custom"], default="synthetic")
    ap.add_argument("--data-root", default=None)
    ap.add_argument("--n-per-class", type=int, default=200,
                    help="Samples/class (synthetic only)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--batch-size", type=int, default=128)
    ap.add_argument("--device", choices=["cpu", "cuda", "mps", "auto"], default="auto")
    ap.add_argument("--allow-random-pixel-split", action="store_true")
    return ap


def resolve_device(requested: str) -> torch.device:
    if requested == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda")
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")
    return torch.device(requested)


def main() -> None:
    args = build_parser().parse_args()

    outputs = Path(__file__).resolve().parent.parent / "outputs"
    outputs.mkdir(exist_ok=True)

    ckpt_path = Path(args.checkpoint) if args.checkpoint else outputs / "best_model.pt"
    if not ckpt_path.exists():
        raise FileNotFoundError(
            f"Checkpoint not found: {ckpt_path}. "
            "Run train.py first or pass --checkpoint."
        )

    device = resolve_device(args.device)
    log.info("Loading checkpoint: %s", ckpt_path)
    ckpt = torch.load(str(ckpt_path), map_location=device, weights_only=False)

    # Validate checkpoint has normalization stats (HIGH 5)
    if "stats" not in ckpt:
        raise ValueError(
            "Checkpoint missing 'stats' key — normalization parameters not saved. "
            "Re-train with the updated train.py."
        )
    stats = ckpt["stats"]
    if stats.get("method") not in ("per_band_zscore", "per_spectrum_snv", "none"):
        raise ValueError(f"Unknown normalization method in checkpoint: {stats.get('method')!r}")

    class_names = ckpt["class_names"]
    n_bands     = ckpt["n_bands"]
    n_classes   = ckpt["n_classes"]

    model = HSICNN(n_bands=n_bands, n_classes=n_classes).to(device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    log.info("Model: bands=%d  classes=%d  device=%s", n_bands, n_classes, device)

    # Load data
    _args_stub = argparse.Namespace(
        mode=args.mode, data_root=args.data_root,
        n_per_class=args.n_per_class, seed=args.seed,
        allow_random_pixel_split=args.allow_random_pixel_split,
    )
    loaders = {
        "synthetic":   load_synthetic,
        "indianpines": load_real_indianpines,
        "custom":      load_custom,
    }
    X, y, eval_class_names, coords = loaders[args.mode](_args_stub)

    if len(eval_class_names) != n_classes:
        log.warning(
            "Data has %d classes but checkpoint expects %d — "
            "metrics may be unreliable",
            len(eval_class_names), n_classes,
        )

    # Apply normalisation from checkpoint
    norm_mean = norm_std = None
    if stats["method"] == "per_band_zscore":
        if stats["mean"] is None or stats["std"] is None:
            raise ValueError(
                "Checkpoint norm method is per_band_zscore but mean/std are not saved. "
                "Re-train with updated train.py."
            )
        norm_mean = np.array(stats["mean"], dtype=np.float32)
        norm_std  = np.array(stats["std"],  dtype=np.float32)

    X_norm = apply_norm(X, stats["method"], norm_mean, norm_std)
    if not np.all(np.isfinite(X_norm)):
        raise ValueError("Non-finite values after applying checkpoint normalization")

    from torch.utils.data import DataLoader, TensorDataset
    ds = TensorDataset(
        torch.from_numpy(X_norm).unsqueeze(1).float(),
        torch.from_numpy(y).long(),
    )
    loader = DataLoader(ds, batch_size=args.batch_size, shuffle=False)

    y_pred_all, y_true_all = [], []
    with torch.no_grad():
        for xb, yb in loader:
            out = model(xb.to(device))
            y_pred_all.extend(out.argmax(1).cpu().tolist())
            y_true_all.extend(yb.tolist())

    metrics = compute_metrics(y_true_all, y_pred_all, class_names)
    cm = confusion_matrix(y_true_all, y_pred_all, labels=list(range(n_classes)))

    log.info("[eval] acc=%.3f  mF1=%.3f  bal_acc=%.3f  kappa=%.3f",
             metrics["overall_accuracy"], metrics["macro_f1"],
             metrics["balanced_accuracy"], metrics["cohen_kappa"])
    log.info("Per-class F1 (low→high):")
    for cls, f1v in metrics["per_class_f1_sorted"].items():
        log.info("  %-35s %.3f", cls, f1v)

    save_cm(cm, class_names, outputs,
            title=f"Eval acc={metrics['overall_accuracy']:.3f}  mF1={metrics['macro_f1']:.3f}")

    if coords is not None and args.mode != "synthetic":
        H = int(coords[:, 0].max()) + 1
        W = int(coords[:, 1].max()) + 1
        save_prediction_map(
            np.array(y_pred_all), coords, H, W,
            class_names, outputs, y_true=y,
        )

    eval_metrics = {
        "checkpoint": str(ckpt_path),
        "mode": args.mode,
        "dataset_sha256_prefix": sha256_prefix(X),
        "class_names": class_names,
        "norm_method": stats["method"],
        "metrics": metrics,
    }
    out_path = outputs / "eval_metrics.json"
    out_path.write_text(
        json.dumps(eval_metrics, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )
    log.info("Saved eval_metrics.json, confusion_matrix.png/csv")


if __name__ == "__main__":
    main()
