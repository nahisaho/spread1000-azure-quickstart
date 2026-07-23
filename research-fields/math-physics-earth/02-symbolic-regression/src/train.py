"""
gplearn SymbolicRegressor で観測データから数式を発見する.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from gplearn.genetic import SymbolicRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--population", type=int, default=2000)
    p.add_argument("--generations", type=int, default=30)
    p.add_argument("--parsimony", type=float, default=0.001, help="式の長さペナルティ")
    p.add_argument("--test-size", type=float, default=0.2)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def main():
    a = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    d = np.load(a.data)
    X, y = d["X"], d["y"]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=a.test_size, random_state=a.seed)
    print(f"[data] train={X_tr.shape} test={X_te.shape}")

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
    )
    est.fit(X_tr, y_tr)

    y_pred_tr = est.predict(X_tr)
    y_pred_te = est.predict(X_te)
    r2_tr = float(r2_score(y_tr, y_pred_tr))
    r2_te = float(r2_score(y_te, y_pred_te))
    mse_te = float(mean_squared_error(y_te, y_pred_te))
    program = str(est._program)
    length = int(est._program.length_)

    print(f"[eval] R² train={r2_tr:.4f}  R² test={r2_te:.4f}  MSE test={mse_te:.4f}")
    print(f"[eval] discovered program (length {length}):")
    print("       ", program)

    (OUT_DIR / "best_program.txt").write_text(program + "\n", encoding="utf-8")

    # 世代ごとの best fitness curve
    gens = list(range(len(est.run_details_["best_fitness"])))
    plt.figure(figsize=(6, 4))
    plt.plot(gens, est.run_details_["best_fitness"], marker="o", label="best fitness")
    plt.plot(gens, est.run_details_["average_fitness"], marker="s", alpha=0.4, label="avg fitness")
    plt.xlabel("generation")
    plt.ylabel("fitness (MAE + parsimony)")
    plt.title("Symbolic regression evolution")
    plt.legend(); plt.grid(alpha=0.3)
    plt.tight_layout(); plt.savefig(OUT_DIR / "fitness_curve.png", dpi=120); plt.close()

    # 予測 vs 真値
    plt.figure(figsize=(5, 5))
    lo, hi = float(min(y_te.min(), y_pred_te.min())), float(max(y_te.max(), y_pred_te.max()))
    plt.plot([lo, hi], [lo, hi], "k--", alpha=0.5)
    plt.scatter(y_te, y_pred_te, alpha=0.5)
    plt.xlabel("true y"); plt.ylabel("predicted y")
    plt.title(f"Test R² = {r2_te:.3f}")
    plt.grid(alpha=0.3)
    plt.tight_layout(); plt.savefig(OUT_DIR / "pred_vs_true.png", dpi=120); plt.close()

    with (OUT_DIR / "metrics.json").open("w", encoding="utf-8") as f:
        json.dump({"r2_train": r2_tr, "r2_test": r2_te, "mse_test": mse_te,
                   "program": program, "length": length,
                   "generations": a.generations, "population": a.population,
                   "seed": a.seed}, f, indent=2)
    print(f"[train] saved → {OUT_DIR}/best_program.txt, fitness_curve.png, "
          f"pred_vs_true.png, metrics.json")


if __name__ == "__main__":
    main()
