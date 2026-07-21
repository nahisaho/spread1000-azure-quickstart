"""Train a 3-layer GINE on MoleculeNet ESOL for aqueous solubility regression.

Input:
  --esol-csv PATH           Raw delaney-processed.csv (mounted from Data Asset).
  --output-dir PATH         Directory to write metrics.json and best_model.pt.

Logs to MLflow (AML auto-starts the run):
  Params: model, hidden, layers, epochs, patience, lr, batch_size, split_seed
  Per-epoch: train_loss, val_rmse
  Final:    test_rmse, test_mae, test_r2, epochs_run
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from shutil import copy2

import mlflow
import numpy as np
import torch
import torch.nn.functional as F
from sklearn.metrics import mean_absolute_error, r2_score
from torch import nn
from torch_geometric.datasets import MoleculeNet
from torch_geometric.loader import DataLoader
from torch_geometric.nn import GINEConv, global_mean_pool

# PyG 2.7 MoleculeNet featurization dims (from PyG source)
ATOM_DIMS = (119, 9, 11, 12, 9, 5, 8, 2, 2)
BOND_DIMS = (22, 6, 2)


def one_hot(x: torch.Tensor, dims: tuple[int, ...]) -> torch.Tensor:
    return torch.cat(
        [F.one_hot(x[:, i].long(), d) for i, d in enumerate(dims)],
        dim=1,
    ).float()


class SolubilityGINE(nn.Module):
    def __init__(self, hidden: int = 64, layers: int = 3, dropout: float = 0.15):
        super().__init__()
        self.dropout = dropout
        self.atom = nn.Linear(sum(ATOM_DIMS), hidden)
        self.convs = nn.ModuleList(
            [
                GINEConv(
                    nn.Sequential(
                        nn.Linear(hidden, hidden),
                        nn.ReLU(),
                        nn.Linear(hidden, hidden),
                    ),
                    edge_dim=sum(BOND_DIMS),
                )
                for _ in range(layers)
            ]
        )
        self.head = nn.Sequential(
            nn.Linear(hidden, 32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, 1),
        )

    def forward(self, batch) -> torch.Tensor:
        x = self.atom(one_hot(batch.x, ATOM_DIMS))
        e = one_hot(batch.edge_attr, BOND_DIMS)
        for conv in self.convs:
            x = F.dropout(F.relu(conv(x, batch.edge_index, e)), self.dropout, self.training)
        return self.head(global_mean_pool(x, batch.batch)).squeeze(1)


def load_esol(work_dir: Path, asset_csv: Path) -> MoleculeNet:
    """Copy the raw CSV into a writable PyG root and load ESOL."""
    root = work_dir / "esol_root"
    raw_dst = root / "esol" / "raw" / "delaney-processed.csv"
    raw_dst.parent.mkdir(parents=True, exist_ok=True)
    if not raw_dst.exists():
        copy2(asset_csv, raw_dst)
    return MoleculeNet(root=str(root), name="ESOL")


def evaluate(model, loader, mu, sd, device):
    model.eval()
    preds, trues = [], []
    with torch.no_grad():
        for b in loader:
            b = b.to(device)
            preds.append((model(b) * sd + mu).cpu())
            trues.append(b.y.view(-1).cpu())
    y_pred = torch.cat(preds).numpy()
    y_true = torch.cat(trues).numpy()
    rmse = float(np.sqrt(np.mean((y_pred - y_true) ** 2)))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred))
    return rmse, mae, r2


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--esol-csv", required=True, help="Path to mounted delaney-processed.csv")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--hidden", type=int, default=64)
    ap.add_argument("--layers", type=int, default=3)
    ap.add_argument("--epochs", type=int, default=150)
    ap.add_argument("--patience", type=int, default=20)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--weight-decay", type=float, default=1e-4)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[train] device={device} torch={torch.__version__}", flush=True)

    dataset = load_esol(out_dir / "work", Path(args.esol_csv))
    print(f"[train] Loaded ESOL: {len(dataset)} molecules", flush=True)

    idx = torch.randperm(len(dataset), generator=torch.Generator().manual_seed(args.seed))
    n1 = int(0.8 * len(dataset))
    n2 = int(0.9 * len(dataset))
    train_ds = dataset[idx[:n1]]
    val_ds = dataset[idx[n1:n2]]
    test_ds = dataset[idx[n2:]]

    y_train = torch.cat([d.y for d in train_ds]).view(-1)
    mu = y_train.mean().to(device)
    sd = y_train.std().to(device)
    print(f"[train] y mu={mu.item():.3f} sd={sd.item():.3f}", flush=True)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False)
    test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False)

    model = SolubilityGINE(hidden=args.hidden, layers=args.layers).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)

    mlflow.log_params(
        {
            "model": "GINE",
            "hidden": args.hidden,
            "layers": args.layers,
            "epochs_max": args.epochs,
            "patience": args.patience,
            "lr": args.lr,
            "weight_decay": args.weight_decay,
            "batch_size": args.batch_size,
            "split_seed": args.seed,
        }
    )

    best_rmse = float("inf")
    best_state = None
    stale = 0
    epoch = 0

    for epoch in range(1, args.epochs + 1):
        model.train()
        last_loss = None
        for batch in train_loader:
            batch = batch.to(device)
            opt.zero_grad()
            pred = model(batch)
            target = (batch.y.view(-1) - mu) / sd
            loss = F.mse_loss(pred, target)
            loss.backward()
            opt.step()
            last_loss = float(loss.item())

        val_rmse, _, _ = evaluate(model, val_loader, mu, sd, device)
        mlflow.log_metrics({"train_loss": last_loss, "val_rmse": val_rmse}, step=epoch)
        print(f"  epoch {epoch:3d}  train_loss={last_loss:.4f}  val_rmse={val_rmse:.4f}", flush=True)

        if val_rmse < best_rmse:
            best_rmse = val_rmse
            best_state = copy.deepcopy(model.state_dict())
            stale = 0
        else:
            stale += 1
            if stale >= args.patience:
                print(f"[train] Early stop at epoch {epoch} (patience={args.patience})", flush=True)
                break

    assert best_state is not None, "Training loop produced no best state."
    model.load_state_dict(best_state)

    test_rmse, test_mae, test_r2 = evaluate(model, test_loader, mu, sd, device)
    print(
        f"[train] TEST rmse={test_rmse:.4f} mae={test_mae:.4f} r2={test_r2:.4f}",
        flush=True,
    )

    mlflow.log_metrics(
        {
            "test_rmse": test_rmse,
            "test_mae": test_mae,
            "test_r2": test_r2,
            "epochs_run": float(epoch),
            "best_val_rmse": best_rmse,
        }
    )

    # Save artifacts
    metrics_path = out_dir / "metrics.json"
    with metrics_path.open("w") as f:
        json.dump(
            {
                "test_rmse": test_rmse,
                "test_mae": test_mae,
                "test_r2": test_r2,
                "best_val_rmse": best_rmse,
                "epochs_run": epoch,
                "n_train": len(train_ds),
                "n_val": len(val_ds),
                "n_test": len(test_ds),
            },
            f,
            indent=2,
        )
    model_path = out_dir / "best_model.pt"
    torch.save(
        {
            "state_dict": best_state,
            "mu": mu.cpu().item(),
            "sd": sd.cpu().item(),
            "hidden": args.hidden,
            "layers": args.layers,
        },
        model_path,
    )
    mlflow.log_artifact(str(metrics_path))
    mlflow.log_artifact(str(model_path))
    print(f"[train] Wrote {metrics_path} and {model_path}", flush=True)


if __name__ == "__main__":
    main()
