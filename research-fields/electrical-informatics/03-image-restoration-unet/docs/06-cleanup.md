# 06 — 片付けと次のステップ

## ローカルで完結した場合

Azure リソースは一切作成していないので、**追加の料金は発生しません**。

不要になれば以下を削除して構いません:

```bash
rm -rf data/ outputs/ .venv/
```

- `data/train/`, `data/val/`, `data/samples/`: `generate_data.py` の再実行で再生成
- `outputs/`: 学習成果物。別途保存したい場合は先に別ディレクトリへ退避

## Azure ML を使った場合

[docs/05-azure-ml-t4.md](05-azure-ml-t4.md) の compute cluster を放置しても `min-instances=0` なら料金は発生しません。完全削除:

```bash
az ml compute delete --name gpu-t4 --yes
```

## 応用のヒント

### 別の劣化タイプに変える

`src/generate_data.py::add_gaussian_noise` を差し替えるだけで別の劣化タイプに拡張できます:

```python
def add_poisson_gaussian(img, alpha, sigma_read, rng):
    """ショットノイズ (Poisson) + 読み出しノイズ (Gaussian) の混合."""
    lam = np.clip(img, 0, 1) * alpha
    shot = rng.poisson(lam=lam) / alpha
    read = rng.normal(0, sigma_read, size=img.shape)
    return np.clip(shot + read, 0, 1).astype(np.float32)


def add_blur_and_noise(img, sigma_blur, sigma_noise, rng):
    """ボケ + ノイズ (deblurring 課題)."""
    from scipy.ndimage import gaussian_filter
    blurred = gaussian_filter(img[0], sigma=sigma_blur)[None]
    return np.clip(blurred + rng.normal(0, sigma_noise, size=img.shape), 0, 1).astype(np.float32)


def add_downsample(img, factor, rng):
    """低解像度 → 高解像度 (超解像)."""
    from scipy.ndimage import zoom
    low = zoom(img[0], 1/factor, order=1)
    up  = zoom(low, factor, order=1)  # bicubic upsample
    return up[None].astype(np.float32)
```

学習側のコードは全く変える必要がありません。

### 実データに置き換える

`NoisyCleanDataset` は `.npz` の `clean` / `noisy` キーを読むだけです。実データを `(1, H, W) float32 in [0, 1]` に前処理して同じ形式で保存すれば、そのまま学習できます。

**実データ移行時の注意**:

1. **正規化範囲**: 実 RAW は 12〜16 bit 整数。`float32 / (2**bits - 1)` で [0,1] に正規化
2. **サイズ**: MiniUNet は 4 の倍数の入力を要求。必要ならクロップまたはパディング
3. **チャネル数**: 3ch RGB なら `MiniUNet(in_channels=3, out_channels=3)`
4. **noisy/clean ペアが取れない場合**: Noise2Noise (Lehtinen et al. 2018) や Noise2Void (Krull et al. 2019) 系の自己教師あり手法を検討

### 大規模化

- **より深い U-Net**: `base=32` にすると ~470K params (D-3 と同じ trick)
- **注意 (attention U-Net)**: skip connection に attention gate を追加
- **拡散モデル**: DiT/Latent Diffusion で条件生成 (計算量は跳ね上がる)

いずれも本教材の枠を超えるので、まずは baseline PSNR/SSIM を安定して超える MiniUNet で「復元学習の勘所」を掴んでから移行してください。

## 医療・産業応用時に追加で必要なこと

**本モデルは医療機器ではありません**（[docs/07-ethics-and-limits.md](07-ethics-and-limits.md) 参照）。研究として発展させる場合の追加検証:

1. **合成 noisy と実 noisy の分布差** の定量評価
2. **偽構造 (hallucination) 検出** — 復元結果を測定値として使う場合は死活問題
3. **異常入力への挙動** — 学習分布外の入力に対する退化を確認
4. **医療応用の場合**: 日本では SaMD、EU では MDR、米国では FDA の枠組みに従う

## 次のステップ

- [01: Phi-4-mini LoRA ファインチューニング](../01-llm-lora/) — LLM 系
- [02: 時系列信号分類 (1D-CNN)](../02-timeseries-1dcnn/) — 生体信号系
- 他分野: [ルート README](../../../README.md)
