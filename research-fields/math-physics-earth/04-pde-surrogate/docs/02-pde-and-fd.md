# 02 — PDE と有限差分

## 移流拡散方程式

$$\frac{\partial u}{\partial t} = \underbrace{D \nabla^2 u}_{\text{拡散}} - \underbrace{\mathbf{v} \cdot \nabla u}_{\text{移流}}$$

- **拡散項** $D \nabla^2 u$: u を平滑化 (熱、濃度、渦度の拡散)
- **移流項** $\mathbf{v} \cdot \nabla u$: 流速 $\mathbf{v}$ に沿って u を運ぶ (風、海流)
- 気象・海洋・化学工学の基本方程式群 (Navier-Stokes の簡略型)

## 有限差分による離散化

**空間** (中心差分, 周期境界):
$$\nabla^2 u \approx \frac{u_{i+1,j} + u_{i-1,j} + u_{i,j+1} + u_{i,j-1} - 4 u_{i,j}}{\Delta x^2}$$

`np.roll(u, 1, axis=0)` が周期シフト → 境界処理不要。

**時間** (陽的 Euler):
$$u^{n+1} = u^n + \Delta t \cdot \text{RHS}(u^n)$$

## CFL 条件

安定性のために:
$$\Delta t < \min\left( \frac{\Delta x}{|\mathbf{v}|}, \frac{\Delta x^2}{4D} \right)$$

- 移流優位: 流速がグリッドを 1 セル進む時間より短く
- 拡散優位: 拡散が 1 セル広がる時間より短く

本教材では 0.4 倍の安全係数を掛けている。

## なぜ FD より NN サロゲートが有利になり得るか

- 64×64 グリッドで 40 タイムステップ = 40 回の全格子更新
- 実用気象モデル (ECMWF IFS) は数百万格子、数千タイムステップ → **1 予報 = 数時間**
- ニューラルサロゲートは 1 forward pass で k タイムステップ先を出力 → 大規模問題では**数百倍高速**の報告例あり
- ただし本教材の 64×64 NumPy FD は既に高速なため、教材レベルでは劇的な速度差は出ないのが普通です

## 参考文献

- LeVeque (2007). *"Finite Difference Methods for Ordinary and Partial Differential Equations"*
- Bar-Sinai et al. (2019). *"Learning data-driven discretizations for partial differential equations"*, PNAS
