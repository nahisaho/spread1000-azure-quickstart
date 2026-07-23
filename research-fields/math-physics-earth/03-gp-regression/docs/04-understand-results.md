# 04 — 結果の解釈

## gp_fit.png の見方

- **黒線**: 真の関数 (通常は未知)
- **青線**: GP 予測平均
- **青帯**: 95% 信頼区間
- **赤点**: 観測データ (エラーバー付き)
- **灰色破線**: 外挿境界 (t = t_max)

**期待される特徴**:
- 観測点近傍で信頼区間が狭い (青帯が細い)
- 観測から離れると信頼区間が広がる
- 外挿領域 (t > 20) では帯が急速に広がる

## residuals.png

- 残差 (観測値 - GP 予測平均) が 0 の周りにランダムに散らばる → 良好
- 系統的なパターン (トレンド、うねり) → kernel 選定を見直す

## metrics.json

```json
{
  "rmse_interp": 0.0919,
  "rmse_extrap": 0.0729,
  "log_marginal_likelihood": 6.61,
  "optimized_kernel": "2.62**2 * ExpSineSquared(length_scale=4.22, periodicity=5.02) + ..."
}
```

## log-marginal-likelihood の解釈

- **モデル比較の指標**: 高いほど良い
- 別 kernel (例: RBF のみ) を試して比較する
  ```python
  # kernel を RBF + WhiteKernel だけに変えて run し、LML が下がることを確認
  ```
- 過学習の警告: LML が高くても外挿 RMSE が悪い場合、kernel が過剰にデータを覚えている

## 95% 信頼区間の意味

「予測点 t\* に対する y の真値が、この帯に 95% の確率で入る」 (kernel が正しいことを仮定して)。
**この仮定が崩れると信頼区間は意味を失う**ため、kernel 選定と残差診断は必須。
