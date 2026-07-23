"""Train XGBoost regressor on band gap, compare against baselines.

Usage:
    python src/train.py --features data/features.parquet --output data/metrics.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--features", required=True, type=Path)
    p.add_argument("--output", type=Path, default=Path("data/metrics.json"))
    p.add_argument("--predictions", type=Path, default=Path("data/predictions.parquet"))
    p.add_argument("--test-size", type=float, default=0.2)
    p.add_argument("--n-splits", type=int, default=5)
    p.add_argument("--random-state", type=int, default=42)
    p.add_argument("--n-estimators", type=int, default=500)
    p.add_argument("--max-depth", type=int, default=6)
    p.add_argument("--learning-rate", type=float, default=0.05)
    return p.parse_args()


def main() -> int:
    args = parse_args()

    import numpy as np
    import pandas as pd
    from sklearn.dummy import DummyRegressor
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
    from sklearn.model_selection import GroupKFold, GroupShuffleSplit, cross_val_score
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from xgboost import XGBRegressor

    df = pd.read_parquet(args.features)
    meta_cols = {"material_id", "formula_pretty", "band_gap"}
    feature_cols = [c for c in df.columns if c not in meta_cols]
    X = df[feature_cols].to_numpy(dtype=np.float32)
    y = df["band_gap"].to_numpy(dtype=np.float32)
    ids = df["material_id"].to_numpy()
    # Group by reduced formula so polymorphs of the same composition stay in the
    # same fold. Prevents composition leakage that inflates metrics.
    groups = df["formula_pretty"].to_numpy()
    n_groups = len(np.unique(groups))
    print(f"[train] X shape={X.shape}, y stats: mean={y.mean():.3f} std={y.std():.3f}")
    print(f"[train] {n_groups} unique reduced-formula groups over {len(y)} samples")

    if args.n_splits < 2:
        raise SystemExit(f"ERROR: --n-splits must be >= 2 (got {args.n_splits}).")
    if n_groups < args.n_splits + 2:
        raise SystemExit(
            f"ERROR: {n_groups} unique groups is too few for {args.n_splits}-fold "
            f"GroupKFold + holdout. Fetch more data."
        )

    gss = GroupShuffleSplit(n_splits=1, test_size=args.test_size,
                            random_state=args.random_state)
    tr_idx, te_idx = next(gss.split(X, y, groups=groups))
    X_tr, X_te = X[tr_idx], X[te_idx]
    y_tr, y_te = y[tr_idx], y[te_idx]
    id_tr, id_te = ids[tr_idx], ids[te_idx]
    groups_tr = groups[tr_idx]
    n_groups_tr = len(np.unique(groups_tr))
    assert set(groups[tr_idx]).isdisjoint(set(groups[te_idx])), \
        "composition leakage between train and holdout"
    if n_groups_tr < args.n_splits:
        raise SystemExit(
            f"ERROR: only {n_groups_tr} unique groups in training split, "
            f"cannot run {args.n_splits}-fold GroupKFold. Lower --n-splits or fetch more data."
        )

    dummy = DummyRegressor(strategy="mean")
    linear = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LinearRegression())
    xgb = XGBRegressor(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        learning_rate=args.learning_rate,
        objective="reg:squarederror",
        n_jobs=2,
        random_state=args.random_state,
    )

    cv = GroupKFold(n_splits=args.n_splits)
    results: dict[str, dict] = {}
    for name, model in [("dummy_mean", dummy), ("linear", linear), ("xgboost", xgb)]:
        cv_mae = -cross_val_score(model, X_tr, y_tr, groups=groups_tr, cv=cv,
                                  scoring="neg_mean_absolute_error", n_jobs=1)
        model.fit(X_tr, y_tr)
        pred = model.predict(X_te)
        mae = float(mean_absolute_error(y_te, pred))
        rmse = float(root_mean_squared_error(y_te, pred))
        r2 = float(r2_score(y_te, pred))
        results[name] = {
            "cv_mae_mean": float(cv_mae.mean()),
            "cv_mae_std": float(cv_mae.std()),
            "holdout_mae": mae,
            "holdout_rmse": rmse,
            "holdout_r2": r2,
        }
        print(f"[train] {name:10s}: CV MAE={cv_mae.mean():.3f}±{cv_mae.std():.3f} "
              f"| holdout MAE={mae:.3f} RMSE={rmse:.3f} R²={r2:.3f}")

    # Save holdout predictions from the XGBoost model for downstream analysis.
    pred_df = pd.DataFrame({
        "material_id": id_te,
        "band_gap_true": y_te,
        "band_gap_pred_xgboost": xgb.predict(X_te),
    })
    args.predictions.parent.mkdir(parents=True, exist_ok=True)
    pred_df.to_parquet(args.predictions, index=False)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        "features": str(args.features),
        "n_samples": int(len(y)),
        "n_features": int(X.shape[1]),
        "test_size": args.test_size,
        "n_splits": args.n_splits,
        "random_state": args.random_state,
        "results": results,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False, indent=2))
    print(f"[train] wrote {args.output}")
    print(f"[train] wrote {args.predictions}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
