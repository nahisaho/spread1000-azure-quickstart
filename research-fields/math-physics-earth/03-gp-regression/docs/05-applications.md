# 05 — 応用

## 天体観測

### 系外惑星ライトカーブ (トランジット + 恒星活動)

- 主星の周期的な明るさ変動を GP でモデル化 → トランジット信号のみ残せる
- `celerite2` (Foreman-Mackey ら) が高速な 1D GP 実装で系外惑星コミュニティで標準

### 変光星の周期検出

- 不等間隔観測から周期を推定 → GP の ExpSineSquared kernel の `periodicity` 推定値

## 地球観測 / 気象

- 気温・降水量の時空間補間 (Kriging = GP の別名)
- 地質サンプルからの鉱物分布推定
- CO₂ 濃度の長期予測 (Rasmussen & Williams の教科書例、Mauna Loa データ)

## 実験計画法 / ベイズ最適化

- ブラックボックス関数 (実験・シミュレーション) の最適化
- GP で目的関数を回帰 → Expected Improvement で次の観測点を選ぶ
- ライブラリ: `scikit-optimize`, `botorch`

## スケール問題対策

`sklearn` の `GaussianProcessRegressor` は $n$ 数千で遅くなる。大規模データは:
- **GPy** / **GPyTorch**: Inducing point (sparse GP)、GPU 対応
- **celerite2**: 1D 時系列に特化した O(n) アルゴリズム

## 多出力 GP

複数の相関ある信号を同時にモデル化: Multi-task GP (GPyTorch にサンプル多数)
