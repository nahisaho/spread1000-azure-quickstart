# データ

`src/generate_data.py` が **実行時に合成生成** します。事前ダウンロード不要。

出力: `data/vibration.npz`
- `X_train`: (640, 2048) float32 — 正常波形のみ (AE 学習用)
- `X_val`:   (160, 2048) float32 — 正常波形のみ (閾値決定用)
- `X_test`:  (400, 2048) float32 — 正常 200 + 異常 200 (シャッフル済み)
- `y_test`:  (400,) int64 — 0=正常, 1=異常
- `fs`, `sample_len`, `seed`: メタデータ

実データへの応用は [docs/05-real-data.md](../docs/05-real-data.md) 参照 (CWRU Bearing dataset)。
