# トラブルシューティング

## MedMNIST ダウンロード失敗

- `data/pathmnist.npz` を手動 DL: https://zenodo.org/records/10519652
- `PathMNIST(root='data', download=False)` で読み込み

## `IndexError: too many indices for tensor`

- ラベルの shape に注意: MedMNIST は `(N, 1)` の 2D 配列で返す
- 本教材は `yb.squeeze(-1).long()` で 1D に変換済み

## val_acc が 0.11 前後 (chance level)

- ラベル squeeze を忘れている
- `nn.CrossEntropyLoss` に one-hot ではなく class index を渡しているか確認

## メモリ不足

- `--batch-size 32` に減らす
- `--train-frac 0.05` で train を極小化

## Windows で DataLoader ハング

- `num_workers=0` (デフォルト) を明示

## 精度が飽和しない

- lr scheduler 追加: `torch.optim.lr_scheduler.CosineAnnealingLR`
- モデル容量アップ: base channel を 32 → 64 に
- Data augmentation 強化 (H&E 染色向けの ColorJitter)
