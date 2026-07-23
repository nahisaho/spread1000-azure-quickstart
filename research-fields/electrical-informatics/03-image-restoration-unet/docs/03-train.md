# 03 — 学習

## 実行

```bash
python src/train.py --device cpu --epochs 20 --batch-size 16 --seed 42
```

主要 CLI オプション:

| オプション | 既定 | 説明 |
|---|---|---|
| `--device` | `cpu` | `cpu` / `cuda` |
| `--epochs` | `20` | 最大エポック数 |
| `--batch-size` | `16` | 128×128 画像で ~200 MB メモリ / batch |
| `--lr` | `1e-3` | AdamW 初期学習率 |
| `--weight-decay` | `1e-4` | AdamW 正則化 |
| `--patience` | `4` | 早期停止 (val PSNR が改善しない epoch 数) |
| `--seed` | `42` | 完全再現用 |
| `--data-dir` | `<repo>/data` | 入力データ |
| `--output-dir` | `<repo>/outputs` | 成果物出力先 |

## モデル

`src/model.py` の `MiniUNet` — 3 レベル U-Net、**約 117K パラメータ**。

```
入力 (B, 1, 128, 128)
  → enc1: DoubleConv(1→16)                          (B, 16, 128, 128)
  → pool + enc2: DoubleConv(16→32)                  (B, 32, 64, 64)
  → pool + bot: DoubleConv(32→64)                   (B, 64, 32, 32)
  → up2 + skip: DoubleConv(64→32)                   (B, 32, 64, 64)
  → up1 + skip: DoubleConv(32→16)                   (B, 16, 128, 128)
  → head: Conv1x1(16→1)                             (B, 1, 128, 128)
```

**D-3 (材料顕微鏡セグメンテーション) と全く同じ構造** です。違いは:

| | D-3 セグメンテーション | E-3 復元 (このシナリオ) |
|---|---|---|
| 出力 | 二値マスク (0/1) | 復元画像 ([0,1]) |
| 損失 | `BCEWithLogitsLoss` | `L1Loss` |
| 出力アクティベーション | 推論時に `sigmoid` | 推論時に `clamp(0,1)` |
| 評価 | IoU / F1 | PSNR / SSIM |

同じ骨格を **タスクの性質だけを変えて再利用** できることが U-Net の魅力です。

## 損失関数の選定 — なぜ L1?

Gaussian ノイズ除去に対しては数式的には L2 (MSE) が最尤推定と一致しますが、**実務では L1 (MAE) が好まれる** 傾向があります。

- L2: 大誤差を強く罰する → 平滑化されすぎ、エッジがぼける
- **L1**: 中程度の誤差を均等に扱う → エッジ・細部が保たれる

Zhao et al. (2017) *"Loss Functions for Image Restoration with Neural Networks"* (IEEE Trans. Computational Imaging) が代表的な比較文献です。より高度な設定では `L1 + 0.1 × SSIM_loss` も有効ですが、教材ではシンプルさを優先して L1 のみを採用します。

## 早期停止

- val **PSNR** が改善するたびにベスト重みを `outputs/best_model.pt` に保存
- `--patience` 回連続で改善しなければ停止
- 学習終了時点でベスト重みを再ロードして比較画像を保存

## Baseline PSNR/SSIM

学習開始前に **noisy 自体を clean と比較した PSNR/SSIM** を測定し、`train_history.json` と学習曲線に記録します。これが「モデルなしで到達できる下限」です。**モデルは必ずこれを上回るはず** です。上回らない場合は実装バグを疑ってください。

期待される baseline: σ=0.10 のノイズなら概ね **PSNR 20 dB, SSIM 0.55** 前後。復元後は **PSNR 30 dB 前後, SSIM 0.90 前後** を目安にしてください（データ・seed によって変動）。

## 期待される出力

```
[data] train=200, val=40
[model] MiniUNet, trainable params = 117,681
[baseline] val noisy vs clean: PSNR=19.99 dB, SSIM=0.5xxx
[epoch  1/20] train_loss=0.05xx val_loss=0.03xx val_PSNR=25.xx val_SSIM=0.8xxx  ★ (best, saved)
...
[epoch 15/20] train_loss=0.01xx val_loss=0.02xx val_PSNR=30.xx val_SSIM=0.9xxx  ★ (best, saved)
...
[train] best val PSNR = 30.xx dB (epoch xx)
```

数値は環境と seed に依存します。詳細な解釈は [docs/04-understand-results.md](04-understand-results.md) を参照してください。

## 再現性

以下を全て設定しています:

```python
random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)
torch.cuda.manual_seed_all(seed)
DataLoader(..., generator=torch.Generator().manual_seed(seed), num_workers=0)
```

CPU / `num_workers=0` の組み合わせでは同一環境なら bit-exact に近い再現性が得られます (BLAS の非決定性を除く)。GPU では [PyTorch 公式ガイド](https://docs.pytorch.org/docs/stable/notes/randomness.html) の追加設定が必要です。

## 成果物

```
outputs/
├── best_model.pt           # ベスト重み (~500 KB)
├── train_history.json      # 学習曲線数値 + baseline
├── loss_curve.png          # L1 損失 + PSNR + baseline PSNR 線
└── comparison.png          # 4 val サンプル: noisy | denoised | clean
```
