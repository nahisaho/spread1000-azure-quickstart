# 02 — 転移学習の考え方

## Fine-tuning vs Feature extraction

| モード | Backbone | Head | データ量 |
|---|---|---|---|
| **Feature extraction** (本教材) | 凍結 (eval + requires_grad=False) | 学習 | 少数 (数十〜数百) |
| **Fine-tuning (upper layers)** | 上位ブロックのみ学習 | 学習 | 中規模 (数千) |
| **Full fine-tuning** | 全層学習 (lr 小さめ) | 学習 | 大規模 (数万+) |

**目安**: データが 1000 サンプル以下ならまず feature extraction、それ以上なら fine-tuning を検討。

## なぜ Backbone 凍結が有効か

- ImageNet 事前学習は **一般的な視覚特徴** (エッジ、テクスチャ、部分形状) を学習済み
- 少数データで backbone を fine-tune すると **既に有用な表現を破壊**する (catastrophic forgetting)
- head だけ学習 → 既存表現を組み合わせるだけで数十サンプルでも動く

## BatchNorm の罠

- backbone を `requires_grad=False` にしても、`model.train()` すると BatchNorm の running mean/var が更新される
- **本教材の対応**: 学習ループの最初に `for m in model.modules(): if isinstance(m, nn.BatchNorm2d): m.eval()` を実行
- これがないと、少数バッチの統計値が backbone の pretrained BN 統計を汚染して精度が落ちる

## Data augmentation

- 少データでは augmentation が accuracy に大きく効く
- 本教材: `RandomResizedCrop(224, scale=(0.7, 1.0))` + `RandomHorizontalFlip`
- 追加候補: `ColorJitter`, `RandomRotation`, `TrivialAugmentWide`
