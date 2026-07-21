"""Train the small 1D CNN on prepared MIT-BIH windows.

Logs metrics + model to MLflow (AML command job → workspace tracker automatically).
Saves the best-val-macro-F1 checkpoint to --output-dir.
"""
from __future__ import annotations

import argparse
import json
import logging
import random
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # noqa: E402
import matplotlib.pyplot as plt
import mlflow
import mlflow.pytorch
import numpy as np
import torch
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
)
from torch.utils.data import DataLoader, TensorDataset

from model import ECG1DCNN, num_parameters

CLASSES = ["N", "S", "V", "F", "Q"]
logger = logging.getLogger(__name__)


def _seed_all(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def _load_split(prepared_dir: Path, name: str) -> TensorDataset:
    npz = np.load(prepared_dir / f"{name}.npz")
    X = torch.from_numpy(npz["X"]).float()
    y = torch.from_numpy(npz["y"]).long()
    return TensorDataset(X, y)


def _class_weights(y: np.ndarray, n_classes: int) -> torch.Tensor:
    counts = np.bincount(y, minlength=n_classes).astype(np.float64)
    counts[counts == 0] = 1.0  # avoid div0
    inv = counts.sum() / (n_classes * counts)
    return torch.tensor(inv, dtype=torch.float32)


def _evaluate(model: torch.nn.Module, loader: DataLoader, device: torch.device) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    ys, preds = [], []
    with torch.no_grad():
        for x, y in loader:
            x = x.to(device, non_blocking=True)
            out = model(x)
            preds.append(out.argmax(dim=1).cpu().numpy())
            ys.append(y.numpy())
    return np.concatenate(ys), np.concatenate(preds)


def _plot_confusion_matrix(cm: np.ndarray, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(4.5, 4))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(CLASSES)))
    ax.set_yticks(range(len(CLASSES)))
    ax.set_xticklabels(CLASSES)
    ax.set_yticklabels(CLASSES)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title("Confusion matrix (test)")
    for i in range(len(CLASSES)):
        for j in range(len(CLASSES)):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black", fontsize=9)
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True, help="Folder written by prepare_data.py")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    _seed_all(args.seed)

    data_dir = Path(args.data_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    train_ds = _load_split(data_dir, "train")
    val_ds = _load_split(data_dir, "val")
    test_ds = _load_split(data_dir, "test")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Device: %s", device)

    pin = device.type == "cuda"
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True,
                              num_workers=2, pin_memory=pin, drop_last=False)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False,
                            num_workers=2, pin_memory=pin)
    test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False,
                             num_workers=2, pin_memory=pin)

    model = ECG1DCNN(n_classes=len(CLASSES)).to(device)
    weights = _class_weights(train_ds.tensors[1].numpy(), len(CLASSES)).to(device)
    criterion = torch.nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    mlflow.log_params({
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "lr": args.lr,
        "seed": args.seed,
        "n_train": len(train_ds),
        "n_val": len(val_ds),
        "n_test": len(test_ds),
        "n_params": num_parameters(model),
        "device": str(device),
    })

    best_val_f1 = -1.0
    best_state: dict[str, torch.Tensor] | None = None
    for epoch in range(1, args.epochs + 1):
        model.train()
        loss_sum, n_seen = 0.0, 0
        for x, y in train_loader:
            x = x.to(device, non_blocking=True)
            y = y.to(device, non_blocking=True)
            optimizer.zero_grad()
            out = model(x)
            loss = criterion(out, y)
            loss.backward()
            optimizer.step()
            loss_sum += loss.item() * len(y)
            n_seen += len(y)
        train_loss = loss_sum / max(n_seen, 1)

        y_val, p_val = _evaluate(model, val_loader, device)
        val_f1 = f1_score(y_val, p_val, average="macro",
                          labels=list(range(len(CLASSES))), zero_division=0)

        mlflow.log_metrics({"train_loss": train_loss, "val_macro_f1": val_f1}, step=epoch)
        logger.info("epoch=%d train_loss=%.4f val_macro_f1=%.4f", epoch, train_loss, val_f1)

        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    if best_state is None:
        raise RuntimeError("Training produced no checkpoint (best_val_f1 never updated).")
    model.load_state_dict(best_state)

    y_test, p_test = _evaluate(model, test_loader, device)
    test_macro_f1 = f1_score(y_test, p_test, average="macro",
                             labels=list(range(len(CLASSES))), zero_division=0)
    cm = confusion_matrix(y_test, p_test, labels=list(range(len(CLASSES))))
    report = classification_report(y_test, p_test, labels=list(range(len(CLASSES))),
                                   target_names=CLASSES, output_dict=True, zero_division=0)

    mlflow.log_metric("test_macro_f1", test_macro_f1)
    (out_dir / "classification_report.json").write_text(json.dumps(report, indent=2))
    np.savetxt(out_dir / "confusion_matrix.csv", cm, fmt="%d", delimiter=",",
               header=",".join(CLASSES), comments="")

    cm_path = out_dir / "confusion_matrix.png"
    _plot_confusion_matrix(cm, cm_path)
    mlflow.log_artifact(str(cm_path), artifact_path="evaluation")
    mlflow.log_artifact(str(out_dir / "classification_report.json"), artifact_path="evaluation")

    torch.save(best_state, out_dir / "model.pt")
    # code_paths=["model.py"] packages the model definition so the artifact loads
    # standalone in a clean environment (`mlflow.pytorch.load_model` requires the
    # source class to reconstruct the eager model).
    model_code = Path(__file__).parent / "model.py"
    try:
        mlflow.pytorch.log_model(model, name="model", code_paths=[str(model_code)])
    except TypeError:
        # older MLflow versions used artifact_path
        mlflow.pytorch.log_model(model, artifact_path="model", code_paths=[str(model_code)])

    logger.info("Best val macro-F1=%.4f | Test macro-F1=%.4f", best_val_f1, test_macro_f1)
    logger.info("Confusion matrix (rows=true, cols=pred):\n%s", cm)


if __name__ == "__main__":
    main()
