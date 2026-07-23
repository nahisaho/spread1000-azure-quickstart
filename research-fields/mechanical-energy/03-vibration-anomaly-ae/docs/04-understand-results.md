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

## 期待される結果

```
[eval] threshold=0.003841
[eval] ROC-AUC = 0.9987
[eval] precision=0.995  recall=0.990  F1=0.992
[eval] confusion matrix (rows=true, cols=pred):
        pred_neg  pred_pos
 neg         199         1
 pos           2       198
```

**目安**: ROC-AUC ≥ 0.95, F1 ≥ 0.85 なら合成データセットとして良好。

## score_distribution.png

- 横軸: 再構成 MSE (異常スコア)
- 青ヒスト: 正常テストサンプル (低スコア側にピーク)
- 赤ヒスト: 異常テストサンプル (高スコア側に分布)
- 黒破線: 閾値 (val 99 分位)

**理想**: 2 つの分布がほぼ完全分離。オーバーラップ = 誤検出/未検出。

## pr_curve.png

- Precision-Recall 曲線 (すべての閾値で計算)
- 右上に張り付いていれば AUC-PR も高い
- 不均衡データ (異常が稀) では ROC より PR を重視

## 閾値の再選び方

`train.py` は 99 分位を採用 (誤検出率 1% 目標)。用途によって:
- **保守優先 (誤検出許容, 未検出は困る)** → 95 分位
- **精密優先 (誤検出コスト大)** → 99.5 分位, または precision >= 0.99 の点を PR 曲線から選ぶ
