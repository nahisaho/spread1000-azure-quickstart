# トラブルシューティング

## `ModuleNotFoundError: torch`

CPU 版 PyTorch をインストール:

```bash
pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu
```

## `test_acc` が 0.17 前後 (chance level)

- BatchNorm を eval() 化していないか確認 (本教材は end-to-end 学習なので `train()` が正しい)
- lr を試す (`--lr 5e-4` or `--lr 2e-3`)
- Epochs を増やす (`--epochs 30`)

## 実データで学習が発散

- **入力正規化**を必ず行う (per-band z-score)
- lr を下げる (`--lr 3e-4`)
- Adam の gradient clipping: `torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)`

## メモリ不足

- `--batch-size 16`
- `--n-per-class 100`

## Windows で `RuntimeError: DataLoader worker`

- 本教材は `num_workers` 指定なし (=0) なので該当なし
