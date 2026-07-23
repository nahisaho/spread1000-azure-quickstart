# 03 — ニューラルサロゲートの設計

## モデル: TinyUNet

```
Input (B, 1, 64, 64)  [u(t)]
   │
Encoder 1: Conv3+Conv3 (1→16)      → e1 (B, 16, 64, 64)
   │ MaxPool
Encoder 2: Conv3+Conv3 (16→32)     → e2 (B, 32, 32, 32)
   │ MaxPool
Bottleneck: Conv3+Conv3 (32→64)    →    (B, 64, 16, 16)
   │ ConvTranspose 
Decoder 2: cat[up, e2] Conv3+Conv3 → (B, 32, 32, 32)
   │ ConvTranspose
Decoder 1: cat[up, e1] Conv3+Conv3 → (B, 16, 64, 64)
   │
Output Conv1x1 (16→1) + skip: u + Δu
```

パラメータ数: **~117K** (CPU で数分)

## 残差学習が効く理由

- 直接 $u_{t+k}$ を予測: モデルが input を「再構成」する部分も学習必要 → 難
- 残差 $\Delta u = u_{t+k} - u_t$ を予測: 変化分だけ学習 → **勾配が安定、精度↑**
- 実装: `return x + self.out(d1)` で入力を skip

## k-step 先予測

- k=1: dense 教師データ、精度高いが 1 forward あたりの高速化率は低い
- k=5 (本教材): 5 タイムステップ先 → FD 5 回分を 1 回で置換
- k=20+: 精度落ちる、rollout 用途に不向き

## Autoregressive Rollout

長期予測は繰り返し適用:
```python
u = u0
for _ in range(n_steps):
    u = model(u)  # k-step 先を予測
```

**誤差累積**: 各ステップの誤差が指数的に増える → 気象予測では 3-7 日が実用限界

## 精度指標

**Relative L2 error**:
$$\text{relL2} = \frac{\|u_{\text{pred}} - u_{\text{true}}\|_2}{\|u_{\text{true}}\|_2}$$

- < 0.01 = 論文級
- 0.01-0.05 = 実用可能
- 0.05-0.20 = 動作確認レベル
- > 0.20 = 学習不足

## より高度な手法

| 手法 | 特徴 | 参考 |
|---|---|---|
| **FNO** (Fourier Neural Operator) | Fourier 空間で畳み込み、超高速 | Li et al. 2021, ICLR |
| **DeepONet** | Branch/Trunk net で汎化 | Lu et al. 2021, Nat MI |
| **FourCastNet** | 気象向け ViT ベース ERA5 学習 | Pathak 2022, arXiv |
| **PDE-Refiner** | Diffusion で誤差修正 | Lippe 2023, NeurIPS |
| **PINN** | PDE 損失で無教師学習 | 本 repo の F-1 参照 |
