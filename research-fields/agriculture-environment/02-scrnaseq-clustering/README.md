# 02 — scRNA-seq クラスタリング (scanpy)

**分野**: single-cell 転写・エピゲノム解析、生態多様性、植物病理  
**手法**: scanpy による細胞クラスタリング定番ワークフロー  
**データ**: PBMC 3k (10x Genomics 公開データ, CC BY 4.0 — 末梢血単核球 ~2,700 細胞, 自動 DL)  
**出典**: Zheng et al. (2017) Nat Commun DOI [10.1038/ncomms14049](https://doi.org/10.1038/ncomms14049)  
**時間**: ~3 分 (CPU)

## 何が学べるか

- QC (mitochondrial %, gene count) の考え方
- normalize_total + log1p + HVG 選択 + scale + PCA のパイプライン
- k-NN グラフ + UMAP 埋め込み + Leiden クラスタリング
- rank_genes_groups で探索的マーカー候補の同定

## 使い方

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/agriculture-environment/02-scrnaseq-clustering"
cd "$SCENARIO_DIR"
test -f src/analyze.py || { echo "wrong dir — aborting"; exit 1; }
python -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.in
python src/analyze.py --resolution 0.5
```

## 出力

- `outputs/umap_leiden.png` — UMAP 上のクラスタ着色
- `outputs/marker_heatmap.png` — 各クラスタの top 5 探索的マーカー候補
- `outputs/metrics.json` — cluster 数、top marker candidates per cluster、バージョン/引数/SHA-256 プロベナンス
- `outputs/pbmc3k_qc_counts.h5ad` — QC 済み生カウント + QC メタデータ (`.X`=log-normalized, `.layers["counts"]`=raw counts)
- `outputs/pbmc3k_processed.h5ad` — 処理済み AnnData (`.X`=scaled HVG, `.raw.X`=log-normalized)

## 応用

- 農学: 植物 single-cell atlas (Arabidopsis, tomato leaf) 解析
- 環境: 植物・昆虫の single-cell データ解析

> **⚠️ 微生物 ASV への適用について**: 微生物群集 (ASV) データは組成データであり、scRNA-seq のワークフロー (CP10K 正規化, HVG, Euclidean PCA, Leiden) をそのまま適用すると誤った構造を生む可能性があります。ASV データには QIIME2 / phyloseq / CLR 変換 / Aitchison 距離の使用を推奨します。詳細は [docs/05-your-data.md](docs/05-your-data.md) を参照。

## ドキュメント

- [01 前提条件](docs/01-prerequisites.md)
- [02 パイプライン](docs/02-pipeline.md)
- [03 実行](docs/03-run.md)
- [04 結果の解釈](docs/04-understand-results.md)
- [05 自前データ](docs/05-your-data.md)
- [06 片付け](docs/06-cleanup.md)
- [07 倫理と限界](docs/07-ethics-and-limits.md)
- [トラブルシューティング](troubleshooting.md)
