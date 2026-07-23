# 02 — scRNA-seq クラスタリング (scanpy)

**分野**: single-cell 転写・エピゲノム解析、生態多様性、植物病理  
**手法**: scanpy による細胞クラスタリング定番ワークフロー  
**データ**: PBMC 3k (10x Genomics 公開データ、末梢血単核球 ~2,700 細胞、自動 DL)  
**時間**: ~3 分 (CPU)

## 何が学べるか

- QC (mitochondrial %, gene count) の考え方
- normalize_total + log1p + HVG 選択 + scale + PCA のパイプライン
- k-NN グラフ + UMAP 埋め込み + Leiden クラスタリング
- rank_genes_groups で marker gene 同定

## 使い方

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt
python src/analyze.py --resolution 0.5
```

## 出力

- `outputs/umap_leiden.png` — UMAP 上のクラスタ着色
- `outputs/marker_heatmap.png` — 各クラスタの top 5 marker gene
- `outputs/metrics.json` — cluster 数、top markers per cluster
- `outputs/pbmc3k_processed.h5ad` — 処理済み AnnData

## 応用

- 農学: 植物 single-cell atlas (Arabidopsis, tomato leaf) 解析
- 環境: メタゲノムの ASV クラスタリング (scanpy パイプラインの一部を再利用)
- 生態: マイクロバイオーム多様性の細胞群クラスタリング

## ドキュメント

- [01 前提条件](docs/01-prerequisites.md)
- [02 パイプライン](docs/02-pipeline.md)
- [03 実行](docs/03-run.md)
- [04 結果の解釈](docs/04-understand-results.md)
- [05 自前データ](docs/05-your-data.md)
- [06 片付け](docs/06-cleanup.md)
- [07 倫理と限界](docs/07-ethics-and-limits.md)
- [トラブルシューティング](troubleshooting.md)
