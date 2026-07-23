# トラブルシューティング

## `ModuleNotFoundError: No module named 'leidenalg'`

`pip install leidenalg igraph` — Leiden クラスタリング必須依存。

## `sc.datasets.pbmc3k()` がタイムアウト

- scanpy が 10x のサーバからダウンロード。ネットワーク不安定なら手動 DL:
  - https://cf.10xgenomics.com/samples/cell-exp/1.1.0/pbmc3k/pbmc3k_filtered_gene_bc_matrices.tar.gz
  - 展開して `sc.read_10x_mtx("filtered_gene_bc_matrices/hg19/")` で読み込み

## Leiden クラスタが 1 個しかできない

- resolution を上げる (`--resolution 1.0`)
- neighbors の k を減らす (`--k-neighbors 5`)
- QC で細胞を絞りすぎていないか確認

## メモリ不足 (数万細胞以上)

- `sc.pp.subsample(adata, n_obs=5000)` で先にダウンサンプル
- 疎行列を維持: `adata.X = scipy.sparse.csr_matrix(adata.X)` を早期に

## marker heatmap がうまく描画されない

- `matplotlib.use("Agg")` を確実に import 前に設定 (X server なし環境)
- outputs/ ディレクトリが存在するか確認
