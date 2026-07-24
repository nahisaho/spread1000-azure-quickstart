# トラブルシューティング

## インストール

### `ERROR: Could not find a version that satisfies the requirement ...`

Python 3.12 系を使っているか `python --version` で確認してください。Windows では `py -3.12 -m pip install -r requirements.txt` のように明示すると確実です。

## データ準備

### `403 Forbidden`

UCI 側の公開 URL が一時的に変わることがあります。`data/har.zip` を手動配置した場合でも、`prepare_data.py` は outer archive SHA-256 を検証します。ハッシュ不一致ならファイルを削除して再取得してください。

### `nested 'UCI HAR Dataset.zip' was not found`

外側 ZIP の展開結果が想定と異なります。破損した ZIP や別アーカイブを置いた可能性があります。`data/har.zip` を削除して再実行してください。

### `subject leak between official train/test`

本来発生しないため、データセット破損の可能性が高いです。`data/har.zip` と `data/UCI_HAR_Dataset/` を削除して再生成してください。

## 学習

### `CUDA requested but not available`

CUDA 付き PyTorch が入っていないか、GPU が見えていません。ローカルでは `--device cpu`、Azure ML では GPU compute を使ってください。

### `non-finite inputs / logits / loss`

入力データ破損、標準化ミス、過大な学習率が主因です。`python src/prepare_data.py` をやり直し、必要なら `--lr 5e-4` を試してください。

### `val macro-F1 = 1.0` のように高すぎる

リーク疑いです。被験者分割、標準化の fit 対象、train/test 混入を再確認してください。

## Azure ML

### `Quota exceeded for NCasT4v3Family`

```bash
az ml compute list-usage --resource-group "$RG" --workspace-name "$WS" -o table
```

不足している場合は Azure Portal から AML/GPU クォータ増加を申請してください。
