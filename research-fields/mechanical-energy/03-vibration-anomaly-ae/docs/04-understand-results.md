# 04 — 結果の読み方

## 実行

```bash
python src/evaluate.py --data data/vibration.npz --model outputs/best_ae.pt
```

## 評価指標

- **ROC-AUC**: 閾値非依存の識別能力 (0.5=ランダム, 1.0=完全)
- **precision**: 異常と判定した中で本当に異常だった割合
- **recall**: 実際の異常のうち検出できた割合
- **F1**: precision と recall の調和平均

## 期待される結果 (seed=42, epochs=30)

```
[eval] threshold=0.318548
[eval] ROC-AUC = 0.9986
[eval] precision=0.990  recall=0.975  F1=0.982
[eval] confusion matrix (rows=true, cols=pred):
        pred_neg  pred_pos
 neg         198         2
 pos           5       195
```

**目安**: ROC-AUC ≥ 0.95, F1 ≥ 0.85 なら合成データセットとして良好
(自動検証: `python -m pytest tests/test_regression.py -v`)。

## score_distribution.png

- 横軸: 再構成 MSE (異常スコア)
- 青ヒスト: 正常テストサンプル (低スコア側にピーク)
- 赤ヒスト: 異常テストサンプル (高スコア側に分布)
- 黒破線: 閾値 (キャリブレーションセットの 99 分位)

**理想**: 2 つの分布がほぼ完全分離。オーバーラップ = 誤検出/未検出。

## pr_curve.png

- Precision-Recall 曲線 (すべての閾値で計算)
- 右上に張り付いていれば AUC-PR も高い
- 不均衡データ (異常が稀) では ROC より PR を重視

## confusion_matrix.png

- 縦軸: 真のラベル (normal / anomaly)
- 横軸: 予測ラベル (normal / anomaly)
- 右上 (FP): 正常を異常と誤判定 → 不要な保全作業
- 左下 (FN): 異常を見逃す → **安全上最もコストが高い**

## threshold_vs_metrics.png

- 横軸: 閾値 (再構成 MSE)
- 縦軸: F1 / precision / recall
- 黒破線: 現在選択済みの閾値 (キャリブレーションセットの 99 分位)

## 閾値の再選び方

> [!IMPORTANT]
> **しきい値はキャリブレーションセット (`data/vibration.npz` 内の `X_cal`) で
> 1 回だけ選び、テストセットは最終評価に 1 回だけ使用すること。**
> テスト PR 曲線から閾値を選ぶとテストセット汚染が生じる。

`train.py` は `X_cal` の 99 分位を採用 (誤検出率 1% 目標)。用途によって:
- **保守優先 (誤検出許容, 未検出は困る)** → 95 分位 → recall 向上
- **精密優先 (誤検出コスト大)** → 99.5 分位

再キャリブレーションは `train.py` を `--latent-dim` や分位数を変えて再実行し、
`evaluate.py` でテストセット評価を **1 回だけ** 行う。
