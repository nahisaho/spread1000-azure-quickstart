# 04 — 結果の解釈

## PBMC 3k で期待される cell types

PBMC (末梢血単核球) は well-characterized なので、marker gene から細胞種を推定できます:

| Cluster マーカー例 | 推定細胞種 |
|---|---|
| `LDHB`, `RPS12`, `CCR7` | Naive T cells / CD4+ T |
| `NKG7`, `GZMA`, `GNLY` | NK cells / CD8+ effector |
| `CD79A`, `CD74`, `MS4A1` | B cells |
| `TYROBP`, `LYZ`, `FTL` | CD14+ monocytes |
| `FCER1A`, `HLA-DPA1` | Dendritic cells |
| `SDPR`, `GNG11`, `HIST1H2AC` | Platelets / Megakaryocytes |

## resolution の調整

> **⚠️ 注意**: 「既知の細胞種数に近づける」ことを resolution 選択の基準にしないでください。これは circular reasoning (クラスタ数をあらかじめ知っていることを前提とする) であり、実データでは通用しません。

適切な resolution の選択には **ロバスト性と安定性** を基準とします:

1. **Resolution スイープ**: `{0.3, 0.5, 0.8, 1.0, 1.5}` を試し、クラスタ数の変化を記録する
2. **Seed 安定性**: 複数の random seed で繰り返し、ARI (Adjusted Rand Index) / AMI (Adjusted Mutual Information) でクラスタ安定性を評価する
3. **グラフ安定性**: silhouette score や modularity でクラスタの内部凝集度を確認する
4. **マーカー一貫性**: 各クラスタに既知リニエージマーカー (系譜マーカー) が集中しているか確認する

## ラベルは暫定的

- クラスタラベルは **探索的・暫定的** であり、生物学的確証ではありません
- UMAP の幾何学的配置はトポロジのみ反映し、「距離」は根拠になりません
- 確証的 cell type annotation には参照マッピング (celltypist, Azimuth) またはドメインエキスパートによる検証が必要です

## 品質確認チェックリスト

- [ ] 複数 resolution / seed でクラスタ構成が安定している
- [ ] 各クラスタの top marker candidate が既知系譜マーカーと一致する
- [ ] UMAP に明確なクラスタ分離が見える (参考情報; 確証ではない)
- [ ] mt% でフィルタしたのに 1 クラスタが低品質細胞に見える → QC 閾値見直し
- [ ] batch effect っぽい分離 (由来サンプル別) → BBKNN / Harmony 検討
- [ ] 参照データセットとのマッピング (celltypist 等) で label を独立検証した
