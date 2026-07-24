"""
gplearn SymbolicRegressor で観測データから数式を発見する.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from gplearn.genetic import SymbolicRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from _argtypes import bounded_int, finite_nonneg_float

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs"

BUDGET_WARN = 60_000    # population × generations soft cap
BUDGET_LOW_MEM = 200_000  # enable low_memory above this


def parse_args():
    p = argparse.ArgumentParser(
        description="Discover a symbolic expression from .npz data."
    )
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--population", type=bounded_int("population", 10, 2000),
                   default=2000, help="Population size [10, 2000]")
    p.add_argument("--generations", type=bounded_int("generations", 1, 200),
                   default=30, help="Number of generations [1, 200]")
    p.add_argument("--parsimony", type=float, default=0.001,
                   help="式の長さペナルティ")
    p.add_argument("--test-size", type=float, default=0.15,
                   help="Test fraction (default 0.15)")
    p.add_argument("--val-size", type=float, default=0.15,
                   help="Validation fraction (default 0.15)")
    p.add_argument("--noise", type=finite_nonneg_float("noise"), default=None,
                   help="Noise std-dev override (must be finite >= 0)")
    p.add_argument("--n-samples", type=bounded_int("n-samples", 50, 100_000),
                   default=None, help="Override sample count [50, 100000]")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--allow-long-run", action="store_true",
                   help=f"Required when population × generations > {BUDGET_WARN}")
    return p.parse_args()


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


def _file_sha256(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    a = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    budget = a.population * a.generations
    if budget > BUDGET_WARN and not a.allow_long_run:
        print(
            f"[error] budget = population({a.population}) × generations({a.generations}) "
            f"= {budget} > {BUDGET_WARN}. Pass --allow-long-run to proceed.",
            file=sys.stderr,
        )
        sys.exit(1)
    low_memory = budget > BUDGET_LOW_MEM

    d = np.load(a.data, allow_pickle=True)
    X = np.asarray(d["X"], dtype=np.float64)
    y = np.asarray(d["y"], dtype=np.float64)

    # Load provenance from data file where available
    target_formula = str(d["target_formula"]) if "target_formula" in d else "unknown"
    data_noise = float(d["noise"]) if "noise" in d else None
    data_seed = int(d["seed"]) if "seed" in d else None

    assert np.isfinite(X).all(), "X loaded from file contains NaN or Inf"
    assert np.isfinite(y).all(), "y loaded from file contains NaN or Inf"
    assert X.shape[0] == y.shape[0], "X and y length mismatch in data file"

    # 70 / 15 / 15 split: first split off test, then val from the remainder
    X_tmp, X_te, y_tmp, y_te = train_test_split(
        X, y, test_size=a.test_size, random_state=a.seed
    )
    val_frac_of_tmp = a.val_size / (1.0 - a.test_size)
    X_tr, X_val, y_tr, y_val = train_test_split(
        X_tmp, y_tmp, test_size=val_frac_of_tmp, random_state=a.seed
    )
    print(
        f"[data] train={X_tr.shape} val={X_val.shape} test={X_te.shape}"
    )

    est = SymbolicRegressor(
        population_size=a.population,
        generations=a.generations,
        function_set=("add", "sub", "mul", "div", "sqrt", "log", "sin", "cos"),
        metric="mean absolute error",
        parsimony_coefficient=a.parsimony,
        p_crossover=0.7,
        p_subtree_mutation=0.1,
        p_hoist_mutation=0.05,
        p_point_mutation=0.1,
        max_samples=0.9,
        random_state=a.seed,
        verbose=1,
        n_jobs=1,
        low_memory=low_memory,
    )
    est.fit(X_tr, y_tr)

    y_pred_tr = est.predict(X_tr)
    y_pred_val = est.predict(X_val)
    y_pred_te = est.predict(X_te)

    assert np.isfinite(y_pred_tr).all(), "Train predictions contain NaN/Inf"
    assert np.isfinite(y_pred_val).all(), "Val predictions contain NaN/Inf"
    assert np.isfinite(y_pred_te).all(), "Test predictions contain NaN/Inf"

    r2_tr = float(r2_score(y_tr, y_pred_tr))
    r2_val = float(r2_score(y_val, y_pred_val))
    r2_te = float(r2_score(y_te, y_pred_te))
    mse_val = float(mean_squared_error(y_val, y_pred_val))
    mse_te = float(mean_squared_error(y_te, y_pred_te))
    program = str(est._program)
    length = int(est._program.length_)

    print(
        f"[eval] R² train={r2_tr:.4f}  val={r2_val:.4f}  test={r2_te:.4f}  "
        f"MSE val={mse_val:.4f}  MSE test={mse_te:.4f}"
    )
    print(f"[eval] discovered program (length {length}):")
    print("       ", program)

    (OUT_DIR / "best_program.txt").write_text(program + "\n", encoding="utf-8")

    # Fitness curve (raw MAE, no parsimony component)
    gens = list(range(len(est.run_details_["best_fitness"])))
    plt.figure(figsize=(6, 4))
    plt.plot(gens, est.run_details_["best_fitness"], marker="o", label="best raw fitness (MAE)")
    plt.plot(gens, est.run_details_["average_fitness"], marker="s", alpha=0.4, label="avg raw fitness (MAE)")
    plt.xlabel("generation")
    plt.ylabel("raw fitness (MAE)")
    plt.title("Symbolic regression evolution")
    plt.legend(); plt.grid(alpha=0.3)
    plt.tight_layout(); plt.savefig(OUT_DIR / "fitness_curve.png", dpi=120); plt.close()

    # Predicted vs true (test set)
    plt.figure(figsize=(5, 5))
    lo = float(min(y_te.min(), y_pred_te.min()))
    hi = float(max(y_te.max(), y_pred_te.max()))
    plt.plot([lo, hi], [lo, hi], "k--", alpha=0.5)
    plt.scatter(y_te, y_pred_te, alpha=0.5)
    plt.xlabel("true y"); plt.ylabel("predicted y")
    plt.title(f"Test R² = {r2_te:.3f}")
    plt.grid(alpha=0.3)
    plt.tight_layout(); plt.savefig(OUT_DIR / "pred_vs_true.png", dpi=120); plt.close()

    import gplearn
    import sklearn
    import matplotlib as mpl

    metrics = {
        "r2_train": r2_tr,
        "r2_val": r2_val,
        "r2_test": r2_te,
        "mse_val": mse_val,
        "mse_test": mse_te,
        "program": program,
        "length": length,
        "input_sha256": _file_sha256(a.data),
        "generator_params": {
            "target_formula": target_formula,
            "noise": data_noise,
            "seed": data_seed,
        },
        "cli_args": {
            "data": str(a.data),
            "population": a.population,
            "generations": a.generations,
            "parsimony": a.parsimony,
            "test_size": a.test_size,
            "val_size": a.val_size,
            "seed": a.seed,
            "allow_long_run": a.allow_long_run,
        },
        "versions": {
            "python": sys.version,
            "numpy": np.__version__,
            "sklearn": sklearn.__version__,
            "gplearn": gplearn.__version__,
            "matplotlib": mpl.__version__,
        },
        "git_sha": _git_sha(),
        "model_params": {
            "parsimony_coefficient": a.parsimony,
            "function_set": ["add", "sub", "mul", "div", "sqrt", "log", "sin", "cos"],
            "low_memory": low_memory,
        },
    }
    with (OUT_DIR / "metrics.json").open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, allow_nan=False)
    print(
        f"[train] saved → {OUT_DIR}/best_program.txt, "
        f"fitness_curve.png, pred_vs_true.png, metrics.json"
    )


if __name__ == "__main__":
    main()
