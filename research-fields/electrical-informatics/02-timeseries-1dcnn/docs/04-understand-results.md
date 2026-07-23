# 04 — 結果の読み方

## 実行

```bash
python src/evaluate.py --device cpu
```

`outputs/best_model.pt` と `outputs/normalization.npz` を読み込み、**公式 test 2,947 窓 (未知 9 被験者) で 1 回だけ評価** します。

## 成果物

```
outputs/
├── metrics.json              # サマリ (accuracy, macro-F1, per-class F1)
├── classification_report.json # sklearn 詳細 (precision/recall/F1/support)
└── confusion_matrix.png      # 6×6 混同行列 (数値付きヒートマップ)
```

## `metrics.json` の見方

```json
{
  "test_accuracy": 0.90,
  "macro_f1": 0.89,
  "per_class_f1": {
    "WALKING": 0.94,
    "WALKING_UPSTAIRS": 0.88,
    "WALKING_DOWNSTAIRS": 0.90,
    "SITTING": 0.83,
    "STANDING": 0.82,
    "LAYING": 0.98
  },
  "checkpoint_epoch": 12,
  "checkpoint_val_macro_f1": 0.9052,
  "split": "official_subject_independent_test",
  "n_test_windows": 2947,
  "test_subjects": [2, 4, 9, 10, 12, 13, 18, 20, 24]
}
```

> [!IMPORTANT]
> 上記の数値は **説明用の例** であり、実測値ではありません。あなたの環境で実行した結果に置き換えてください。コンパクト CNN + 15 epoch という条件では **test accuracy 88〜93%、macro-F1 0.87〜0.92** が目安です。

## accuracy と macro-F1 の違い

- **accuracy**: 全 test 窓のうち正解した割合
- **macro-F1**: **クラスごと** に F1 を計算し、単純平均。少数クラスも同じ重みで評価される

UCI HAR はクラス不均衡が軽度（最大/最小 = 約 1.43）ですが、`SITTING` と `STANDING` は静止姿勢で判別が難しいため、この 2 クラスの F1 だけが低くなることがあります。**accuracy だけを見ていると気づかない差** が per-class F1 で可視化されます。

## 混同行列の見方

`confusion_matrix.png` は 6×6 のヒートマップです。

- **行**: 真のクラス
- **列**: 予測したクラス
- **対角成分**: 正解した数（多いほど良い）
- **非対角成分**: 誤分類 (どのクラス同士が混ざりやすいか)

UCI HAR で頻出のパターン:

- `SITTING ↔ STANDING`: 静止姿勢同士は加速度が小さく差が出にくい
- `WALKING_UPSTAIRS ↔ WALKING_DOWNSTAIRS`: 歩行パターンが似ている
- `LAYING`: ジャイロ・加速度が独特で最も分類しやすい (F1 が高い)

## 期待レンジと解釈

| 指標 | 期待範囲 (コンパクト CNN) | 判定 |
|---|---:|---|
| test accuracy | 88〜93% | 妥当 |
| macro-F1 | 0.87〜0.92 | 妥当 |
| val macro-F1 との差 | ±0.03 | 良好な汎化 |
| val macro-F1 との差 | > 0.10 | 過学習 or 被験者リーク疑い |
| test accuracy | > 95% | 実装バグ疑い (被験者リーク、標準化ミス、test 混入) |

**95% を超える結果が出た場合は疑ってください**。UCI HAR で被験者独立 test が 95% を超える報告は、非常に大きなモデル + 十分な調整が必要です。この教材のようなコンパクト CNN で簡単に達成できる数値ではありません。

## より深く見る

`classification_report.json` は `sklearn.metrics.classification_report` の生出力です:

```json
{
  "WALKING": {
    "precision": 0.93,
    "recall": 0.95,
    "f1-score": 0.94,
    "support": 496
  },
  ...
  "macro avg": {"precision": 0.89, "recall": 0.89, "f1-score": 0.89, "support": 2947},
  "weighted avg": {"precision": 0.90, "recall": 0.90, "f1-score": 0.90, "support": 2947}
}
```

**precision**: そのクラスと予測したもののうち正解の割合（False Positive を減らしたい時に重視）
**recall**: そのクラスの真値のうち正解した割合（False Negative を減らしたい時に重視）
**support**: そのクラスの真値の個数

医療応用であれば、見逃したくないクラス (例: 転倒) の recall を優先することが一般的です。本教材はあくまで技術デモですが、応用時には **業務要件から重視すべき指標を決める** ことが最重要です。
