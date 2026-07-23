# 03 — 実行

```bash
python src/analyze.py --resolution 0.5
```

## CLI

| フラグ | 既定値 | 説明 |
|---|---|---|
| `--resolution` | 0.5 | Leiden の粗さ (0.3 少数統合 / 1.0 細分化) |
| `--n-hvg` | 2000 | HVG 遺伝子数 |
| `--n-pcs` | 50 | PCA 次元数 |
| `--k-neighbors` | 10 | k-NN グラフの近傍数 |
| `--seed` | 42 | UMAP/Leiden の乱数 |

## 期待進行 (~3 分 CPU)

```
[data] loading PBMC 3k (auto-download ~5MB on first run)
[data] cells=2700 genes=32738
[qc] after: cells=2638 genes=13714
[normalize] total-count normalization + log1p
[hvg] selecting top 2000 highly variable genes
[pca] 50 components
[neighbors] k=10
[umap] embedding
[leiden] resolution=0.5
[leiden] found 6 clusters
[marker] rank_genes_groups (wilcoxon)
[plot] UMAP colored by leiden
[plot] top marker heatmap
[done] top markers per cluster: {"0": ["LDHB","RPS12","RPS25"], ...}
```

## 出力

- `outputs/umap_leiden.png`
- `outputs/marker_heatmap.png`
- `outputs/metrics.json` — cluster 数、各クラスタ top 10 markers
- `outputs/pbmc3k_processed.h5ad` — 処理済み AnnData (次段解析用)
