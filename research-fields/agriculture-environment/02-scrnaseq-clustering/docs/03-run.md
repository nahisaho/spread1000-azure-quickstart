# 03 — 実行

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/agriculture-environment/02-scrnaseq-clustering"
cd "$SCENARIO_DIR"
test -f src/analyze.py || { echo "wrong dir — aborting"; exit 1; }
python src/analyze.py --resolution 0.5
```

## CLI

| フラグ | 既定値 | 説明 |
|---|---|---|
| `--resolution` | 0.5 | Leiden の粗さ (0, 10] |
| `--n-hvg` | 2000 | HVG 遺伝子数 [50, n_vars-1] |
| `--n-pcs` | 50 | PCA 次元数 [2, min(n_obs,n_hvg)-1] |
| `--k-neighbors` | 10 | k-NN グラフの近傍数 [2, n_obs-1] |
| `--seed` | 42 | UMAP/Leiden の乱数 [0, 2^32-1] |
| `--mt-prefix` | `MT-` | ミトコンドリア遺伝子プレフィックス (例: `mt-` for mouse) |
| `--zero-center` / `--no-zero-center` | True | scale 時のゼロセンタリング (大行列は自動スキップ) |
| `--max-dense-cells` | 5e7 | 行列サイズがこれを超えたらゼロセンタリング自動スキップ |

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
[marker] rank_genes_groups (wilcoxon) — exploratory marker candidates
[plot] UMAP colored by leiden
[plot] top marker heatmap
[done] top marker candidates per cluster: {"0": ["LDHB","RPS12","RPS25"], ...}
```

## 出力

- `outputs/umap_leiden.png`
- `outputs/marker_heatmap.png`
- `outputs/metrics.json` — cluster 数、各クラスタ top 10 marker candidates、バージョン/引数/SHA-256 プロベナンス
- `outputs/pbmc3k_qc_counts.h5ad` — QC 済み AnnData (`.X`=log-normalized, `.layers["counts"]`=raw counts)
- `outputs/pbmc3k_processed.h5ad` — 処理済み AnnData (`.X`=scaled HVG, `.raw.X`=log-normalized)
