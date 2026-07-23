# トラブルシューティング

## インストール

### `ERROR: Could not find a version that satisfies the requirement torch==2.13.0` / `numpy==2.5.1`

依存パッケージ (特に numpy 2.5.1) が Python 3.12 以上を要求します。`python --version` で **3.12 以上** を確認してください。

Windows で複数の Python がインストールされている場合、`py -3.12 -m pip install ...` のように明示してください。

### `error: Microsoft Visual C++ 14.0 or greater is required` (Windows)

ネイティブ拡張のビルドが必要と誤検知しています。`pip install --upgrade pip wheel setuptools` を実行してから再度 `pip install -r requirements.txt` を試してください。CPU 版 torch は wheel が提供されているのでビルドは通常不要です。

### `Killed` / `MemoryError` (Linux, インストール中)

`pip install` がスワップ不足で OOM しています。以下を試してください:

```bash
pip install --no-cache-dir -r requirements.txt
```

## データ準備

### `urllib.error.HTTPError: 403 Forbidden`

UCI サーバのミラーが変更された可能性があります。以下を手動で試して、成功した URL の ZIP を `data/har.zip` に配置してください:

- https://archive.ics.uci.edu/static/public/240/human+activity+recognition+using+smartphones.zip
- https://archive.ics.uci.edu/ml/machine-learning-databases/00240/UCI%20HAR%20Dataset.zip

その後 `prepare_data.py` を再実行するとキャッシュされた ZIP から展開が始まります。

### `RuntimeError: unsafe zip entry`

ダウンロードした ZIP が信頼できない状態です。`data/har.zip` を削除して再実行してください。

### `AssertionError: subject leak`

`prepare_data.py` は train と test の被験者 ID が重複しないことを検証しています。UCI HAR で本来ありえないため、データセットが破損しているか、上記の 403 対処で誤った ZIP を配置した可能性があります。`data/har.zip` を削除して再実行してください。

## 学習

### 「val macro-F1 が 0.5 台で頭打ち」

- 標準化統計が train 以外で fit されている可能性を確認してください（本コードでは正しく train のみで fit しています）
- `--seed` を変えて再現するか確認 (数 seed で確認して大きなばらつきなら実装ではなく確率の問題)
- Loss が下がっていない場合は `--lr` を `5e-4` に下げるか、`--batch-size 64` にしてみてください

### 「val macro-F1 = 1.0 になる / 明らかに高すぎる」

**バグ疑いです**。以下を疑ってください:

1. train と val に同じ被験者が入っている (被験者リーク)
2. 標準化統計を全データで fit している (label 相当情報がリーク)
3. test を train に混入している

本コードは 1〜3 を assert で防いでいますが、コードを改変した場合は再確認を。

### `RuntimeError: DataLoader worker (pid xxx) exited unexpectedly` (Windows)

`num_workers > 0` にした場合の既知の問題です。本コードは `num_workers=0` に固定しているため通常発生しませんが、改変時は Windows で `if __name__ == "__main__":` ガードを必ず入れてください。

### 学習が遅い (CPU で 30 分以上)

- `--batch-size 256` に上げる (メモリに余裕があれば)
- `torch.set_num_threads(...)` の値を CPU コア数に合わせる (`os.cpu_count()`)
- 他の重いプロセスを止める (ブラウザ、ビデオ会議など)

## 評価

### `FileNotFoundError: normalization.npz`

`train.py` を実行せずに `evaluate.py` を実行しています。先に `train.py` を実行してください。

### `RuntimeError: Error(s) in loading state_dict`

`best_model.pt` のモデル構造と `model.py` の `BiosignalCNN` が一致していません。`model.py` を改変した場合は `train.py` を再実行して新しい重みを保存してから `evaluate.py` を実行してください。

## Azure ML (発展編)

### `Environment not found: acpt-pytorch-2.8-cuda12.6`

Microsoft がキュレーション環境名を更新した可能性があります。以下で現行名を確認して `train_job.yml` の `environment:` を更新してください:

```bash
az ml environment list --registry-name azureml \
  --query "[?contains(name, 'acpt-pytorch')].{name:name, latest:latest_version}" \
  --output table
```

### `Quota exceeded for NCasT4v3Family`

サブスクリプションで T4 の vCPU クォータが不足しています:

```bash
# 現状確認
az vm list-usage --location japaneast --query "[?contains(name.value, 'NCasT4')]"

# 増加申請 (Azure Portal → Help + support → New support request)
```

`NCasT4_v3` は 1 ノード = 4 vCPU なので、`min=0, max=1` なら 4 vCPU あれば起動できます。

### 「ジョブは成功したが outputs/ が空」

`command:` の中で `--output-dir ${{outputs.artifacts}}` を渡し忘れています。YAML を再確認してください。
