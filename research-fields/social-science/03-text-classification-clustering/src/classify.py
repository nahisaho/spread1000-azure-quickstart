"""Train a LogisticRegression baseline on precomputed embeddings.

Usage:
    python src/classify.py --embeddings data/embeddings/sentiment.npy \
        --labels data/synthetic_sentiment.csv --label-col label

Outputs:
    stdout — classification_report, confusion_matrix, per-fold macro-F1
    data/output/<name>-cv.json — fold scores + confusion matrix
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_val_score
from sklearn.preprocessing import normalize


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--embeddings", required=True, type=Path)
    p.add_argument("--labels", required=True, type=Path)
    p.add_argument("--label-col", default="label")
    p.add_argument("--n-splits", type=int, default=5)
    p.add_argument("--random-state", type=int, default=42)
    p.add_argument("--output", type=Path, default=None,
                   help="Optional JSON output path. Defaults to data/output/<stem>-cv.json.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    X = np.load(args.embeddings)
    if X.dtype != np.float32:
        X = X.astype(np.float32)
    X = normalize(X, norm="l2")

    labels_df = pd.read_csv(args.labels)
    if args.label_col not in labels_df.columns:
        raise SystemExit(f"ERROR: --label-col {args.label_col!r} not in {list(labels_df.columns)}")
    y = labels_df[args.label_col].astype(str).to_numpy()
    if len(y) != X.shape[0]:
        raise SystemExit(f"ERROR: label rows ({len(y)}) != embedding rows ({X.shape[0]}). "
                         "Check that the CSV order matches the .npy order.")

    # StratifiedKFold requires >= n_splits samples per class.
    class_counts = pd.Series(y).value_counts()
    min_class = int(class_counts.min())
    if min_class < args.n_splits:
        raise SystemExit(
            f"ERROR: smallest class has {min_class} samples < n_splits={args.n_splits}. "
            f"Add more samples or reduce --n-splits.\nCounts:\n{class_counts.to_string()}"
        )

    clf = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        random_state=args.random_state,
    )
    cv = StratifiedKFold(n_splits=args.n_splits, shuffle=True, random_state=args.random_state)

    fold_f1 = cross_val_score(clf, X, y, cv=cv, scoring="f1_macro")
    y_pred = cross_val_predict(clf, X, y, cv=cv)

    print(f"[classify] fold macro-F1: {fold_f1.tolist()}")
    print(f"[classify] mean±std     : {fold_f1.mean():.3f} ± {fold_f1.std():.3f}")
    print("[classify] classification_report:")
    print(classification_report(y, y_pred, digits=3))

    labels_sorted = sorted(set(y))
    cm = confusion_matrix(y, y_pred, labels=labels_sorted)
    print("[classify] confusion_matrix (rows=true, cols=pred):")
    header = "        " + "  ".join(f"{c:>10}" for c in labels_sorted)
    print(header)
    for i, row_label in enumerate(labels_sorted):
        print(f"{row_label:>8}  " + "  ".join(f"{v:>10d}" for v in cm[i]))

    out_path = args.output or Path("data/output") / f"{args.embeddings.stem}-cv.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "embeddings": str(args.embeddings),
        "labels": str(args.labels),
        "label_col": args.label_col,
        "n_samples": int(X.shape[0]),
        "n_features": int(X.shape[1]),
        "n_splits": args.n_splits,
        "fold_macro_f1": fold_f1.tolist(),
        "mean_macro_f1": float(fold_f1.mean()),
        "std_macro_f1": float(fold_f1.std()),
        "labels_sorted": labels_sorted,
        "confusion_matrix": cm.tolist(),
    }, ensure_ascii=False, indent=2))
    print(f"[classify] wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
