# 04 — ニューラル PDE サロゲート (2D 移流拡散方程式)

**分野**: 気候・気象、海洋、地球流体、宇宙プラズマ、都市気流  
**手法**: 2D PDE の有限差分解を教師データに、U-Net で「時刻 t → t+k dt」の写像を学習  
**時間**: ~3-5 分 (CPU、n_train=64, epochs=15)

## 何が学べるか

- **ニューラル PDE サロゲート**の基本パターン (FourCastNet, ClimODE, PDE-Refiner 等の起源)
- 有限差分 (FD) で正解データを生成する仕組み
- 残差学習 (`u + Δu`) と autoregressive rollout の考え方
- サロゲートによる高速化の**考え方** (実際のスピード比は問題設定・実装・ハードウェア次第。本教材の小型 CPU 実装では NumPy FD ソルバがすでに高速なので、明確な速度差は出ないこともあります)

## 対象 PDE

2 次元 移流拡散方程式 (周期境界):

$$\frac{\partial u}{\partial t} = D \nabla^2 u - \left( v_x \frac{\partial u}{\partial x} + v_y \frac{\partial u}{\partial y} \right)$$

- D=0.02 (拡散係数)、v=(0.5, 0.3) (流速ベクトル)
- 64×64 グリッド、CFL 条件を満たす dt

## 使い方

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
python src/train.py --n-train 64 --epochs 15
```

## 出力

- `outputs/best_model.pt`
- `outputs/learning_curve.png` — val relative L2 error の推移
- `outputs/rollout.png` — 3 段グリッド (FD 正解 / サロゲート予測 / 誤差) × 6 タイムステップ
- `outputs/metrics.json`

## 期待精度 (n_train=32, epochs=8 smoke)

```
[epoch  1/8] train_mse=0.00652 val_relL2=0.113
[epoch  4/8] train_mse=0.00003 val_relL2=0.022
[epoch  8/8] train_mse=0.00001 val_relL2=0.012
[rollout] final max err=0.385 (6 steps autoregressive)
```

**1 モデル呼び出し (=5 FD ステップ相当) の relL2 < 0.02** (2% 相対誤差) は「気象向けニューラルサロゲート」の入門レベル。長期 rollout では誤差が蓄積するのが一般的挙動。

## 応用例

| ドメイン | サロゲート対象 |
|---|---|
| 気象・気候 | ERA5 再解析データ (温度、湿度、気圧) の短時間予測 |
| 海洋 | 海面高度、水温の空間パターン予測 |
| 都市 | 大気汚染、風速場の高解像度化 |
| 宇宙物理 | プラズマ シミュレーションの高速化 |
| 材料 | 相場 (phase field) の時間発展 |

## ドキュメント

- [01 前提条件](docs/01-prerequisites.md)
- [02 PDE と有限差分](docs/02-pde-and-fd.md)
- [03 ニューラルサロゲート](docs/03-surrogate.md)
- [04 学習と rollout](docs/04-train.md)
- [05 実データへの拡張](docs/05-your-data.md)
- [06 片付け](docs/06-cleanup.md)
- [07 倫理と限界](docs/07-ethics-and-limits.md)
- [トラブルシューティング](troubleshooting.md)
