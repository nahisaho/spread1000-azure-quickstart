# トラブルシューティング

## Fashion-MNIST ダウンロード失敗

- torchvision のダウンロード URL が変わっている可能性。手動で `data/FashionMNIST/raw/` に配置:
  https://github.com/zalandoresearch/fashion-mnist
- または `--n-subset 512` で先に小規模テストしてから増やす

## 生成物が全て真っ黒 / 真っ白

- 学習が全く進んでいない → epoch を増やす、lr を上げる
- Reverse process のスケジューラ実装ミスの可能性 → `src/model.py` の `p_sample_loop` を確認

## MPS (macOS) で NaN

- `--device cpu` に切り替え。MPS は GroupNorm/一部演算で不安定。

## メモリ不足

- `--batch-size 32` に減らす
- `--n-subset 2000` に減らす
