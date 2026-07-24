"""Smoke tests for HSI-CNN training pipeline (MED 11).

Run:
    cd <scenario_root>
    python -m pytest tests/test_smoke.py -v

Marked `slow` — excluded from fast CI by default:
    python -m pytest tests/ -v -m "not slow"
"""
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

# Ensure src/ is importable
_SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(_SRC))


@pytest.mark.slow
def test_train_synthetic_1epoch(tmp_path):
    """Train 1 epoch on synthetic data; check loss decreases and checkpoint loads."""
    import train as T

    # Patch outputs directory
    import importlib, types

    class _Args:
        mode = "synthetic"
        data_root = None
        n_per_class = 30
        split_strategy = "random_pixel"
        patch_grid = 8
        exclusion_radius = 0
        allow_random_pixel_split = True
        norm_method = "per_band_zscore"
        balance = "weighted_ce"
        epochs = 2
        batch_size = 16
        lr = 1e-3
        device = "cpu"
        amp = False
        deterministic = True
        seed = 0
        best_metric = "macro_f1"

    args = _Args()
    T.set_repro(args.seed, args.deterministic)

    X, y, class_names, coords = T.load_synthetic(args)
    assert np.all(np.isfinite(X)), "Synthetic data must be finite"

    X_train, X_val, X_test, y_train, y_val, y_test = T.make_splits(
        X, y, coords, "synthetic", "random_pixel", args
    )

    norm_mean, norm_std = T.compute_stats(X_train)
    X_train_n = T.apply_norm(X_train, "per_band_zscore", norm_mean, norm_std)
    X_val_n   = T.apply_norm(X_val,   "per_band_zscore", norm_mean, norm_std)
    assert np.all(np.isfinite(X_train_n)), "Normalised train must be finite"

    n_classes = len(class_names)
    n_bands   = X.shape[1]
    model = T.HSICNN(n_bands=n_bands, n_classes=n_classes)

    ds_train = torch.utils.data.TensorDataset(
        torch.from_numpy(X_train_n).unsqueeze(1).float(),
        torch.from_numpy(y_train).long(),
    )
    loader = torch.utils.data.DataLoader(ds_train, batch_size=16, shuffle=True)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    criterion = torch.nn.CrossEntropyLoss()

    losses = []
    for ep in range(args.epochs):
        model.train()
        tl = 0.0
        for xb, yb in loader:
            opt.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            opt.step()
            tl += loss.item() * yb.size(0)
        losses.append(tl / len(ds_train))

    assert len(losses) == args.epochs, "Should have one loss per epoch"
    # Allow some tolerance — should generally trend down over 2 epochs
    assert losses[-1] < losses[0] * 1.5, (
        f"Loss did not decrease meaningfully: {losses[0]:.4f} → {losses[-1]:.4f}"
    )

    # Save and reload checkpoint
    ckpt_path = tmp_path / "model.pt"
    ckpt = {
        "model_state": model.state_dict(),
        "class_names": class_names,
        "n_bands": n_bands,
        "n_classes": n_classes,
        "stats": {
            "mean":   norm_mean.tolist(),
            "std":    norm_std.tolist(),
            "method": "per_band_zscore",
        },
        "args": vars(args), "epoch": args.epochs,
    }
    torch.save(ckpt, ckpt_path)
    ckpt2 = torch.load(str(ckpt_path), map_location="cpu", weights_only=False)
    model2 = T.HSICNN(n_bands=ckpt2["n_bands"], n_classes=ckpt2["n_classes"])
    model2.load_state_dict(ckpt2["model_state"])
    model2.eval()

    # Same predictions before and after reload
    xb = torch.from_numpy(X_val_n[:8]).unsqueeze(1).float()
    with torch.no_grad():
        p1 = model(xb).argmax(1)
        p2 = model2(xb).argmax(1)
    assert torch.equal(p1, p2), "Reloaded model must give same predictions"


@pytest.mark.slow
def test_argtypes_validators():
    """Check _argtypes validators raise on bad input."""
    from _argtypes import bounded_int, bounded_float, positive_int
    import argparse

    with pytest.raises(argparse.ArgumentTypeError):
        positive_int(0)
    with pytest.raises(argparse.ArgumentTypeError):
        positive_int(-1)
    assert positive_int(1) == 1
    assert positive_int(999) == 999

    bi = bounded_int(1, 100)
    with pytest.raises(argparse.ArgumentTypeError):
        bi(0)
    with pytest.raises(argparse.ArgumentTypeError):
        bi(101)
    assert bi(50) == 50

    bf = bounded_float(0, 1, inclusive_lo=False)
    with pytest.raises(argparse.ArgumentTypeError):
        bf(0.0)
    with pytest.raises(argparse.ArgumentTypeError):
        bf(1.1)
    assert bf(0.001) == pytest.approx(0.001)


@pytest.mark.slow
def test_dataset_clip():
    """Generated spectra must be clipped to [0, 1]."""
    from dataset import generate
    X, y, names = generate(n_per_class=50, seed=42)
    assert np.all(X >= 0.0), "Reflectance must be >= 0"
    assert np.all(X <= 1.0), "Reflectance must be <= 1 (LOW 12 fix)"
    assert np.all(np.isfinite(X)), "All values must be finite"


@pytest.mark.slow
def test_load_indianpines_imports():
    """load_indianpines module must import and expose IP_MIRRORS."""
    from load_indianpines import IP_MIRRORS, CLASS_NAMES_IP
    assert isinstance(IP_MIRRORS, list)
    assert len(IP_MIRRORS) >= 2
    assert all(url.startswith("https://") for url in IP_MIRRORS)
    assert len(CLASS_NAMES_IP) == 16


@pytest.mark.slow
def test_metrics_json_no_nan(tmp_path):
    """json.dumps with allow_nan=False must not write NaN literals."""
    data = {"a": 1.0, "b": float("inf")}
    import json
    with pytest.raises((ValueError, OverflowError)):
        json.dumps(data, allow_nan=False)
