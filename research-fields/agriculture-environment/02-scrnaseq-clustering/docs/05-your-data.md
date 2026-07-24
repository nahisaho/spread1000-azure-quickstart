# 05 — 自前データへの適用

## 対応フォーマット

scanpy は主要な single-cell フォーマットをすべて読み込み可能:

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/agriculture-environment/02-scrnaseq-clustering"
cd "$SCENARIO_DIR"
test -f src/analyze.py || { echo "wrong dir — aborting"; exit 1; }
```

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

## データローダーを差し替えるときの必須検証

`sc.datasets.pbmc3k()` を差し替える際は、以下を **必ず** 確認してください。コード例:

```python
import numpy as np
import scipy.sparse as sp

# 1. 向き確認: cells × genes (行 = 細胞, 列 = 遺伝子)
assert adata.n_obs > adata.n_vars or input("行=細胞, 列=遺伝子 か確認 (Enter で続行):")

# 2. 重複名の排除
adata.obs_names_make_unique()
adata.var_names_make_unique()

# 3. CSR 疎行列に変換 (カウント行列向け)
if not sp.issparse(adata.X):
    adata.X = sp.csr_matrix(adata.X)

# 4. 有限・非負・整数近似カウントを検証
data = adata.X.data if sp.issparse(adata.X) else adata.X.ravel()
assert np.isfinite(data).all(), "NaN/Inf を含む値が存在します"
assert (data >= 0).all(), "負のカウントが存在します"
# カウントが近似整数かチェック (0.01 未満の小数部分)
non_int_frac = np.mean(np.abs(data - np.round(data)) > 0.01)
if non_int_frac > 0.01:
    import warnings
    warnings.warn(f"非整数値が {non_int_frac:.1%} 存在します。正規化済みデータを渡していないか確認してください。")

# 5. 最小品質フィルタ
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.filter_genes(adata, min_cells=3)
assert adata.n_obs >= 50, "細胞数が少なすぎます (最低 50 細胞)"
assert adata.n_vars >= 500, "遺伝子数が少なすぎます (最低 500 遺伝子)"
```

## 種ごとのミトコンドリア遺伝子プレフィックス

`--mt-prefix` オプションで種に合わせて変更してください:

| 種 | プレフィックス | 備考 |
|---|---|---|
| ヒト | `MT-` (デフォルト) | Human mitochondria |
| マウス | `mt-` | Mouse mitochondria |
| 植物 (Arabidopsis 等) | `ATMG` / `ATCG` | Mitochondria + Chloroplast を両方 QC |
| 昆虫 | `mt:` (Drosophila) | 種依存で確認 |

```bash
python src/analyze.py --mt-prefix mt-   # マウスの場合
```

## ダブレット (Doublet) 検出の推奨

真の解析では、クラスタリング前にダブレット除去ツールの使用を推奨します:

- **Scrublet**: `scrublet` パッケージ — Python ネイティブ、scanpy と統合容易
- **DoubletFinder**: R パッケージだが h5ad 出力 → scRNA-seq ベスト プラクティスに沿う
- **scDblFinder** (R/Bioconductor): 高精度

## 農学・環境分野での応用例

| ドメイン | データ | 補足 |
|---|---|---|
| 植物 single-cell | Arabidopsis leaf/root atlas (GEO GSE121619 等) | mt% ではなく chloroplast (`ATCG`) + mitochondria (`ATMG`) 両方を除外 |
| 昆虫単細胞 | Drosophila brain atlas (Fly Cell Atlas) | Leiden resolution 大きめ (多様な neuron subtype) |

## Batch effect 対策

複数サンプル/複数実験を統合する場合は以下の手順で:

### HVG 選択 (batch-aware)

```python
sc.pp.highly_variable_genes(adata, n_top_genes=2000, flavor="seurat", batch_key="batch")
```

### BBKNN

BBKNN は `sc.pp.neighbors` の **代替** として適用します。その後 UMAP/Leiden は通常通り:

```python
pip install bbknn  # 事前インストール

sc.external.pp.bbknn(adata, batch_key="batch")
# sc.pp.neighbors は呼ばない (BBKNN が neighbors グラフを構築する)
sc.tl.umap(adata, random_state=42)
sc.tl.leiden(adata, resolution=0.5, flavor="igraph", n_iterations=2, directed=False)
```

### Harmony

Harmony は PCA 後の埋め込みを補正します。補正後は **必ず** `use_rep="X_pca_harmony"` を指定してください:

```python
pip install harmonypy  # 事前インストール

sc.external.pp.harmony_integrate(adata, key="batch")
# neighbors を補正済み埋め込みから再構築
sc.pp.neighbors(adata, use_rep="X_pca_harmony", n_neighbors=10, random_state=42)
sc.tl.umap(adata, random_state=42)
sc.tl.leiden(adata, resolution=0.5, flavor="igraph", n_iterations=2, directed=False)
```

### 過補正チェック

補正後も既知マーカー遺伝子 (例: CD3D, CD79A, LYZ) がバッチ間で同様に発現しているか確認してください:

```python
sc.pl.umap(adata, color=["batch", "CD3D", "CD79A", "LYZ"])
```

## 微生物メタゲノム ASV データへの適用について

> **⚠️ 重要な注意**: 微生物群集 (ASV) データは **組成データ (compositional data)** であり、scRNA-seq のワークフロー (CP10K 正規化, HVG, Euclidean PCA, Leiden) をそのまま適用すると **誤った構造** を生む可能性があります。
>
> ASV データには以下の専用解析ツールを推奨します:
> - **QIIME2** — 微生物群集解析のスタンダード
> - **phyloseq** (R) — 系統情報つき群集解析
> - **CLR 変換 (compositional log-ratio)** — 組成データのバイアスを除去
> - **Aitchison 距離** — 組成空間での適切な距離指標
>
> scanpy の UMAP + Leiden を ASV に適用する場合は、必ず CLR 変換後に実施し、その限界を明示してください。

## 追加解析

- **Trajectory (擬似時間)**: `sc.tl.paga` + `sc.tl.dpt`
- **Cell-cell communication**: `CellPhoneDB`, `CellChat`
- **Cell type annotation 自動化**: `celltypist`, `scANVI`, `Azimuth`
