# 03 — 学習

## 実行

```bash
python src/train.py --device cpu --epochs 15 --batch-size 128 --seed 42
```

主要 CLI オプション:

| オプション | 既定 | 説明 |
|---|---|---|
| `--device` | `cpu` | `cpu` / `cuda`。GPU は AML 実行時のみ |
| `--epochs` | `15` | 最大エポック数 (早期停止と組み合わせ) |
| `--batch-size` | `128` | メモリが少なければ 64 に |
| `--lr` | `1e-3` | AdamW 初期学習率 |
| `--weight-decay` | `1e-4` | AdamW 正則化 |
| `--dropout` | `0.30` | 分類ヘッド前 |
| `--patience` | `4` | 早期停止 (val macro-F1 が改善しない epoch 数) |
| `--seed` | `42` | 完全再現用 |
| `--output-dir` | `<repo>/outputs` | 成果物出力先 |

## モデル

`src/model.py` の `BiosignalCNN` — 3 ブロック Conv1d + BN + ReLU + MaxPool + GAP + Dropout + Linear、**約 32K パラメータ**。

```
入力 (B, 9, 128)
  → Conv1d(9→32, k=7) + BN + ReLU + MaxPool(2)   → (B, 32, 64)
  → Conv1d(32→64, k=5) + BN + ReLU + MaxPool(2)  → (B, 64, 32)
  → Conv1d(64→96, k=3) + BN + ReLU + MaxPool(2)  → (B, 96, 16)
  → AdaptiveAvgPool1d(1)                          → (B, 96)
  → Dropout(0.30) + Linear(96→6)                  → (B, 6) ロジット
```

シンプルですが UCI HAR には十分な容量です。

## 被験者独立 4:1 分割

**公式 test (2,947 窓, 9 被験者) は最後まで触りません**。公式 train (7,352 窓, 21 被験者) の中で被験者独立に 4:1 に分割し、片方を validation として使います。

```python
from sklearn.model_selection import StratifiedGroupKFold
skf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
train_idx, val_idx = next(skf.split(X_all, y_all, groups=subj_all))
```

これにより:

1. train subjects と val subjects が完全に分離される（同じ人が両方に入らない）
2. train と val でクラス分布ができるだけ揃う
3. 早期停止の目安である val macro-F1 が、公式 test でも近い値になる

## 標準化 (正規化)

チャネル別 mean/std を **train 被験者のみで fit** し、val にも test にも同じ統計を適用します。

```python
mean = X_train.mean(axis=(0, 2), keepdims=True)
std  = X_train.std(axis=(0, 2), keepdims=True).clip(min=1e-6)
```

**per-window 標準化はしません**。EMG 強度や姿勢による振幅差は分類に有用な情報を含むため、これを全窓で消してしまうと性能が下がります（バイオシグナル分類の落とし穴として頻出）。

計算した `mean, std` は `outputs/normalization.npz` に保存され、`evaluate.py` が読み直して同じ変換を test に適用します。

## 早期停止

- val macro-F1 が改善するたびにベスト重みを `outputs/best_model.pt` に保存
- `--patience` 回連続で改善しなければ停止
- ベストの epoch と val macro-F1 を `outputs/train_history.json` に記録

## 再現性

以下を全て設定しています:

```python
random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)
torch.cuda.manual_seed_all(seed)  # cuda 時のみ有効
generator = torch.Generator().manual_seed(seed)
DataLoader(..., generator=generator, num_workers=0)
```

`num_workers=0` は Windows での安定性と、教育目的での挙動の予測性の両方を優先しています。実際の研究では計算時間短縮のため `num_workers>0` を検討してください。

## 期待される出力

```
[data] official train: X=(7352, 9, 128), subjects=21
[split] train subjects (16-17): [1, 3, 5, ...]
[split] val   subjects (4-5):  [7, 17, 23, 27]
[model] BiosignalCNN, trainable params = 32,006
[epoch  1/15] train_loss=1.2xxx val_loss=1.0xxx val_macro_F1=0.5xxx  ★ (best, saved)
[epoch  2/15] train_loss=0.7xxx val_loss=0.6xxx val_macro_F1=0.7xxx  ★ (best, saved)
...
[epoch 12/15] train_loss=0.1xxx val_loss=0.3xxx val_macro_F1=0.90xx  ★ (best, saved)
...
[train] best val macro-F1 = 0.9xxx (epoch xx)
[train] saved → outputs/best_model.pt, outputs/normalization.npz, loss_curve.png
```

具体的な数値は環境・seed によって変動します。**val macro-F1 が 0.85 を大きく下回る場合はどこかで被験者リークやバグが疑われます**（[troubleshooting.md](../troubleshooting.md) 参照）。

## 成果物

```
outputs/
├── best_model.pt           # ベスト重み (< 200 KB)
├── normalization.npz       # チャネル別 mean/std
├── train_history.json      # 学習曲線数値・分割情報
└── loss_curve.png          # 学習曲線可視化
```
