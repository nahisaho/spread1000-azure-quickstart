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

- 少ないクラスタしか出ない → resolution ↑ (0.5 → 1.0)
- 意味なく細分化される → resolution ↓ (0.5 → 0.3)
- 目安: **既知の細胞種数に近づける**

## 品質確認チェックリスト

- [ ] UMAP に明確なクラスタ分離が見える
- [ ] 各クラスタの top marker が既知細胞種と一致
- [ ] mt% でフィルタしたのに 1 クラスタが低品質細胞に見える → QC 閾値見直し
- [ ] batch effect っぽい分離 (由来サンプル別) → BBKNN / Harmony 検討
