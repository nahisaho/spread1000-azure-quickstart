# 02 — GP の考え方

## Gaussian Process とは

**関数上の確率分布**。任意の有限点集合 $\{t_1, ..., t_n\}$ における値 $(y_1, ..., y_n)$ が多変量正規分布に従う関数族。

$$y \sim \mathcal{GP}(m(t), k(t, t'))$$

- $m(t)$: 平均関数 (通常 0)
- $k(t, t')$: **カーネル (共分散関数)** — 2 点の類似度を決める

## Kernel が全てを決める

| Kernel | 意味 |
|---|---|
| RBF (Gaussian) | 滑らかな関数、長さスケールで柔軟性 |
| Matern | RBF より粗さ許容 |
| ExpSineSquared | 完全周期関数 |
| DotProduct | 線形トレンド |
| WhiteKernel | 観測ノイズ |

Kernel は**加算・乗算で組み合わせ可能**:
```
periodic * amplitude + trend + noise
= ExpSineSquared * ConstantKernel + RBF + WhiteKernel
```

## ハイパラ最適化

$k$ のパラメータ (length_scale, periodicity 等) を **log marginal likelihood 最大化** で求める:

$$\log p(y | X) = -\tfrac{1}{2} y^T K^{-1} y - \tfrac{1}{2} \log |K| - \tfrac{n}{2} \log 2\pi$$

sklearn は `n_restarts_optimizer` 回、異なる初期値で L-BFGS-B を回して最良解を選ぶ。

## 予測

観測 $\{X, y\}$ が与えられたときの $t^*$ での予測:
- **平均**: $\bar{y}^* = k_*^T (K + \sigma^2 I)^{-1} y$
- **分散**: $\sigma^{*2} = k_{**} - k_*^T (K + \sigma^2 I)^{-1} k_*$

$\bar{y}^* \pm 1.96 \sigma^*$ で 95% 信頼区間。

## GP の強みと弱み

**強み**:
- 少ないデータ (数十点) で予測 + 不確実性 が得られる
- ハイパラが少ない (kernel を選べば良い)
- 内挿は極めて正確、外挿でも不確実性が増加して知らせてくれる

**弱み**:
- 計算量 $O(n^3)$: 数千点以上でスケールしない (Sparse GP, Inducing points で対処)
- Kernel 選定が難しい
- 非定常性は苦手
