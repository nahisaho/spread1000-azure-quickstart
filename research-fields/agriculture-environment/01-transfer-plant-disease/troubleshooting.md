# トラブルシューティング

## Flowers102 ダウンロード失敗 / タイムアウト

- torchvision の Oxford VGG サーバへの接続が不安定な場合:
  - 手動 DL: https://www.robots.ox.ac.uk/~vgg/data/flowers/102/
  - `102flowers.tgz`, `imagelabels.mat`, `setid.mat` を `data/flowers-102/` に配置
- または CIFAR-10 で代替 (`datasets.CIFAR10`) して転移学習パターンを確認

## `RuntimeError: The size of tensor a (X) must match ...`

- ImageNet 正規化を忘れている: `transforms.Normalize(mean=[0.485,...], std=[0.229,...])` を必ず含める

## val_acc が 1/n_classes 前後で動かない

- Backbone が正しく凍結・head が trainable か確認 (MED 12):

```python
# backbone frozen, fc trainable のみが正しい状態
frozen = [n for n, p in model.named_parameters() if not n.startswith("fc.") and p.requires_grad]
trainable = [n for n, p in model.named_parameters() if n.startswith("fc.") and p.requires_grad]
if frozen:
    raise RuntimeError(f"Non-fc params still trainable: {frozen}")
if len(trainable) < 2:
    raise RuntimeError(f"fc not fully trainable: {trainable}")
```

## Windows で DataLoader ハング

- 本教材は `num_workers=0` 固定なので該当なし

## メモリ不足

- `--batch-size 8` に減らす
- `--n-classes 3` に減らして先に動作確認
