# 02 — パイプライン

## scanpy 標準ワークフロー

```
raw count matrix (cells × genes, sparse)
   │
   │ ① QC: mitochondrial %, n_genes/cell
   ▼
   │ ② normalize_total (target_sum=1e4) + log1p
   ▼
   │ ③ HVG 選択 (top 2000 variable genes)
   ▼
   │ ④ scale (zero-mean, unit var, clip=10)
   ▼
   │ ⑤ PCA (50 comp)
   ▼
   │ ⑥ neighbors (k=10 in PC space)
   ▼
   │ ⑦ UMAP (2D 可視化)
   │ ⑧ Leiden (グラフクラスタリング)
   ▼
   │ ⑨ rank_genes_groups (Wilcoxon, marker 抽出)
```

## 各ステップの意義

| Step | 目的 | 注意点 |
|---|---|---|
| ① QC | 死細胞 (高 mt%)、doublet (異常に多い遺伝子数) を除外 | mt% 5% は経験則、組織ごとに調整 |
| ② normalize | 細胞ごとの total count 差 (シーケンス深度) を補正 | log1p は分散を安定化しダイナミックレンジを圧縮する (Gaussian 化ではない) |
| ③ HVG | 3 万遺伝子 → 2 千に圧縮、生物学的シグナルを保持 | flavor='seurat_v3' は count 必要 |
| ④ scale | PCA 前の遺伝子スケール正規化 | 発現の高い遺伝子だけに引きずられないため |
| ⑤ PCA | 次元削減 (2000 → 50)、ノイズ低減 | n_comps は 30-50 が一般的 |
| ⑥ neighbors | 各細胞の PC 空間近傍を計算 | k は 10-30、大きいほど滑らか |
| ⑦ UMAP | 2D 可視化 | 距離の絶対値は意味を持たない (トポロジのみ) |
| ⑧ Leiden | resolution 大 → 細分化、小 → 統合 | 0.3-1.0 を試して biology と照合 |
| ⑨ marker | クラスタごとに他クラスタに対して発現差の大きい遺伝子 (探索的候補マーカー) | Wilcoxon は分布仮定不要だが観測の独立性を要求する (同一ドナー由来のセルは独立ではない); クラスタ由来データで検定するため p-value は anti-conservative — 推論目的には独立ドナーの pseudobulk + カウントモデル DE (DESeq2, edgeR, muscat) を使うこと |

> **⚠️ 探索的マーカー候補 (marker candidates) について**: `rank_genes_groups` の p-value は、クラスタが同一データから導出されている (double-dipping) ため anti-conservative です。単一ドナー由来のセルは独立した観測値ではありません。これらは **探索的マーカー候補** であり、確証的推論には使用しないでください。DE 推論には独立ドナーの pseudobulk + カウントモデル (DESeq2, edgeR, muscat) を使用してください。

## 参考文献

- Wolf, Angerer, Theis (2018). *"SCANPY: large-scale single-cell gene expression data analysis"*, Genome Biology
- Traag, Waltman, van Eck (2019). *"From Louvain to Leiden: guaranteeing well-connected communities"*, Scientific Reports
