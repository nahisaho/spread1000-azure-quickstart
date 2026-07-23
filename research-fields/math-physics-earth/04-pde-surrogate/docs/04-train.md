# 04 — 学習と rollout

```bash
python src/train.py --n-train 64 --epochs 15 --k-step 5
```

## CLI

| フラグ | 既定 | 説明 |
|---|---|---|
| `--n-train` | 64 | 学習用トラジェクトリ数 |
| `--n-val` | 16 | 検証用トラジェクトリ数 |
| `--n-steps` | 40 | 各トラジェクトリの FD ステップ数 |
| `--k-step` | 5 | 何ステップ先を予測するか |
| `--epochs` | 15 | |
| `--batch-size` | 32 | |
| `--lr` | 1e-3 | Adam |

## 期待進行

```
[data] generating FD solutions: n_train=64 n_val=16 n_steps=40
[data] dt=0.00488, k-step prediction horizon = 0.0244
[data] train pairs=2304 val pairs=576
[model] TinyUNet | params=116,753
[epoch  1/15] train_mse=0.00612 val_relL2=0.11
[epoch  8/15] train_mse=0.00001 val_relL2=0.012
[epoch 15/15] train_mse=0.00001 val_relL2=0.010
[rollout] autoregressive multi-step forecast on 1 val trajectory
[done] best val relL2=0.010, rollout final max err=0.35
```

## rollout.png の見方

3 行 × 7 列 (or fewer) のグリッド:
- **行 1 (FD)**: 有限差分の正解 u(t=0, 5dt, 10dt, ...)
- **行 2 (pred)**: ニューラルサロゲートの autoregressive 予測
- **行 3 (|err|)**: 絶対誤差、赤くなるほど大きい

## サロゲートの高速化 (考え方)

- 1 モデル呼び出し = k FD ステップ相当のジャンプ
- 同じ物理時間 T を進めるのに: FD は N ステップ、サロゲートは N/k 呼び出し
- **ただし絶対速度は問題規模・実装・ハードに大きく依存**
  - 小規模 (64×64, NumPy FD) では NumPy が既に高速で、モデル呼び出しオーバーヘッドで**サロゲートの方が遅い**ことも
  - 大規模 (数百万格子, スパース線形代数) では**明確に速い** — FourCastNet が ECMWF IFS を数百〜数千倍上回るのはこの領域
- 教材レベルでは「速度」より「学習で PDE 挙動を近似できる」ことに注目してください
