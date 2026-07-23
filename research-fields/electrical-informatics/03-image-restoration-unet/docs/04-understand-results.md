# 04 — 結果の読み方

## 実行

```bash
python src/evaluate.py --device cpu
```

`outputs/best_model.pt` を val セット (40 サンプル) で再評価し、以下を保存します:

```
outputs/
├── metrics.json         # baseline_noisy / restored / improvement
└── test_samples.png     # 8 サンプル比較画像 (noisy | denoised | clean)
```

## `metrics.json` の見方

```json
{
  "baseline_noisy": {
    "psnr_db": 19.99,
    "ssim": 0.5623
  },
  "restored": {
    "psnr_db": 30.42,
    "ssim": 0.9187
  },
  "improvement": {
    "psnr_db": 10.43,
    "ssim": 0.3564
  },
  "checkpoint_epoch": 15,
  "n_val": 40
}
```

> [!IMPORTANT]
> 上記の数値は **説明用の例** であり実測値ではありません。あなたの環境で実行した結果に置き換えてください。

## PSNR と SSIM の意味

### PSNR (Peak Signal-to-Noise Ratio)

$$
\mathrm{PSNR} = 10 \log_{10} \left( \frac{1^2}{\mathrm{MSE}} \right)
$$

- 単位: dB (デシベル)
- 値が **大きいほど** 良い
- **20 dB**: ノイズがはっきり見える
- **30 dB**: ノイズがほぼ見えないレベル (実用の下限目安)
- **40 dB 以上**: ほぼ完全復元
- **注意**: PSNR は画素値の平均二乗誤差ベースなので、**人間の主観品質と乖離する** ことがある

### SSIM (Structural Similarity Index)

- 値の範囲: 0〜1 (負値もあり得る)
- 値が **大きいほど** 良い
- 輝度・コントラスト・構造の 3 成分を比較
- **人間の主観品質と相関が高い**
- **0.9 以上** で構造的にほぼ一致

## improvement が重要

「モデルが本当に何かを学んだか」を測るのは **absolute な PSNR/SSIM ではなく、baseline との差 (improvement)** です。

- σ=0.10 の Gaussian ノイズなら baseline PSNR は約 20 dB 固定
- 復元後が 30 dB なら **+10 dB の改善** = 良い学習
- 復元後が 22 dB (改善 2 dB) なら実装バグ or 未学習

期待レンジ:

| 指標 | baseline (noisy) | 期待復元後 | 期待改善 |
|---|---:|---:|---:|
| PSNR | 20 dB 前後 | **28〜32 dB** | +8〜12 dB |
| SSIM | 0.5〜0.6 | **0.88〜0.94** | +0.30〜0.40 |

これは σ=0.10 かつ 128×128 幾何プリミティブ画像・117K params U-Net という条件での目安です。

## `test_samples.png` の見方

8 サンプル × 3 列 (noisy | denoised | clean) のグリッドで、モデルが実際にどう振る舞ったかを目視確認します。

**注目すべきポイント**:

1. **エッジの鋭さ** — 鮮鋭に保たれているか、ぼけているか
2. **平坦領域の滑らかさ** — ノイズが除去されているか、残っているか
3. **偽構造 (hallucination)** — clean にない模様が現れていないか（ここ重要）
4. **輝度階調** — 明るさが正しく保たれているか、系統的に暗く/明るくなっていないか

## PSNR/SSIM 曲線 (`loss_curve.png`)

- 青: train L1 loss (下がるべき)
- 橙: val L1 loss (下がるべき、train より上でもよい)
- 緑破線: val PSNR (上がるべき)
- 赤点線: baseline PSNR (noisy 自体) — 緑がこれを **必ず** 上回るべき

学習が進むと train loss は単調に下がり、val loss は途中で下げ止まる (early stopping)。PSNR は val loss と逆に単調に上がる関係です。

## トラブル

| 症状 | 考えられる原因 |
|---|---|
| improvement PSNR < 2 dB | 学習率が高すぎ (`--lr 5e-4`)、epoch 不足、モデル出力が壊れている |
| val PSNR ≈ baseline PSNR | モデルが恒等関数を学習 (input をそのまま返している) — 学習率が低すぎ、または損失計算のバグ |
| test_samples.png が真っ黒/真っ白 | 出力の clamp を忘れている、または model 側で誤って sigmoid をかけている |
| PSNR は高いが目視で不自然 | L2 過適合による over-smoothing、または hallucination — L1 損失または L1+SSIM ハイブリッドを検討 |
