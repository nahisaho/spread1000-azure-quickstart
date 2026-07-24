# 03 — 学習

```bash
# 作業ディレクトリを固定してから実行
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/agriculture-environment/01-transfer-plant-disease"
cd "$SCENARIO_DIR"
test -f src/train.py || { echo "wrong dir; abort"; exit 1; }

python src/train.py --epochs 8 --n-classes 5 --seed 42
```

## CLI

| フラグ | 既定値 | 説明 |
|---|---|---|
| `--epochs` | 8 | [1, 100]; >30 は `--allow-long-run` 必須 |
| `--lr` | 1e-3 | fc head の学習率 (0, 1] |
| `--batch-size` | 16 | [1, 256] |
| `--n-classes` | 5 | Flowers102 先頭 N クラス [2, 102] (`--data-root` 時は無視) |
| `--seed` | 42 | [0, 2^32-1] |
| `--data-root` | — | 自前データ (train/val/test サブフォルダ) |
| `--balance` | none | `weighted-loss` / `weighted-sampler` |
| `--best-metric` | val_acc | `val_macro_f1` を不均衡時に推奨 |
| `--fine-tune` | — | layer4 + fc 同時学習 |
| `--scheduler` | none | `cosine` / `step` |
| `--patience` | — | 早期終了エポック数 |
| `--device` | cpu | `cpu` / `cuda` / `mps` |

## 前処理パイプライン

- **学習**: `Resize(256)` → `RandomResizedCrop(224, scale=(0.7,1.0))` → `RandomHorizontalFlip` → `ToTensor` → ImageNet normalize
- **検証/テスト**: `Resize(256)` → `CenterCrop(224)` → `ToTensor` → ImageNet normalize

## 期待進行

```
[data] downloading Flowers102 (~330MB, only first time)
[data] train=50 val=50 test=161
[data] class counts (train): {0: 10, 1: 10, 2: 10, 3: 10, 4: 10}
[model] ResNet18 (backbone frozen) | trainable=2,565 / total=11,179,077
[epoch  1/8] train_loss=1.5921 val_loss=1.3812 val_acc=0.480 val_macro_f1=0.470 *best*
[epoch  4/8] train_loss=0.6244 val_loss=0.5311 val_acc=0.820 val_macro_f1=0.818 *best*
[epoch  8/8] train_loss=0.3811 val_loss=0.4128 val_acc=0.880 val_macro_f1=0.879 *best*
```

## 実行時間

| CPU | epochs=8 |
|---|---|
| Apple M1 | ~5 分 |
| Intel i5 | ~10 分 |
| GPU (CUDA T4) | 1 分未満 |

> [!NOTE]
> MPS (Apple Silicon GPU) を使う場合は `--device mps` を指定 (PyTorch 2.0+ が必要)。

## 出力

- `outputs/best_model.pt` — head + backbone state dict
- `outputs/loss_acc.png`
- `outputs/train_metrics.json` — 学習引数・バージョン・git SHA・クラス数等を記録

## Evaluate

```bash
python src/evaluate.py --model outputs/best_model.pt
```

出力: test accuracy, macro-F1, balanced accuracy, `confusion_matrix.png`, `eval_metrics.json`.
