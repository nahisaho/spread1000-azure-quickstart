"""scRNA-seq クラスタリング (scanpy PBMC 3k)

- QC (n_genes, mt%) → normalize_total → log1p → HVG 選択
- scale → PCA 50 → neighbors k=10 → UMAP → Leiden
- rank_genes_groups で各クラスタの marker gene を抽出
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scanpy as sc


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--resolution", type=float, default=0.5, help="Leiden resolution")
    ap.add_argument("--n-hvg", type=int, default=2000)
    ap.add_argument("--n-pcs", type=int, default=50)
    ap.add_argument("--k-neighbors", type=int, default=10)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    np.random.seed(args.seed)
    sc.settings.verbosity = 1
    sc.settings.set_figure_params(dpi=100, facecolor="white")

    outputs = Path(__file__).resolve().parent.parent / "outputs"
    data_dir = Path(__file__).resolve().parent.parent / "data"
    outputs.mkdir(exist_ok=True)
    data_dir.mkdir(exist_ok=True)

    print("[data] loading PBMC 3k (auto-download ~5MB on first run)")
    adata = sc.datasets.pbmc3k()
    print(f"[data] cells={adata.n_obs} genes={adata.n_vars}")

    print("[qc] annotating mitochondrial genes")
    adata.var["mt"] = adata.var_names.str.startswith("MT-")
    sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], inplace=True, log1p=False)

    print("[qc] filtering cells/genes")
    sc.pp.filter_cells(adata, min_genes=200)
    sc.pp.filter_genes(adata, min_cells=3)
    adata = adata[adata.obs["pct_counts_mt"] < 5, :].copy()
    adata = adata[adata.obs["n_genes_by_counts"] < 2500, :].copy()
    print(f"[qc] after: cells={adata.n_obs} genes={adata.n_vars}")

    print("[normalize] total-count normalization + log1p")
    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)

    print(f"[hvg] selecting top {args.n_hvg} highly variable genes")
    sc.pp.highly_variable_genes(adata, n_top_genes=args.n_hvg, flavor="seurat")
    adata.raw = adata
    adata = adata[:, adata.var["highly_variable"]].copy()

    print("[scale] scaling to unit variance (clip=10)")
    sc.pp.scale(adata, max_value=10)

    print(f"[pca] {args.n_pcs} components")
    sc.tl.pca(adata, n_comps=args.n_pcs, random_state=args.seed)

    print(f"[neighbors] k={args.k_neighbors}")
    sc.pp.neighbors(adata, n_neighbors=args.k_neighbors, n_pcs=args.n_pcs, random_state=args.seed)

    print("[umap] embedding")
    sc.tl.umap(adata, random_state=args.seed)

    print(f"[leiden] resolution={args.resolution}")
    sc.tl.leiden(adata, resolution=args.resolution, random_state=args.seed, flavor="igraph", n_iterations=2, directed=False)
    n_clusters = adata.obs["leiden"].nunique()
    print(f"[leiden] found {n_clusters} clusters")

    print("[marker] rank_genes_groups (wilcoxon)")
    sc.tl.rank_genes_groups(adata, "leiden", method="wilcoxon")

    top_markers: dict[str, list[str]] = {}
    for cl in sorted(adata.obs["leiden"].unique(), key=int):
        genes = [str(g) for g in adata.uns["rank_genes_groups"]["names"][cl][:10]]
        top_markers[cl] = genes

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

    metrics = {
        "n_cells": int(adata.n_obs),
        "n_genes_hvg": int(adata.n_vars),
        "n_clusters": int(n_clusters),
        "resolution": args.resolution,
        "top_markers_per_cluster": top_markers,
    }
    (outputs / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False))
    adata.write(outputs / "pbmc3k_processed.h5ad")
    print("[done] outputs/ written")
    print(f"[done] top markers per cluster: {json.dumps({k: v[:3] for k, v in top_markers.items()}, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
