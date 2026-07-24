# 02 — DDPM 数式

## Forward process (拡散)

元画像 $\mathbf{x}_0$ に段階的に Gaussian ノイズを付加:

$$q(\mathbf{x}_t | \mathbf{x}_{t-1}) = \mathcal{N}(\sqrt{1 - \beta_t}\, \mathbf{x}_{t-1},\; \beta_t \mathbf{I})$$

$\beta_t$ は事前定義した noise schedule。本教材では **cosine schedule** (Nichol & Dhariwal 2021) を使用 (デフォルト, T=200)。cosine schedule では末端 SNR $\bar{\alpha}_T \approx 0$ が保証され、$\mathbf{x}_T \approx \mathcal{N}(0, \mathbf{I})$ が成立する。線形スケジュール (例: 1e-4 → 0.02) では $\bar{\alpha}_{200} \approx 0.13$ となり終端分布が Gaussian に収束しないため、生成品質が低下する (`--schedule linear` で切替可)。

**閉形式**: $\alpha_t = 1 - \beta_t$, $\bar{\alpha}_t = \prod_{s=1}^{t} \alpha_s$ として

$$\mathbf{x}_t = \sqrt{\bar{\alpha}_t}\, \mathbf{x}_0 + \sqrt{1 - \bar{\alpha}_t}\, \boldsymbol{\epsilon}, \quad \boldsymbol{\epsilon} \sim \mathcal{N}(0, \mathbf{I})$$

任意の $t$ に一気にジャンプできる (**学習が高速化**する鍵)。

## 学習損失 (Simplified DDPM)

Ho 2020 は理論上の ELBO を単純化して:

$$L_{\mathrm{simple}} = \mathbb{E}_{t, \mathbf{x}_0, \boldsymbol{\epsilon}} \bigl\lVert \boldsymbol{\epsilon} - \boldsymbol{\epsilon}_\theta(\mathbf{x}_t, t) \bigr\rVert^2$$

NN $\boldsymbol{\epsilon}_\theta$ は **付加されたノイズそのものを予測**する。実装は驚くほど単純:

```python
t = randint(0, T, (B,))
noise = randn_like(x0)
xt = sqrt_alpha_bar[t] * x0 + sqrt_1_minus_alpha_bar[t] * noise
loss = mse(model(xt, t), noise)
```

## Reverse process (生成)

学習が終わったら、$\mathbf{x}_T \sim \mathcal{N}(0, \mathbf{I})$ から出発して 1 ステップずつ denoising。cosine schedule では $\bar{\alpha}_T \approx 0$ なので、この初期分布の仮定が正確に成立する:

$$\mathbf{x}_{t-1} = \frac{1}{\sqrt{\alpha_t}} \Bigl( \mathbf{x}_t - \frac{\beta_t}{\sqrt{1 - \bar{\alpha}_t}} \boldsymbol{\epsilon}_\theta(\mathbf{x}_t, t) \Bigr) + \sqrt{\beta_t}\, \mathbf{z},\quad \mathbf{z} \sim \mathcal{N}(0, \mathbf{I})$$

最後のステップ ($t=0$) では $\mathbf{z} = 0$ とする (deterministic)。

## タイムステップ埋め込み

$t$ を入力にする方法として **sinusoidal encoding** (Transformer と同じ) を使う:

$$\mathrm{PE}(t, 2i) = \sin\bigl(t / 10000^{2i/d}\bigr), \quad \mathrm{PE}(t, 2i+1) = \cos(\cdot)$$

U-Net の各 ResBlock 内で `+ Linear(PE(t))` として feature に加算 (本実装は `src/model.py` 参照)。
