# 02 — PINN の考え方

## 通常の教師あり学習との違い

| 通常の NN | PINN |
|---|---|
| 入力 → 出力 のペア (X, y) を大量に集める | ラベル無しでもよい。**物理方程式 (PDE) そのものを損失に組み込む** |
| データ範囲外は未定義 | 方程式が成立する範囲では外挿的な予測が期待できる (ただし限界あり) |
| ネットワークは「関数近似器」 | ネットワークは「PDE の解 $u(x, t)$ の連続表現」 |

## 3 つの損失

1. **PDE 残差損失**
   ネットワーク出力 $u_\theta(x, t)$ を **Autograd で二階微分** し、方程式両辺の差を残差にする:
   $$r(x, t) = \frac{\partial u_\theta}{\partial t} - \alpha \frac{\partial^2 u_\theta}{\partial x^2}$$
   $$L_{\mathrm{pde}} = \frac{1}{N_r} \sum_{i=1}^{N_r} r(x_i, t_i)^2$$

2. **初期条件損失**
   $u(x, 0) = \sin(\pi x)$ を守らせる:
   $$L_{\mathrm{ic}} = \frac{1}{N_i} \sum_i \bigl(u_\theta(x_i, 0) - \sin(\pi x_i)\bigr)^2$$

3. **境界条件損失**
   $u(0, t) = u(1, t) = 0$:
   $$L_{\mathrm{bc}} = \frac{1}{N_b} \sum_i \bigl(u_\theta(0, t_i)^2 + u_\theta(1, t_i)^2\bigr)$$

**総損失**: $L = L_{\mathrm{pde}} + \lambda_{\mathrm{ic}} L_{\mathrm{ic}} + \lambda_{\mathrm{bc}} L_{\mathrm{bc}}$
今回は $\lambda_{\mathrm{ic}} = \lambda_{\mathrm{bc}} = 10$。

## なぜ Autograd?

PyTorch の `torch.autograd.grad` は **合成関数の偏微分を任意階数まで正確に**計算します。
数値差分 (`(f(x+h)-f(x-h))/(2h)`) と違い、丸め誤差やステップ幅選択の問題がありません。

```python
u = model(x, t)
u_x = torch.autograd.grad(u, x, grad_outputs=torch.ones_like(u), create_graph=True)[0]
u_xx = torch.autograd.grad(u_x, x, grad_outputs=torch.ones_like(u_x), create_graph=True)[0]
u_t = torch.autograd.grad(u, t, grad_outputs=torch.ones_like(u), create_graph=True)[0]
```

`create_graph=True` は「勾配の勾配」を後で計算するために必須です (backprop するときに一階微分の計算グラフが必要)。

## Adam → L-BFGS の 2 段階最適化

- **Adam** (1st order): 滑らかで安定、悪い初期値からも降下できる
- **L-BFGS** (準 Newton 法, 2nd order): 収束近くで一気に精度を上げるが、悪い初期値では暴発する

**PINN の定石**: Adam で 2000〜5000 epoch 走らせ、その後 L-BFGS で ~500 iter 磨く。
