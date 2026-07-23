# Troubleshooting

## インストール

### `RuntimeError: version mismatch: torch/torchvision`
バージョンを合わせて再インストール:
```bash
pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cpu  # or cu126
```

### `ImportError: cannot import name 'binary_jaccard_index'`
`torchmetrics<0.11` の古い API。アップグレード:
```bash
pip install --upgrade "torchmetrics>=1.4"
```

### `ModuleNotFoundError: No module named 'skimage'`
```bash
pip install "scikit-image>=0.24"
```

## 実行時エラー

### `RuntimeError: BCELoss found dtype Byte for target`
Mask の dtype が `uint8` や `bool`。Dataset で `.float()` に変換してから返します:
```python
mask = torch.from_numpy(m).float()   # NOT .byte() / .bool()
```

### `RuntimeError: input and target must have the same shape`
`(N, 1, H, W)` に統一。特に `mask` は `(N, H, W)` になりがちなので `.unsqueeze(1)` するか、Dataset で `[np.newaxis]` を付ける (本 `generate_data.py` は付けています)。

### `RuntimeError: expected scalar type Float but found Long`
Model の入力に `.float()` を忘れています。`train.py` で `torch.from_numpy(...).float()` に。

### `AssertionError: image_size must be divisible by 4`
MiniUNet は 2 段の MaxPool を使うので入力サイズは 4 の倍数必須。`--image-size 128` (既定) または `256`, `512` を使用。

### CUDA out of memory
- `--batch-size` を小さくする (16 → 8 → 4)
- `--image-size` を小さくする (512 → 256)
- MiniUNet は本来 T4 で潤沢 (< 200 MB) なので、他プロセスが GPU を掴んでいないか `nvidia-smi` で確認

## 学習が上手くいかない

### Val loss は下がるが IoU がずっと 0
- Sigmoid の二重適用: `model.forward` に `torch.sigmoid()` を書いていないか確認 (本実装は logits を返す設計)
- 閾値の適用忘れ: 推論時は `(torch.sigmoid(logits) > 0.5).long()` に変換してから metric に渡す

### 予測が全画面白
- `--pos-weight` が高すぎ (陽性側にバイアス過剰)。`5.0` に下げる
- 学習率が高すぎ (`--lr 5e-4` に)

### 予測が全画面黒
- `--pos-weight` が低すぎ (陽性ロスが弱い)。`15.0` に上げる
- クラス不均衡が想定より強い。`[data] boundary/positive pixel fraction` を確認し、`pos_weight = (1 - p) / p` に

### Train loss が下がるが Val が下がらない (過学習)
- `--n-train 500` に増やす (合成データなので無料で増やせる)
- ドロップアウトを model.py に追加

### エポック数が足りない (収束前に打ち切り)
- `--epochs 30` に増やしてみる。Val IoU が飽和するエポックが真の目安

## Windows / WSL2 固有

### DataLoader が hang (Windows/WSL2)
`--num-workers 0` (既定) を維持。**Windows の spawn マルチプロセスが `TensorDataset` の pickle に失敗** することがあります。

### `OSError: [WinError 1455]` (Windows)
仮想メモリ (ページファイル) 不足。設定 → システム → 詳細情報 → パフォーマンス設定 → 詳細設定 → 仮想メモリ で 8 GB 以上に。

## Azure ML 固有

### Compute Instance の GPU が見えない
```bash
nvidia-smi   # → error?
python -c "import torch; print(torch.cuda.is_available())"  # False?
```
curated 環境が CPU 版 PyTorch の可能性。上記手順で CUDA 版を再インストール。

### `Compute target not found: gpu-cluster-nc4t4`
CommandJob 実行前に `az ml compute create --type amlcompute ...` で Compute Cluster を作成 ([03-aml-gpu.md](docs/03-aml-gpu.md) 参照)。Compute Instance では CommandJob は実行できません。

### 結果が消えた (CommandJob 実行後)
`outputs` パラメータを `{"results": Output(type=URI_FOLDER, mode="rw_mount")}` に設定し、`--output ${{outputs.results}}` を train.py に渡してください。

## 出力

### モンタージュ画像が小さくて見にくい
`train.py` の `plt.savefig(..., dpi=100)` を `dpi=150` に。または `--n-montage 3` に減らして 1 行を大きく。

### `per_image_metrics.json` が空
検証データが 0 枚。`--n-val 50` を確認。
