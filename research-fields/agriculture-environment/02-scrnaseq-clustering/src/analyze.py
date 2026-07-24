"""scRNA-seq クラスタリング (scanpy PBMC 3k)

- QC (n_genes, mt%) → normalize_total → log1p → HVG 選択
- scale → PCA 50 → neighbors k=10 → UMAP → Leiden
- rank_genes_groups で各クラスタの marker candidate を抽出
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scanpy as sc

from _argtypes import bounded_float, bounded_int


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


def main() -> None:
    ap = argparse.ArgumentParser(description="scRNA-seq clustering with scanpy")
    ap.add_argument(
        "--resolution",
        type=bounded_float(0.0, 10.0, allow_lo=False),
        default=0.5,
        help="Leiden resolution (0, 10]",
    )
    ap.add_argument(
        "--n-hvg",
        type=int,
        default=2000,
        help="Number of highly variable genes to select",
    )
    ap.add_argument(
        "--n-pcs",
        type=int,
        default=50,
        help="Number of PCA components [2, min(n_obs, n_hvg)-1]",
    )
    ap.add_argument(
        "--k-neighbors",
        type=int,
        default=10,
        help="Number of neighbors for kNN graph [2, n_obs-1]",
    )
    ap.add_argument(
        "--seed",
        type=bounded_int(0, 2**32 - 1),
        default=42,
        help="Random seed [0, 2^32-1]",
    )
    ap.add_argument(
        "--mt-prefix",
        type=str,
        default="MT-",
        help="Mitochondrial gene prefix (MT- human, mt- mouse, pt- plant)",
    )
    ap.add_argument(
        "--zero-center",
        dest="zero_center",
        action="store_true",
        default=True,
        help="Zero-center when scaling (default: True; may densify large matrices)",
    )
    ap.add_argument(
        "--no-zero-center",
        dest="zero_center",
        action="store_false",
        help="Skip zero-centering to preserve sparsity",
    )
    ap.add_argument(
        "--max-dense-cells",
        type=float,
        default=5e7,
        help="If cells*genes exceeds this, zero-center is skipped automatically",
    )
    args = ap.parse_args()

    np.random.seed(args.seed)
    sc.settings.verbosity = 1
    sc.settings.set_figure_params(dpi=100, facecolor="white")

    outputs = Path(__file__).resolve().parent.parent / "outputs"
    data_dir = Path(__file__).resolve().parent.parent / "data"
    outputs.mkdir(exist_ok=True)
    data_dir.mkdir(exist_ok=True)

    # H1: set datasetdir so pbmc3k downloads into data/ not CWD
    sc.settings.datasetdir = str(data_dir)

    print("[data] loading PBMC 3k (auto-download ~5MB on first run)")
    adata = sc.datasets.pbmc3k()
    print(f"[data] cells={adata.n_obs} genes={adata.n_vars}")

    # Compute SHA-256 of downloaded h5ad for provenance (H7, H8)
    h5ad_path = data_dir / "pbmc3k_raw.h5ad"
    dataset_sha256 = _sha256(h5ad_path) if h5ad_path.exists() else "unavailable"

    # H2: post-load validation of n_hvg, n_pcs, k_neighbors
    if args.n_hvg < 50 or args.n_hvg >= adata.n_vars:
        raise ValueError(
            f"--n-hvg={args.n_hvg} must be in [50, {adata.n_vars - 1}] "
            f"(dataset has {adata.n_vars} genes)"
        )
    if args.n_pcs < 2:
        raise ValueError(f"--n-pcs must be >= 2, got {args.n_pcs}")
    if args.k_neighbors < 2 or args.k_neighbors >= adata.n_obs:
        raise ValueError(
            f"--k-neighbors={args.k_neighbors} must be in [2, {adata.n_obs - 1}]"
        )

    print("[qc] annotating mitochondrial genes")
    adata.var["mt"] = adata.var_names.str.startswith(args.mt_prefix)
    sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], inplace=True, log1p=False)

    print("[qc] filtering cells/genes")
    sc.pp.filter_cells(adata, min_genes=200)
    sc.pp.filter_genes(adata, min_cells=3)
    adata = adata[adata.obs["pct_counts_mt"] < 5, :].copy()
    adata = adata[adata.obs["n_genes_by_counts"] < 2500, :].copy()
    print(f"[qc] after: cells={adata.n_obs} genes={adata.n_vars}")

    # M1: preserve raw counts before normalization
    import scipy.sparse as sp
    adata.layers["counts"] = (
        adata.X.copy() if sp.issparse(adata.X) else sp.csr_matrix(adata.X)
    )

    print("[normalize] total-count normalization + log1p")
    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)

    # M1: save QC + counts h5ad before HVG subsetting
    adata.uns["schema_version"] = (
        "qc_counts: .X=log-normalized full matrix; "
        "layers['counts']=raw integer counts"
    )
    adata.write(outputs / "pbmc3k_qc_counts.h5ad")

    print(f"[hvg] selecting top {args.n_hvg} highly variable genes")
    sc.pp.highly_variable_genes(adata, n_top_genes=args.n_hvg, flavor="seurat")
    adata.raw = adata  # .raw.X = log-normalized full-gene matrix
    adata = adata[:, adata.var["highly_variable"]].copy()

    # H4: conditional zero-centering to avoid densification
    print("[scale] scaling to unit variance (clip=10)")
    matrix_size = adata.n_obs * adata.n_vars
    if args.zero_center and matrix_size > args.max_dense_cells:
        warnings.warn(
            f"Matrix size {matrix_size:,} > --max-dense-cells {int(args.max_dense_cells):,}; "
            "skipping zero-center to preserve sparsity. "
            "Use --no-zero-center to suppress this warning, or reduce n_hvg."
        )
        sc.pp.scale(adata, max_value=10, zero_center=False)
    else:
        sc.pp.scale(adata, max_value=10, zero_center=args.zero_center)

    # L1: use sc.pp.pca (canonical API; sc.tl.pca is a legacy alias)
    # H2: clamp n_pcs to valid range post-QC
    max_pcs = min(adata.n_obs, adata.n_vars) - 1
    n_pcs = min(args.n_pcs, max_pcs)
    if n_pcs != args.n_pcs:
        warnings.warn(f"--n-pcs clamped from {args.n_pcs} to {n_pcs} (data shape limit)")
    print(f"[pca] {n_pcs} components")
    sc.pp.pca(adata, n_comps=n_pcs, random_state=args.seed)

    print(f"[neighbors] k={args.k_neighbors}")
    sc.pp.neighbors(adata, n_neighbors=args.k_neighbors, n_pcs=n_pcs, random_state=args.seed)

    print("[umap] embedding")
    sc.tl.umap(adata, random_state=args.seed)

    print(f"[leiden] resolution={args.resolution}")
    sc.tl.leiden(
        adata,
        resolution=args.resolution,
        random_state=args.seed,
        flavor="igraph",
        n_iterations=2,
        directed=False,
    )
    n_clusters = adata.obs["leiden"].nunique()
    print(f"[leiden] found {n_clusters} clusters")

    # H5: Wilcoxon for exploratory marker candidates only (not inference)
    print("[marker] rank_genes_groups (wilcoxon) — exploratory marker candidates")
    warnings.warn(
        "P-values from rank_genes_groups are anti-conservative: clusters are derived from "
        "the same data (double-dipping), and cells from a single donor are NOT independent "
        "replicates. Results are EXPLORATORY MARKER CANDIDATES only. "
        "For differential expression inference, use independent-donor pseudobulk with a "
        "count-model DE tool (e.g., DESeq2, edgeR, muscat)."
    )
    sc.tl.rank_genes_groups(adata, "leiden", method="wilcoxon")

    marker_candidates: dict[str, list[str]] = {}
    for cl in sorted(adata.obs["leiden"].unique(), key=int):
        genes = [str(g) for g in adata.uns["rank_genes_groups"]["names"][cl][:10]]
        marker_candidates[cl] = genes

    print("[plot] UMAP colored by leiden")
    fig, ax = plt.subplots(figsize=(6, 5))
    sc.pl.umap(adata, color="leiden", ax=ax, show=False, legend_loc="on data", frameon=False)
    fig.tight_layout()
    fig.savefig(outputs / "umap_leiden.png", dpi=120)
    plt.close(fig)

    print("[plot] top marker heatmap")
    sc.pl.rank_genes_groups_heatmap(
        adata, n_genes=5, groupby="leiden", show=False,
        show_gene_labels=True, cmap="viridis",
    )
    plt.savefig(outputs / "marker_heatmap.png", dpi=120, bbox_inches="tight")
    plt.close("all")

    # H7: collect library versions and provenance
    import importlib.metadata as _meta
    def _ver(pkg: str) -> str:
        try:
            return _meta.version(pkg)
        except Exception:
            return "unknown"

    import sys
    metrics = {
        "n_cells": int(adata.n_obs),
        "n_genes_hvg": int(adata.n_vars),
        "n_clusters": int(n_clusters),
        "resolution": args.resolution,
        "marker_candidates": marker_candidates,
        "provenance": {
            "python": sys.version,
            "scanpy": _ver("scanpy"),
            "anndata": _ver("anndata"),
            "numpy": _ver("numpy"),
            "pandas": _ver("pandas"),
            "python_igraph": _ver("igraph"),
            "umap_learn": _ver("umap-learn"),
            "dataset_sha256": dataset_sha256,
            "git_commit": _git_sha(),
        },
        "cli_args": {
            "resolution": args.resolution,
            "n_hvg": args.n_hvg,
            "n_pcs": n_pcs,
            "k_neighbors": args.k_neighbors,
            "seed": args.seed,
            "mt_prefix": args.mt_prefix,
            "zero_center": args.zero_center,
            "max_dense_cells": args.max_dense_cells,
        },
        "deterministic": True,
    }
    # H2: disallow nan/inf in JSON output
    (outputs / "metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False, allow_nan=False)
    )

    # M1: save processed h5ad; .raw.X = log-normalized, .X = scaled HVG
    adata.uns["schema_version"] = (
        "processed: .X=scaled HVG; .raw.X=log-normalized full matrix; "
        "layers['counts'] lost after HVG subset (see pbmc3k_qc_counts.h5ad)"
    )
    adata.write(outputs / "pbmc3k_processed.h5ad")

    print("[done] outputs/ written")
    print(
        f"[done] top marker candidates per cluster: "
        f"{json.dumps({k: v[:3] for k, v in marker_candidates.items()}, ensure_ascii=False)}"
    )


if __name__ == "__main__":
    main()
