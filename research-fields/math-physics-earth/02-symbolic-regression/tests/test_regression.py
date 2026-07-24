"""Regression test: default seed should recover the target with R² >= 0.99 and length <= 15."""
from __future__ import annotations
import sys
from pathlib import Path

# Ensure src/ is importable
SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import numpy as np
import pytest
from gplearn.genetic import SymbolicRegressor
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

from generate_data import true_fn


def _generate(seed: int = 42, n: int = 200, noise: float = 0.1):
    rng = np.random.default_rng(seed)
    X = rng.uniform(-3.0, 3.0, size=(n, 2)).astype(np.float64)
    y_clean = true_fn(X[:, 0], X[:, 1])
    y = y_clean + rng.normal(0.0, noise, size=n).astype(np.float64)
    return X, y


def test_default_seed_recovers_target():
    """With default seed=42, R² >= 0.99 and expression length <= 15."""
    X, y = _generate(seed=42)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.15, random_state=42)
    val_frac = 0.15 / (1.0 - 0.15)
    X_tr2, X_val, y_tr2, y_val = train_test_split(X_tr, y_tr, test_size=val_frac, random_state=42)

    est = SymbolicRegressor(
        population_size=2000,
        generations=30,
        function_set=("add", "sub", "mul", "div", "sqrt", "log", "sin", "cos"),
        metric="mean absolute error",
        parsimony_coefficient=0.001,
        p_crossover=0.7,
        p_subtree_mutation=0.1,
        p_hoist_mutation=0.05,
        p_point_mutation=0.1,
        max_samples=0.9,
        random_state=42,
        verbose=0,
        n_jobs=1,
    )
    est.fit(X_tr2, y_tr2)

    y_pred_te = est.predict(X_te)
    r2_te = r2_score(y_te, y_pred_te)
    length = int(est._program.length_)

    print(f"\nR²={r2_te:.4f}  length={length}  program={est._program}")
    assert r2_te >= 0.99, f"R² = {r2_te:.4f} < 0.99 — target may not be recoverable"
    assert length <= 15, f"expression length {length} > 15 — too complex"
