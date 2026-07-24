# トラブルシューティング

## `RuntimeError: shape mismatch` in AE forward

- `Conv1DAE` は seq_len が 8 の倍数であることを前提。
- `sample_len` (npz 内) が 2048 以外の値になっている場合、`--latent-dim` を調整不要だが、Upsample の scale_factor 3 × 2 = 8 が守られる長さを使うこと。

## ROC-AUC がほぼ 0.5 (ランダム)

- **異常データにインパルスが弱すぎる**: `src/generate_data.py` の振幅を `amp = rng.uniform(3.0, 6.0)` に設定されていることを確認 (デフォルト値)
- **AE が underfit**: `--epochs 50 --lr 5e-4` に増やす
- **AE が overfit**: `--latent-dim 16` に落として bottleneck を強くする

## `sklearn.metrics.precision_score` の警告 `Precision is ill-defined`

- 予測が全て陰性 (異常判定なし) の場合。閾値が高すぎる。
- `train.py` を `np.quantile(per_sample, 0.95)` に下げてみる

## Windows で `num_workers > 0` がハング

- 本教材は `num_workers=0` 固定なので該当なし。
- カスタマイズ時は `if __name__ == "__main__":` guard を必ず付ける。
