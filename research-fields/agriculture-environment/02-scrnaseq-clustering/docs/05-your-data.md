# 05 — 自前データへの適用

## 対応フォーマット

scanpy は主要な single-cell フォーマットをすべて読み込み可能:

```python
import scanpy as sc

# 10x Genomics Cell Ranger output
adata = sc.read_10x_mtx("path/to/filtered_feature_bc_matrix/")
# 10x .h5
adata = sc.read_10x_h5("path/to/filtered_feature_bc_matrix.h5")
# AnnData .h5ad
adata = sc.read_h5ad("path/to/file.h5ad")
# CSV / TSV
adata = sc.read_csv("path/to/counts.csv")
```

`src/analyze.py` の `sc.datasets.pbmc3k()` を差し替えるだけで完了。

## 農学・環境分野での応用例

| ドメイン | データ | 補足 |
|---|---|---|
| 植物 single-cell | Arabidopsis leaf/root atlas (GEO GSE121619 等) | mt% ではなく chloroplast/mitochondria 両方を除外 |
| 昆虫単細胞 | Drosophila brain atlas (Fly Cell Atlas) | Leiden resolution 大きめ (多様な neuron subtype) |
| 微生物メタゲノム ASV | QIIME2 出力の ASV × sample count matrix | scanpy の一部 (UMAP + Leiden) を再利用可能 |

## batch effect 対策

複数サンプル/複数実験を統合する場合:

```python
sc.external.pp.bbknn(adata, batch_key="sample")  # Berkeley BBKNN
# または
sc.external.pp.harmony_integrate(adata, key="sample")  # Harmony
```

## 追加解析

- **Trajectory (擬似時間)**: `sc.tl.paga` + `sc.tl.dpt`
- **Cell-cell communication**: `CellPhoneDB`, `CellChat`
- **Cell type annotation 自動化**: `celltypist`, `scANVI`
