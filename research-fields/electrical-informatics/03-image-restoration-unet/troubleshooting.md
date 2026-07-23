# トラブルシューティング

## インストール

### `ERROR: Could not find a version that satisfies the requirement torch==2.7.1`

- Python バージョンが 3.11 以上か確認 (`python --version`)
- `--index-url https://download.pytorch.org/whl/cpu` を付けて再実行:
  ```bash
  pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cpu
  ```

### `Killed` / `MemoryError` (Linux, インストール中)

```bash
pip install --no-cache-dir -r requirements.txt
```

### `error: Microsoft Visual C++ 14.0 or greater is required` (Windows)

```bash
pip install --upgrade pip wheel setuptools
```

## データ生成

### `ModuleNotFoundError: No module named 'skimage'`

`scikit-image` がインストールされていません。`requirements.txt` の依存を再インストール:

```bash
pip install -r requirements.txt
```

## 学習

### 「val PSNR が baseline と大差ない (2 dB 以内)」

- **学習率が高すぎる**: `--lr 5e-4` で再試行
- **エポック不足**: `--patience 8` で早期停止を緩める
- **モデル出力の bug**: `src/model.py` の `head` の後に誤ってアクティベーションを入れていないか確認

### 「val PSNR が epoch 1 で既に 40 dB」

- 学習データと検証データが同じ (`generate_data.py` の split バグ) — `data/train/` と `data/val/` が別内容か確認
- 学習/検証 loader の shuffle 忘れ

### 「comparison.png が全て真っ黒 or 真っ白」

- モデル出力の clamp を忘れている: `pred.clamp(0.0, 1.0)` が train/evaluate の推論経路にあるか確認
- 学習が発散している: `--lr` を下げる、`train_history.json` の `train_loss` が NaN でないか確認

### `RuntimeError: DataLoader worker (pid xxx) exited unexpectedly` (Windows)

本コードは `num_workers=0` に固定しているため通常発生しません。改変時は Windows で `if __name__ == "__main__":` ガードを必ず入れてください。

### 学習が遅い (CPU で 20 分以上)

- `--batch-size 32` に上げる (メモリに余裕があれば)
- 他の重いプロセスを止める
- `torch.set_num_threads(os.cpu_count())` に固定

## 評価

### `FileNotFoundError: best_model.pt`

`train.py` を実行せずに `evaluate.py` を実行しています。先に `train.py` を実行してください。

### `RuntimeError: Error(s) in loading state_dict`

`best_model.pt` のモデル構造と `model.py` の `MiniUNet` が一致していません。`model.py` を改変した場合は `train.py` を再実行して新しい重みを保存してから `evaluate.py` を実行してください。

## Azure ML (発展編)

### `Environment not found: acpt-pytorch-2.8-cuda12.6`

Microsoft がキュレーション環境名を更新した可能性:

```bash
az ml environment list --registry-name azureml \
  --query "[?contains(name, 'acpt-pytorch')].{name:name, latest:latest_version}" \
  --output table
```

### `Quota exceeded for NCasT4v3Family`

```bash
az vm list-usage --location japaneast --query "[?contains(name.value, 'NCasT4')]"
```

Azure Portal → Help + support → New support request で増加申請。
