"""KMeans clustering with silhouette-driven k selection.

Usage:
    python src/cluster.py --embeddings data/embeddings/topic.npy \
        --texts data/synthetic_topic.csv --text-col text \
        --k-range 2 6

Outputs:
    data/output/<stem>-clusters.json — chosen k, silhouette per k,
        cluster assignments, top-3 centroid-nearest text indices per cluster
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--embeddings", required=True, type=Path)
    p.add_argument("--texts", required=True, type=Path,
                   help="CSV whose rows align with embeddings. Prefer <embeddings>.cleaned.csv from embed.py.")
    p.add_argument("--id-col", required=True,
                   help="ID column that must match embed.py's --id-col to prevent silent misalignment.")
    p.add_argument("--text-col", default="text",
                   help="If --texts is embed.py's *.cleaned.csv, use --text-col cleaned_text.")
    p.add_argument("--k-range", nargs=2, type=int, metavar=("KMIN", "KMAX"), default=[2, 6])
    p.add_argument("--random-state", type=int, default=42)
    p.add_argument("--top-per-cluster", type=int, default=3,
                   help="Number of centroid-nearest examples per cluster to save.")
    p.add_argument("--min-cluster-size", type=int, default=2,
                   help="Reject k values that produce clusters smaller than this.")
    p.add_argument("--n-init", type=int, default=10)
    p.add_argument("--output", type=Path, default=None)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    X = np.load(args.embeddings)
    if X.dtype != np.float32:
        X = X.astype(np.float32)
    X = normalize(X, norm="l2")

    texts_df = pd.read_csv(args.texts)
    if args.text_col not in texts_df.columns:
        raise SystemExit(f"ERROR: --text-col {args.text_col!r} not in {list(texts_df.columns)}")
    if args.id_col not in texts_df.columns:
        raise SystemExit(f"ERROR: --id-col {args.id_col!r} not in {list(texts_df.columns)}")

    # Enforce id alignment: cluster.py MUST see the same ordering as embed.py.
    ids_csv = args.embeddings.with_suffix(".ids.csv")
    if not ids_csv.exists():
        raise SystemExit(f"ERROR: {ids_csv} not found. Re-run src/embed.py first.")
    embed_ids = [s.lstrip("'") for s in pd.read_csv(ids_csv)["id"].astype(str).tolist()]
    current_ids = texts_df[args.id_col].astype(str).tolist()
    if embed_ids != current_ids:
        raise SystemExit(
            "ERROR: --texts id column does not match embedding ids.csv (order/content differ). "
            "Use the .cleaned.csv artifact produced by embed.py."
        )

    if texts_df[args.text_col].isna().any():
        n = int(texts_df[args.text_col].isna().sum())
        raise SystemExit(f"ERROR: --text-col has {n} missing values.")
    texts = texts_df[args.text_col].astype(str).tolist()
    if len(texts) != X.shape[0]:
        raise SystemExit(f"ERROR: text rows ({len(texts)}) != embedding rows ({X.shape[0]}).")

    # Duplicate embeddings can collapse clusters and crash silhouette_score.
    _, unique_first_idx = np.unique(X, axis=0, return_index=True)
    n_unique = len(unique_first_idx)
    if n_unique < X.shape[0]:
        print(f"[cluster] WARNING: {X.shape[0] - n_unique} duplicate embedding vectors detected "
              f"({n_unique} unique / {X.shape[0]} total). Silhouette / KMeans behavior may be degraded.",
              file=sys.stderr)

    kmin, kmax = args.k_range
    if kmin < 2:
        raise SystemExit("ERROR: --k-range KMIN must be >= 2 (silhouette undefined for k=1).")
    if kmax >= X.shape[0]:
        raise SystemExit(f"ERROR: --k-range KMAX ({kmax}) must be < n_samples ({X.shape[0]}).")
    if kmax > n_unique:
        raise SystemExit(f"ERROR: --k-range KMAX ({kmax}) > n_unique_vectors ({n_unique}); "
                         "duplicates would force empty clusters.")

    scores: dict[int, float] = {}
    rejected: dict[int, str] = {}
    fitted: dict[int, KMeans] = {}
    for k in range(kmin, kmax + 1):
        km = KMeans(n_clusters=k, n_init=args.n_init, random_state=args.random_state)
        labels_k = km.fit_predict(X)
        unique_labels = np.unique(labels_k)
        if len(unique_labels) < 2:
            rejected[k] = "collapsed to single cluster"
            print(f"[cluster] k={k}: REJECTED ({rejected[k]})", file=sys.stderr)
            continue
        sizes = np.bincount(labels_k, minlength=k)
        if sizes.min() < args.min_cluster_size:
            rejected[k] = f"min cluster size {int(sizes.min())} < {args.min_cluster_size}"
            print(f"[cluster] k={k}: REJECTED ({rejected[k]})", file=sys.stderr)
            continue
        score = float(silhouette_score(X, labels_k, metric="cosine"))
        scores[k] = score
        fitted[k] = km
        print(f"[cluster] k={k}: silhouette(cosine)={score:.4f} sizes={sizes.tolist()}")

    if not scores:
        raise SystemExit("ERROR: no k in --k-range produced a valid clustering.")
    best_k = max(scores, key=scores.get)
    print(f"[cluster] highest-silhouette k={best_k} (silhouette={scores[best_k]:.4f}). "
          "This is a candidate, not the ground-truth optimal k.")

    km = fitted[best_k]
    cluster_labels = km.labels_.tolist()
    centroids = km.cluster_centers_

    top_per_cluster: dict[int, list[dict]] = {}
    for c in range(best_k):
        member_idx = np.where(km.labels_ == c)[0]
        if len(member_idx) == 0:
            top_per_cluster[c] = []
            continue
        # cosine distance to centroid = 1 - dot(unit(x), unit(centroid))
        cn = centroids[c] / (np.linalg.norm(centroids[c]) + 1e-12)
        sims = X[member_idx] @ cn
        order = np.argsort(-sims)[: args.top_per_cluster]
        top_per_cluster[c] = [
            {"row": int(member_idx[j]), "similarity": float(sims[j]), "text": texts[int(member_idx[j])]}
            for j in order
        ]

    out_path = args.output or Path("data/output") / f"{args.embeddings.stem}-clusters.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "embeddings": str(args.embeddings),
        "texts": str(args.texts),
        "text_col": args.text_col,
        "n_samples": int(X.shape[0]),
        "n_unique_vectors": int(n_unique),
        "k_range": [kmin, kmax],
        "silhouette_by_k": scores,
        "rejected_k": rejected,
        "selected_k_note": "Highest silhouette candidate. Not proven optimal — validate with domain knowledge and multi-seed stability.",
        "selected_k": int(best_k),
        "cluster_sizes": np.bincount(km.labels_, minlength=best_k).tolist(),
        "cluster_assignments": cluster_labels,
        "cluster_examples": top_per_cluster,
    }, ensure_ascii=False, indent=2))
    print(f"[cluster] wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
