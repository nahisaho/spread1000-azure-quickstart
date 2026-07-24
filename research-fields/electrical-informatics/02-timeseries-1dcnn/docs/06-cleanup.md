# 06 — 片付けと次のステップ

## ローカルで完結した場合

Azure リソースは一切作成していないので、**追加の料金は発生しません**。

不要になれば以下を削除して構いません:

```bash
rm -rf data/ outputs/ .venv/
```

- `data/har.zip`, `data/UCI_HAR_Dataset/`, `data/har_windows.npz`: 再実行時に自動で再生成
- `outputs/`: 学習成果物。**別途保存したい場合は先に別ディレクトリへ退避**

## Azure ML を使った場合

Azure ML 関連のリソースを一括で片付ける場合は、シナリオ付属の cleanup スクリプトを使います。

```bash
./infra/cleanup.sh
```

このスクリプトは以下をまとめて処理します。

- AML compute の削除
- Resource Group deployment の削除
- Resource Group 全体の削除待機
- Key Vault の purge 保護状態確認と、可能な場合のみ purge

保存済みモデル成果物 (`azureml://...`) はワークスペース削除時に関連ストレージとともに削除されます。長期保管したい場合は、cleanup 前に別の場所へ退避してください。

## 応用のヒント

### 別のデータセットに置き換える

`src/prepare_data.py` を書き換えれば任意の多チャネル時系列に置き換えられます。ポイント:

1. **入力形状**: `(N, C, T)` 3 次元 float32 テンソルに整形（C = チャネル数、T = 時点数）
2. **被験者 ID を必ず保存**: 分割リークを防ぐため
3. **公式 test 分割**: 存在するなら使う。なければ **被験者独立** に切る

### 医療・生体信号へ広げるとき

次の文書も参照してください。

- [docs/07-ethics-and-limits.md](07-ethics-and-limits.md)
- [docs/08-adapt-to-medical-data.md](08-adapt-to-medical-data.md)
