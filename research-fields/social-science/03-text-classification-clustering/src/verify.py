"""End-to-end verification for the C-3 pipeline artifacts.

Checks that downstream outputs are provable, aligned, and internally consistent.

Usage:
    python src/verify.py --embeddings data/embeddings/sentiment.npy \
                         --labels data/synthetic_sentiment.csv \
                         --id-col id --label-col label
    python src/verify.py --embeddings data/embeddings/topic.npy \
                         --clusters data/output/topic-clusters.json \
                         --cluster-labels data/output/topic-labels.json \
                         --id-col id

Fails hard (non-zero exit) on any mismatch so it is safe to wire into CI/workshop
"final green check" steps.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--embeddings", required=True, type=Path)
    p.add_argument("--labels", type=Path, default=None,
                   help="Optional CSV whose --id-col must align with embeddings.")
    p.add_argument("--label-col", default="label")
    p.add_argument("--clusters", type=Path, default=None,
                   help="Optional cluster.py output JSON to cross-check.")
    p.add_argument("--cluster-labels", type=Path, default=None,
                   help="Optional label_clusters.py output JSON to cross-check.")
    p.add_argument("--id-col", required=True)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    failures: list[str] = []

    if not args.embeddings.exists():
        raise SystemExit(f"ERROR: embeddings not found: {args.embeddings}")

    ids_csv = args.embeddings.with_suffix(".ids.csv")
    cleaned_csv = args.embeddings.with_suffix(".cleaned.csv")
    manifest_path = args.embeddings.with_suffix(".manifest.json")
    for req in (ids_csv, cleaned_csv, manifest_path):
        if not req.exists():
            failures.append(f"missing embed artifact: {req}")

    if failures:
        for f in failures:
            print(f"[verify] FAIL: {f}", file=sys.stderr)
        return 1

    manifest = json.loads(manifest_path.read_text())

    # 1. Hash chain: manifest.output_npy_sha256 must match on-disk .npy.
    on_disk_sha = _sha256(args.embeddings)
    if manifest.get("output_npy_sha256") != on_disk_sha:
        failures.append(f"embeddings sha mismatch: manifest={manifest.get('output_npy_sha256')!r} "
                        f"on_disk={on_disk_sha!r} (was the .npy edited after manifest write?)")

    # 2. Shape and NaN/Inf.
    X = np.load(args.embeddings)
    if not np.isfinite(X).all():
        n_bad = int((~np.isfinite(X)).sum())
        failures.append(f"embeddings contain {n_bad} non-finite values (NaN/Inf)")
    if manifest.get("n_rows") and X.shape[0] != manifest["n_rows"]:
        failures.append(f"embeddings rows {X.shape[0]} != manifest n_rows {manifest['n_rows']}")
    if manifest.get("dimensions") and X.shape[1] != manifest["dimensions"]:
        failures.append(f"embeddings dim {X.shape[1]} != manifest dimensions {manifest['dimensions']}")

    # 3. ids.csv rows match embeddings rows.
    ids_df = pd.read_csv(ids_csv)
    if len(ids_df) != X.shape[0]:
        failures.append(f"ids.csv rows {len(ids_df)} != embedding rows {X.shape[0]}")
    embed_ids = [s.lstrip("'") for s in ids_df["id"].astype(str).tolist()]

    # 4. cleaned.csv rows match ids.csv (and cleaned_text non-empty).
    cleaned_df = pd.read_csv(cleaned_csv)
    if len(cleaned_df) != len(ids_df):
        failures.append(f"cleaned.csv rows {len(cleaned_df)} != ids.csv rows {len(ids_df)}")
    if cleaned_df["cleaned_text"].isna().any() or (cleaned_df["cleaned_text"].astype(str).str.len() == 0).any():
        failures.append("cleaned.csv has empty cleaned_text rows (should have been rejected in embed.py)")

    # 5. Labels alignment.
    if args.labels is not None:
        labels_df = pd.read_csv(args.labels)
        if args.id_col not in labels_df.columns:
            failures.append(f"labels CSV missing --id-col {args.id_col!r}")
        elif labels_df[args.id_col].astype(str).tolist() != embed_ids:
            failures.append("labels CSV id order does not match embeddings ids.csv")
        if args.label_col in labels_df.columns and labels_df[args.label_col].isna().any():
            n = int(labels_df[args.label_col].isna().sum())
            failures.append(f"labels CSV has {n} missing values in --label-col {args.label_col!r}")

    # 6. Cluster output cross-check.
    if args.clusters is not None:
        clusters = json.loads(args.clusters.read_text())
        assignments = clusters.get("cluster_assignments") or []
        if len(assignments) != X.shape[0]:
            failures.append(f"cluster_assignments length {len(assignments)} != embedding rows {X.shape[0]}")
        selected_k = clusters.get("selected_k")
        cluster_sizes = clusters.get("cluster_sizes")
        if isinstance(cluster_sizes, list) and selected_k is not None and len(cluster_sizes) != selected_k:
            failures.append(f"cluster_sizes length {len(cluster_sizes)} != selected_k {selected_k}")
        if isinstance(cluster_sizes, list) and cluster_sizes and sum(cluster_sizes) != X.shape[0]:
            failures.append(f"cluster_sizes sum {sum(cluster_sizes)} != embedding rows {X.shape[0]}")

        if args.cluster_labels is not None:
            cluster_labels = json.loads(args.cluster_labels.read_text())
            label_map = cluster_labels.get("labels") or {}
            if selected_k is not None and len(label_map) != selected_k:
                failures.append(f"cluster labels count {len(label_map)} != selected_k {selected_k}")
            if "label_model" not in cluster_labels or "label_model_version" not in cluster_labels:
                failures.append("cluster labels file missing label_model / label_model_version provenance")

    if failures:
        for f in failures:
            print(f"[verify] FAIL: {f}", file=sys.stderr)
        return 1

    print(f"[verify] OK: {args.embeddings.name} passed all checks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
