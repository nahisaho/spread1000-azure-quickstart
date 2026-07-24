# 06: クリーンアップ (課金停止)

Azure 課金を確実に停止するための手順です。CPU パス（ローカルのみ）は課金対象外なので、GPU/Azure パスを使った場合のみ実施します。

> **前提**: `.env` を読み込んでいること — `source .env` (変数: `RG`, `WS`, `LOC`, `KV_NAME`)

## Step 1: Compute Cluster を削除（最重要）

Compute Cluster は 0 ノードでも登録が残ると、次回以降のジョブで再利用されます。完全に課金を止めるには **削除** が確実です。

```bash
# Compute Cluster を削除（今後使わないなら推奨）
az ml compute delete --name t4-cluster -g "$RG" -w "$WS" --yes

# 削除後、クラスタは自動的に再作成されません。
# 再利用する場合は: az ml compute create -f infra/t4-cluster.yml -g "$RG" -w "$WS"
```

または Studio → **Compute → Compute clusters → `t4-cluster` → Delete**

> **重要**: クラスタを削除しても、次のジョブ提出時に自動再作成されることは **ありません**。手動で再作成が必要です。

一時停止のみ（削除しない場合）:
```bash
# Minimum nodes を 0 に確認（既定 0 ならスケールダウン後は自動停止）
az ml compute update --name t4-cluster -g "$RG" -w "$WS" --min-instances 0
```

## Step 2: 未使用ストレージの削除

```bash
# ジョブ出力ディレクトリのサイズ確認
az storage blob list \
  --account-name "$STORAGE_ACCOUNT" \
  --container-name azureml \
  --prefix "ExperimentRun/dcid.<JOB_NAME>/" \
  --query "[].{name:name, size:properties.contentLength}" -o table

# 必要ならローカルにダウンロードしてから削除
az ml job download --name <JOB_NAME> --output-name adapter --all --download-path ./local/
az storage blob delete-batch \
  --account-name "$STORAGE_ACCOUNT" \
  --source azureml \
  --pattern "ExperimentRun/dcid.<JOB_NAME>/*"
```

## Step 3: AML 関連サービスを個別削除する場合

```bash
# AML 内のコンピュートや環境だけ削除（ワークスペースを残す場合）
az ml compute delete --name t4-cluster -g "$RG" -w "$WS" --yes
az ml environment archive --name spread-lora-gpu --version 1 -g "$RG" -w "$WS"
```

## Step 4: ワークスペース・リソースグループ全体を削除する場合

**注意**: ワークスペースを削除すると、登録モデル・データセット・ジョブ履歴もすべて失われます。

```bash
# ワークスペースのみ削除
az ml workspace delete --name "$WS" -g "$RG" --yes --permanently-delete

# リソースグループごと削除（全リソースを一括削除）
az group delete --name "$RG" --yes --no-wait

# 削除完了まで待機
az group wait --name "$RG" --deleted

# Key Vault のソフト削除が残る場合はパージ
# ⚠️ purge protection が有効な場合、ソフト削除保持期間（7 日）が
#    経過するまで即時パージはできません。
az keyvault purge --name "$KV_NAME" --location "$LOC"
```

> **Key Vault パージ保護に関する注意**:
> `infra/main.bicep` では `enablePurgeProtection: true`, `softDeleteRetentionInDays: 7` を設定しています。
> このため、KV をリソースグループと同時に削除しても、**7 日間はソフト削除状態**で残ります。
> `az keyvault purge` を実行しても保持期間中はエラーになります。7 日後に再実行してください。

## Step 5: HuggingFace / Python キャッシュのクリーンアップ（ローカル）

ローカル環境で 3〜10 GB のモデルキャッシュが残っている場合:

```bash
# 特定モデルのキャッシュを確認して削除（推奨）
huggingface-cli cache scan
# 削除したいスナップショット ID を確認してから:
huggingface-cli cache rm <snapshot-id>

# または特定モデルのみ削除
rm -rf ~/.cache/huggingface/hub/models--microsoft--Phi-4-mini-instruct/
rm -rf ~/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/

# ⚠️ 全キャッシュ一括削除は他プロジェクトにも影響します。
#    hf cache rm による確認削除を推奨します。
# 全量確認: du -sh ~/.cache/huggingface/
```

## 課金の再確認

```bash
# Cost Management で現在の日次課金を確認
az consumption usage list --billing-period-name $(date +%Y%m)01 \
  --query "[?contains(instanceName, '$RG')]" -o table
```

または Portal → Cost Management → **Cost analysis** で確認:
- **サービス**: Machine Learning が主
- **日次課金**: Cluster が 0 に戻った日以降は **$0.02/day 未満**（Storage のみ）であるべき

## チェックリスト

- [ ] Compute Cluster が 0 ノードになっている、または削除済み（`az ml compute delete`）
- [ ] Storage 上の不要な出力を削除、またはリソースグループ削除済み
- [ ] Key Vault がパージされた（または 7 日待機中）
- [ ] ローカルの HuggingFace キャッシュを `huggingface-cli cache rm` で整理済み
- [ ] Cost Management で当日以降の日次課金がストレージ料金 (<$0.03/day) のみになっている
