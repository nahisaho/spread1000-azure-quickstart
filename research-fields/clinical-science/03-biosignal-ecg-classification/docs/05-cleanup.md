# 05. クリーンアップ

## 課金停止の最短ルート

Compute cluster を止め、Resource Group を丸ごと削除するのが確実です。

```bash
# 1) Compute cluster を 0 に縮小 (min_instances=0 が効いているので通常不要だが念のため)
az ml compute update \
  --name ecg-t4 \
  --min-instances 0 \
  --max-instances 1 \
  -g "$AZURE_RESOURCE_GROUP" \
  -w "$AZURE_WORKSPACE_NAME"

# 2) Resource Group を削除 (最も確実な課金停止)
az group delete --name "$AZURE_RESOURCE_GROUP" --yes --no-wait
```

削除ジョブは 5〜10 分バックグラウンドで実行されます。

## 個別リソースだけを止めたい場合

**Compute だけ止める** (再学習の予定がある場合):

```bash
az ml compute update \
  --name ecg-t4 \
  --min-instances 0 \
  --max-instances 1 \
  -g "$AZURE_RESOURCE_GROUP" \
  -w "$AZURE_WORKSPACE_NAME"
```

> [!NOTE]
> `--max-instances 0` は AML CLI が拒否します（下限 1）。上記コマンドは `min=0` によってアイドル時に自動でノードを 0 に落とし、compute VM 課金を止めます。完全に削除したい場合は `az ml compute delete --name ecg-t4 ...` を使ってください。

**Workspace + 依存リソースを残しつつデータだけ消す**:

```bash
az storage blob delete-batch \
  --account-name "$AZURE_STORAGE_ACCOUNT" \
  --source datasets \
  --pattern "mitdb-1.0.0/*" \
  --auth-mode login
```

## 削除後の確認

```bash
az group show --name "$AZURE_RESOURCE_GROUP" 2>&1 | grep -i "could not be found"
# → could not be found → 削除完了
```

## 費用の最終確認

Cost Analysis はデータが 8〜24 時間遅延で反映されます。翌日再確認してください。

- Azure Portal > Cost Management > Cost Analysis
- Scope: 該当サブスクリプション
- Group by: **Resource group** で該当 RG を確認
- 詳細: [`../../../../docs/01-cost-management.md`](../../../../docs/01-cost-management.md)
