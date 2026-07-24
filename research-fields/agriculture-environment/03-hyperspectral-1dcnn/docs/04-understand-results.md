# 04 — 結果の解釈

> ⚠ **合成データの精度はベンチマークではありません。** 6-class toy データは実際の
> Indian Pines と異なる (センサー応答・大気補正・water-absorption bands 欠損なし)。
> 実際の性能指標には実 Indian Pines / Salinas / Pavia 等の実データを使用すること。

## metrics.json の主要フィールド

| フィールド | 説明 |
|---|---|
| `overall_accuracy` | 全ピクセル正解率 |
| `macro_f1` | クラス平均 F1 (不均衡データでは overall_accuracy より重要) |
| `balanced_accuracy` | 各クラス recall の平均 |
| `cohen_kappa` | ランダム一致を除いた合意度 (1=完全一致, 0=ランダム) |
| `per_class_f1_sorted` | F1 低→高でソート済み: 困難クラスを特定するのに使う |
| `note` | 合成データの場合に警告文 |

## split_strategy の重要性 (BLOCKING 2)

| strategy | 空間リーク | 実データ推奨 |
|---|---|---|
| `random_pixel` | あり → 精度過大評価 | ✗ |
| `disjoint_patch` | なし (パッチ単位) | ✓ |
| `disjoint_class_stratified` | なし | ✓ |

## per_class_f1_sorted — 困難クラスの特定

```
Oats                              0.214   ← サンプル数 20、最低
Alfalfa                           0.467   ← サンプル数 46
...
Hay-windrowed                     0.980   ← サンプル数 478
```

- **F1 が極端に低いクラス** = データ不足 or スペクトル重複
- `--balance weighted_ce` または `focal` で改善を試みる

## confusion_matrix.csv の利用

```python
import pandas as pd
cm = pd.read_csv("outputs/confusion_matrix.csv", index_col=0)
# 最も混同されているペアを確認
off_diag = cm.copy(); off_diag.values[[range(len(cm))]*2] = 0
print(off_diag.stack().nlargest(5))
```

## prediction_map.png (実データのみ)

- 左: 予測マップ (全ピクセルを推論して 2D に投影)
- 右: 正解ラベル
- 色パレット: tab20 (最大 20 クラス)

## loss_acc.png の見方

- val_loss > train_loss は正常
- 両者の差が急拡大 → 過学習 (エポック減 or data augmentation)
- val_acc/mF1 の頭打ちが早い → モデル容量不足 (チャネル数増やす)
- val_macro_f1 が val_acc より低い → クラス不均衡 (`--balance` を確認)

## 参考精度

| データ | split | acc | macro_F1 |
|---|---|---|---|
| 合成 6-class (toy) | random_pixel | ≥ 0.95 | ≥ 0.95 |
| Indian Pines (16 class) | random_pixel | ~0.85–0.90 ⚠ 過大 | — |
| Indian Pines (16 class) | disjoint_patch | ~0.75–0.85 | — |
