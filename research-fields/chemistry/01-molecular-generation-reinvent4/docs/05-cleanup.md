# 05. クリーンアップ

## 課金停止の最短ルート

Resource Group を丸ごと削除するのが確実です。

```bash
# 1) Compute cluster を 0 に縮小 (min_instances=0 が効いているので通常不要だが念のため)
az ml compute update \
  --name molgen-cpu \
  --min-instances 0 \
  --max-instances 1 \
  -g "$AZURE_RESOURCE_GROUP" \
  -w "$AZURE_WORKSPACE_NAME"

# 2) Resource Group を削除 (最も確実な課金停止)
az group delete --name "$AZURE_RESOURCE_GROUP" --yes --no-wait
```

削除ジョブは 5〜10 分バックグラウンドで実行されます。

## 個別リソースだけを止めたい場合

**Compute だけ止める** (再生成の予定がある場合):

```bash
az ml compute update \
  --name molgen-cpu \
  --min-instances 0 \
  --max-instances 1 \
  -g "$AZURE_RESOURCE_GROUP" \
  -w "$AZURE_WORKSPACE_NAME"
```

> [!NOTE]
> `--max-instances 0` は AML CLI が拒否します（下限 1）。上記コマンドは `min=0` によってアイドル時に自動でノードを 0 に落とし、compute VM 課金を止めます。完全に削除したい場合は `az ml compute delete --name molgen-cpu ...` を使ってください。

**Workspace + 依存リソースを残しつつ prior だけ消す**:

```bash
CONTAINER=$(az ml datastore show -n workspaceblobstore \
  -g "$AZURE_RESOURCE_GROUP" -w "$AZURE_WORKSPACE_NAME" \
  --query 'container_name' -o tsv)

az storage blob delete-batch \
  --account-name "$AZURE_STORAGE_ACCOUNT" \
  --source "$CONTAINER" \
  --pattern "reinvent4-priors/*" \
  --auth-mode login
```

## 削除後の確認

```bash
az group exists --name "$AZURE_RESOURCE_GROUP"
# false と表示されれば完全削除完了
```

## コストの最終確認

Azure Cost Management で本 quickstart にかかった課金を確認:

- Portal > Cost Management + Billing > Cost analysis
- Scope: Resource Group filter を `rg-spread-chem-molgen` に設定
- 詳細: [`../../../../docs/01-cost-management.md`](../../../../docs/01-cost-management.md)

想定範囲: **$0.10〜$0.50** (1 回の生成ラン + Bicep デプロイ)
