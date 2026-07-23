# トラブルシューティング

## `ConvergenceWarning: The optimal value found for dimension X of parameter Y is close to the specified upper bound`

- Kernel パラメータの境界に張り付いた
- 該当パラメータの `bounds` を広げる (train.py 内の `periodicity_bounds=(1.0, 20.0)` 等)

## 予測が観測点間で発散する

- Kernel の length_scale が小さすぎる → データ点を "覚える" 状態
- `normalize_y=True` を維持し、`length_scale_bounds=(1.0, 50.0)` の下限を上げる

## LML が異常に大きい / 小さい

- Kernel が明らかに不適合 (周期のないデータに ExpSineSquared 等)
- 単純に `RBF + WhiteKernel` から始めて、明らかな残差パターンから kernel を組み合わせる

## メモリ不足 (n が 1000+)

- sklearn GP は $O(n^3)$ の Cholesky を持つ
- サブサンプル、または GPyTorch / celerite2 に移行
