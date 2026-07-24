# 05 — 発展編

## 別の PDE を試す

`src/train.py` の PDE 残差計算を書き換えるだけで他の方程式に応用できます。

### バーガース方程式 (非線形移流拡散)

$$u_t + u u_x = \nu u_{xx}$$

```python
def compute_pde_residual(model, x, t, nu):
    x = x.clone().requires_grad_(True); t = t.clone().requires_grad_(True)
    u = model(x, t)
    u_x  = grad(u,  x, torch.ones_like(u),  create_graph=True)[0]
    u_t  = grad(u,  t, torch.ones_like(u),  create_graph=True)[0]
    u_xx = grad(u_x, x, torch.ones_like(u_x), create_graph=True)[0]
    return u_t + u * u_x - nu * u_xx
```

### 波動方程式

$$u_{tt} = c^2 u_{xx}$$

`u_tt` は `u_t` にさらに一階微分をかけて計算。

## 逆問題: 未知パラメータの推定

「観測データから熱拡散係数 α を推定する」

```python
import torch.nn.functional as F
raw_alpha = nn.Parameter(torch.log(torch.expm1(torch.tensor(0.1))))
def positive_alpha() -> torch.Tensor:
    return F.softplus(raw_alpha) + 1e-8
optimizer = torch.optim.Adam(list(model.parameters()) + [raw_alpha], lr=1e-3)
```

`raw_alpha` を softplus で変換することで α が必ず正になり、逆向き熱方程式 (α < 0)
への偶発的な発散を防ぎます。

## 実データフィッティング

実験データ (センサ計測など) を `(x_i, t_i, u_i)` の CSV で読み込み、
「観測損失 + PDE 残差」の重み付き和を最小化すれば、**ノイズ付きデータを物理制約でスムージング**できます。

## より難しい問題

- 高周波成分 (short wavelength) は PINN が苦手 → Fourier feature encoding を初段に入れる
- 領域が複雑 → 点のサンプリングを工夫 (adaptive resampling)
- 収束が遅い → NTK 正則化、SA-PINN 等の改良

参考: Wang et al., *"When and why PINNs fail to train: A neural tangent kernel perspective"* (2022).
