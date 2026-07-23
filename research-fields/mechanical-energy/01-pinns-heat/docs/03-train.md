# 03 — 学習

## 実行

```bash
python src/train.py --device cpu --epochs 3000 --seed 42
```

## CLI オプション

| フラグ | 既定値 | 説明 |
|---|---|---|
| `--device` | `cpu` | `cuda` も指定可 |
| `--epochs` | 3000 | Adam フェーズの epoch 数 (L-BFGS は追加で最大 500 iter) |
| `--lr` | 1e-3 | Adam の学習率 |
| `--n-pde` | 5000 | PDE 残差用コロケーション点数 |
| `--n-ic` | 200 | 初期条件サンプル数 |
| `--n-bc` | 200 | 境界条件サンプル数 (両端合計 400) |
| `--w-ic` | 10.0 | IC 損失の重み |
| `--w-bc` | 10.0 | BC 損失の重み |
| `--seed` | 42 | 乱数シード |

## 期待される進行

```
[Adam    100/3000] total=8.2e-2  pde=2.1e-3  ic=8.1e-3  bc=7.4e-4  L2=42.5%
[Adam   1000/3000] total=3.4e-3  pde=1.9e-4  ic=3.2e-4  bc=1.1e-5  L2=5.8%
[Adam   3000/3000] total=6.1e-4  pde=4.2e-5  ic=5.7e-5  bc=1.9e-6  L2=1.4%
[L-BFGS  500]     total=1.2e-5   L2=0.4%
```

**目安**: 最終 L2 相対誤差が **1% 未満** になれば十分。

## 実行時間の目安

| CPU | Adam 3000 | + L-BFGS 500 | 合計 |
|---|---|---|---|
| Apple M1 | ~5 分 | ~2 分 | ~7 分 |
| Intel i5 (8th gen) | ~8 分 | ~3 分 | ~11 分 |

## 出力

- `outputs/best_model.pt` — 学習済みモデル + `alpha`, 最終 L2 誤差
- `outputs/loss_curve.png` — 4 種類の損失 + L2 誤差 (2 軸プロット)
- `outputs/solution.png` — t=0, 0.25, 0.75 における PINN 予測 vs 解析解
- `outputs/metrics.json` — L2 誤差、ハイパラ、点数

## 損失重みの調整

- L2 誤差が 5% 以下まで下がらない → `--w-ic 20 --w-bc 20` を試す (IC/BC の遵守を強化)
- PDE 残差だけ大きい → `--n-pde 8000` に増やす
