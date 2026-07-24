# 04 — 結果の解釈

## gp_fit.png の見方

- **黒線**: 真の関数 (通常は未知)
- **青線**: GP 予測平均
- **青帯 (薄)**: model-conditional (plug-in MLE) **95% 予測区間 — 新しいノイズ観測値**  
  `return_std=True` が返す標準偏差には WhiteKernel の観測ノイズ分散が含まれる。  
  これは「次の新しい観測値が入る区間」を示す。
- **シアン帯 (濃)**: **95% 予測区間 — 潜在関数 f** (WhiteKernel を除いた signal-only GP)  
  潜在関数の事後不確実性を示す。観測バンドよりも狭い。
- **赤点**: 観測データ (エラーバー付き)
- **灰色破線**: 外挿境界 (t = t_max)

> **2 つの区間の使い分け**:  
> - 潜在バンド: 「真の関数がどこにあるか」の不確実性 → kernel ミス・スペシフィケーション診断に有用  
> - 観測バンド: 「次の観測値がどこに落ちるか」の予測 → 新規データとの比較に使う

**期待される特徴**:
- 観測点近傍で信頼区間が狭い
- 観測から離れると信頼区間が広がる (ただし ExpSineSquared カーネルでは **単調増加しない**)
- 外挿領域 (t > t_max) では、周期カーネルのため帯が急速に広がるとは限らない (HIGH-2)

## residuals.png

### 左: in-sample 残差 (参考のみ)

- GP は観測点を **補間** するため in-sample 残差は楽観的
- **ミスペシフィケーション診断には使わないこと** (MED-7)

### 右: Temporal holdout 残差 (最後の 20% をテスト)

- 時系列順で後ろ 20% を学習から除外し、最適化済みカーネルで予測
- 残差が 0 周りにランダム散布 → 良好
- 系統的なパターン → kernel 選定または前処理を見直す
- **カバレッジ 0.95 付近** が期待値; 大きく外れる場合は kernel か `--noise` を確認

## metrics.json

```json
{
  "holdout_rmse": 0.114,
  "holdout_log_predictive_density": -0.32,
  "holdout_95pct_coverage": 0.83,
  "log_marginal_likelihood": 6.61,
  "condition_number": 1230.0,
  "optimized_period": 5.0241
}
```

## log-marginal-likelihood の解釈 (LOW-11)

- **モデル比較の指標**: 高いほど良い
- **相対比較のみ有効** — 同一データ・同一前処理条件下でのみ異なる kernel と比較可能
- 別 kernel (例: RBF のみ) を試して LML を比較し、**独立した holdout 予測性能と併用**して判断する
  ```bash
  # kernel を変えて run し、LML と holdout RMSE の両方を比較する
  # LML 単独では過学習の警告にならない — holdout 指標と必ずセットで
  ```
- 過学習の警告: LML が高くても holdout RMSE が悪い場合、kernel が過剰にデータを覚えている
