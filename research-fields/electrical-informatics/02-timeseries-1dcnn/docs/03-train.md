# 03 — 学習

## 実行

```bash
python src/train.py --device cpu --epochs 15 --batch-size 128 --seed 42
```

主要 CLI オプション:

| オプション | 既定 | 説明 |
|---|---|---|
| `--device` | `cpu` | `cpu` / `cuda` |
| `--epochs` | `15` | 最大エポック数 |
| `--batch-size` | `128` | メモリが少なければ 64 に |
| `--lr` | `1e-3` | AdamW 初期学習率 |
| `--weight-decay` | `1e-4` | AdamW 正則化 |
| `--dropout` | `0.30` | 分類ヘッド前 |
| `--patience` | `4` | 早期停止 |
| `--seed` | `42` | 再現性向上用 (完全な再現はハードウェア・バージョン依存) |
| `--class-weights` | `off` | train split のクラス重みを CrossEntropyLoss に適用 |
| `--output-dir` | `<repo>/outputs` | 成果物出力先 |

## モデル

`src/model.py` の `BiosignalCNN` — 3 ブロック Conv1d + BN + ReLU + MaxPool + GAP + Dropout + Linear、**31,846 trainable parameters**。

## 被験者独立 4:1 分割

公式 test は最後まで触らず、公式 train の中だけで `StratifiedGroupKFold` により被験者独立の train / val を切ります。同一被験者が両方に入ることはありません。

## 標準化

チャネル別 mean/std を **train 被験者のみ** で fit し、val / test に同じ統計を適用します。`outputs/normalization.npz` に保存し、`evaluate.py` でも再利用します。

## 再現性

以下を有効化しています。

- `random.seed`, `numpy.random.seed`, `torch.manual_seed`
- `torch.use_deterministic_algorithms(True, warn_only=True)`
- `torch.backends.cudnn.deterministic = True`
- `torch.backends.cudnn.benchmark = False`
- `CUBLAS_WORKSPACE_CONFIG=:4096:8`
- `DataLoader(..., generator=..., num_workers=0)`

ただし、**完全な bitwise reproducibility はハードウェア、CUDA 版、cuDNN 版、PyTorch 版に依存** します。今回の設定は再現性を高めるためのものであり、異なる GPU / driver 間で完全一致を保証するものではありません。

## 期待される出力

```text
[data] official train: X=(7352, 9, 128), subjects=21
[split] train subjects (...): [...]
[split] val   subjects (...): [...]
[model] BiosignalCNN, trainable params = 31,846
[epoch  1/15] train_loss=... val_loss=... val_macro_F1=...  ★ (best, saved)
...
[train] best val macro-F1 = 0.9xxx (epoch xx)
```

`train_history.json` には split 情報、deterministic mode、有効化した CLI 引数、SHA-256 付き成果物情報を保存します。`reproducibility_manifest.json` には環境スナップショットも残ります。
