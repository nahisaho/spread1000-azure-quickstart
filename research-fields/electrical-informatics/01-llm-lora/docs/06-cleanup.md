# 06: クリーンアップ (課金停止)

Azure 課金を確実に停止するための手順です。CPU パス（ローカルのみ）は課金対象外なので、GPU/Azure パスを使った場合のみ実施します。

## Step 1: Compute Cluster を停止（最重要）

Azure ML Studio → **Compute → Compute clusters → `t4-cluster`**

### 確認事項

- **Current nodes** が **0** になっている
- **Idle nodes** が **0**

Idle scale-down（既定 5 分）で自動的に 0 に落ちますが、Studio で明示的に確認してください。

### 手動で 0 に強制する

Cluster を選択 → **Edit** → Minimum number of nodes = 0 → Save

### 完全に削除する（今後使わないなら推奨）

Cluster を選択 → **Delete** → 名前を入力して確定

## Step 2: 未使用ストレージの削除

Blob Storage に残った出力（アダプタ、ログ）は少額ですが継続課金されます。

```bash
# ジョブ出力ディレクトリのサイズ確認
az storage blob list \
  --account-name <YOUR_STORAGE_ACCOUNT> \
  --container-name azureml \
  --prefix "ExperimentRun/dcid.<JOB_NAME>/" \
  --query "[].{name:name, size:properties.contentLength}" -o table

# 必要ならローカルにダウンロードしてから削除
az ml job download --name <JOB_NAME> --output-name adapter --download-path ./local/
az storage blob delete-batch \
  --account-name <YOUR_STORAGE_ACCOUNT> \
  --source azureml \
  --pattern "ExperimentRun/dcid.<JOB_NAME>/*"
```

## Step 3: ワークスペース自体を削除する場合

**注意**: ワークスペースを削除すると、そこに登録されたモデル・データセット・ジョブ履歴もすべて失われます。次のクイックスタートで再利用する予定があるなら **削除しないで Compute Cluster だけ削除する** ことを推奨します。

Portal → Resource groups → `rg-spread1000-e1` → **Delete resource group**

## Step 4: HuggingFace / Python キャッシュのクリーンアップ（ローカル）

ローカル環境で 3〜10 GB のモデルキャッシュが残っている場合:

```bash
# HuggingFace cache
rm -rf ~/.cache/huggingface/hub/models--microsoft--Phi-4-mini-instruct/
rm -rf ~/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/

# または全て
du -sh ~/.cache/huggingface/
rm -rf ~/.cache/huggingface/
```

## 課金の再確認

Portal → Cost Management → **Cost analysis** で確認:
- **サービス**: Machine Learning が主
- **日次課金**: Cluster が 0 に戻った日以降は **$0.02/day 未満**（Storage のみ）であるべき

## チェックリスト

- [ ] Compute Cluster が 0 ノードになっている、または削除済み
- [ ] Storage 上の不要な出力を削除、またはワークスペース削除
- [ ] ローカルの HuggingFace キャッシュを（必要なら）削除
- [ ] Cost Management で当日以降の日次課金がストレージ料金 (<$0.03/day) のみになっている
