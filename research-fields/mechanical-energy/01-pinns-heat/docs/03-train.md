# 03 — 学習

## 実行

```bash
cd research-fields/mechanical-energy/01-pinns-heat
python src/train.py --device cpu --epochs 3000 --seed 42
```

## CLI オプション

| フラグ | 既定値 | 説明 |
|---|---|---|
| `--device` | `cpu` | `cuda` も指定可 (CUDA 版 torch が必要) |
| `--epochs` | 3000 | Adam フェーズの epoch 数 (1〜20000) |
| `--lbfgs-iters` | 500 | L-BFGS 最大 iteration 数 (0〜2000) |
| `--lr` | 1e-3 | Adam の学習率 (> 0) |
| `--n-pde` | 5000 | PDE 残差用コロケーション点数 (1〜100000) |
| `--n-ic` | 200 | 初期条件サンプル数 (1〜10000) |
| `--n-bc` | 200 | 境界条件サンプル数 — 両端合計 400 (1〜10000) |
| `--w-ic` | 10.0 | IC 損失の重み (≥ 0) |
| `--w-bc` | 10.0 | BC 損失の重み (≥ 0) |
| `--seed` | 42 | 乱数シード |
| `--output-dir` | `outputs/` | 出力先ディレクトリ |

## 期待される進行

```
[Adam    100/3000] total=8.2e-2  pde=2.1e-3  ic=8.1e-3  bc=7.4e-4  val_L2=42.5%
[Adam   1000/3000] total=3.4e-3  pde=1.9e-4  ic=3.2e-4  bc=1.1e-5  val_L2=5.8%
[Adam   3000/3000] total=6.1e-4  pde=4.2e-5  ic=5.7e-5  bc=1.9e-6  val_L2=1.4%
[L-BFGS eval  500] total=1.2e-5   val_L2=0.4%
[eval] computing independent test L2 on 257x257 grid...
validation L2 = 0.412%  |  test L2 (independent) = 0.421%
```

**目安**: 最終 `validation_l2_percent` が **1% 未満** になれば十分 (ハイパラ調整の基準)。  
`test_l2_percent` は学習後に一度だけ報告される独立評価値 — チューニングには使わないこと。

## 実行時間の目安

| CPU | Adam 3000 | + L-BFGS 500 | 合計 |
|---|---|---|---|
| Apple M1 | ~5 分 | ~2 分 | ~7 分 |
| Intel i5 (8th gen) | ~8 分 | ~3 分 | ~11 分 |

## 出力

- `outputs/final_model.pt` — 学習済みモデル + `alpha`、validation/test L2 誤差
- `outputs/loss_curve.png` — 4 種類の損失 + validation L2 誤差 (2 軸プロット)
- `outputs/solution.png` — t=0, 0.25, 0.75 の断面比較 (解析解 vs PINN)
- `outputs/metrics.json` — validation/test L2 誤差、ハイパラ、L-BFGS 反復数
- `outputs/provenance.json` — 実行環境 (Python/torch/numpy/matplotlib バージョン、git SHA、再現性設定)

## 損失重みの調整

- `validation_l2` が 5% 以下まで下がらない → `--w-ic 20 --w-bc 20` を試す
- PDE 残差だけ大きい → `--n-pde 8000` に増やす
- 調整は `validation_l2` を基準に行い、最終確認のみ `test_l2` を参照すること
