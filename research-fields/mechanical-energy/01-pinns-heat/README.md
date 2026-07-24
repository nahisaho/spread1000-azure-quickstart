# 01 — PINNs で 1D 熱伝導方程式を解く

**対象**: PINNs (Physics-Informed Neural Networks) を試してみたい機械・構造・エネルギー系研究者
**目標**: PyTorch だけで **物理制約を組み込んだニューラルネット** を実装し、1D 熱伝導方程式 $u_t = \alpha u_{xx}$ の解を **境界条件・初期条件・PDE 残差** から同時に学習する体験を、ノートPCで おおむね 7〜12 分で得る
**手法**: 座標入力の MLP + Autograd による偏微分 + 3 種類の損失 (PDE 残差 + IC + BC) の合算

> [!NOTE]
> 完全にローカル CPU 完結。追加のライブラリは PyTorch, NumPy, matplotlib のみ (deepxde 不要)。

## 全体像

```
src/train.py --device cpu --epochs 3000

   ├→ 3 損失の重み付き和を Adam で最小化
   │    L = L_pde + 10·L_ic + 10·L_bc
   │    L_pde = MSE(u_t - alpha * u_xx, 0)   ← Autograd で二階微分
   │    L_ic  = MSE(u(x, 0), sin(pi x))
   │    L_bc  = MSE(u(0, t), 0) + MSE(u(1, t), 0)
   │
   └→ outputs/
       ├── final_model.pt
       ├── loss_curve.png
       ├── solution.png          # t=0, 0.25, 0.75 の断面比較
       ├── metrics.json          # validation/test L2 誤差 vs 解析解
       └── provenance.json       # 実行環境・再現性情報
```

## クイックスタート

```bash
cd research-fields/mechanical-energy/01-pinns-heat

# --- torch のインストール (プラットフォームごとに異なる) ---
# Windows/Linux (CPU):
python -m pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu
# macOS (universal2, native pytorch install):
python -m pip install torch==2.7.1
# Linux + CUDA 12.x (optional, for --device cuda):
# python -m pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cu121

python -m pip install --require-hashes -r requirements-lock/linux-cpu-py312.txt
# macOS: requirements-lock/macos-cpu-py312.txt
# Windows: requirements-lock/windows-cpu-py312.txt

python src/train.py --device cpu --epochs 3000 --seed 42
```

## タスク設定

$$
\frac{\partial u}{\partial t} = \alpha \frac{\partial^2 u}{\partial x^2},
\quad x \in [0, 1], \; t \in [0, 1]
$$

- 熱拡散係数 $\alpha = 0.05$
- 初期条件: $u(x, 0) = \sin(\pi x)$
- 境界条件: $u(0, t) = u(1, t) = 0$
- **解析解**: $u(x, t) = e^{-\pi^2 \alpha t} \sin(\pi x)$ — 評価にのみ使用（学習には与えない）

## スタック

| 種別 | 選定 | 理由 |
|---|---|---|
| モデル | MLP (2→32→32→32→32→1, tanh) | 3,297 params、PINN 定番 |
| 微分 | `torch.autograd.grad` で $u_x, u_{xx}, u_t$ を計算 | 自動微分の教科書例 |
| 損失 | L_pde + 10·L_ic + 10·L_bc | IC/BC 重み付けは PINN 常套 |
| 最適化 | Adam (lr=1e-3) → 最終 500 iter を L-BFGS | 初期は Adam、収束時 L-BFGS で精度向上 |
| コロケーション点 | PDE 5000 + IC 200 + BC 200 (各 side) | 一度サンプル、全 epoch 固定 |

## ドキュメント

1. [前提条件](docs/01-prerequisites.md)
2. [PINN の考え方](docs/02-pinns-concept.md) — 何を学習し、何を制約するか
3. [学習](docs/03-train.md) — CLI、Adam→L-BFGS 切替、重み調整
4. [結果の読み方](docs/04-understand-results.md) — L2 誤差、$u(x,t)$ の可視化
5. [発展編](docs/05-extending.md) — 逆問題、実データフィッティング
6. [片付け](docs/06-cleanup.md)
7. [倫理と限界](docs/07-ethics-and-limits.md) — PINN の失敗モード、外挿の危険性

トラブル対応: [troubleshooting.md](troubleshooting.md)

## ライセンス

- コード: リポジトリのライセンスに従う
- データ: 完全合成 (解析解ベースの ground truth)、CC0-1.0 (`data/LICENSE` 参照)

## 免責

**本教材のモデルは教育目的の PINN 入門例です。実世界の CFD/構造解析への応用時は、PINN 固有の failure mode (高周波成分の学習困難、スペクトル bias、複雑幾何での不安定性) を必ず検証してください。**
参考: Wang et al. (2021) *"When and why PINNs fail to train"* および Krishnapriyan et al. (2021) NeurIPS *"Characterizing possible failure modes in physics-informed neural networks"*。
