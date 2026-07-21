# 05. クリーンアップ

**本 quickstart で作成したリソースを完全に削除し、課金を停止します。**

## ⚠️ AI Search Basic は起動しているだけで課金 (~$2.5/日)

放置しないでください。動作確認が終わったら**必ず**リソースグループごと削除します。

## 1. リソースグループごと削除

```bash
cd research-fields/clinical-science/02-ehr-nlp-rag
set -a && source .env && set +a

az group delete --name "$RG" --yes --no-wait
echo "Deletion started for $RG (async)"
```

## 2. 削除完了確認

```bash
# 5〜10 分後に確認
az group show --name "$RG" --query properties.provisioningState -o tsv 2>/dev/null \
  || echo "✅ RG '$RG' is deleted"
```

## 3. Azure OpenAI の Soft-delete と Purge

Azure OpenAI / Cognitive Services リソースは削除後 48 時間 **soft-delete** 状態で保持されます。同じ `customSubDomainName` を使いたい場合は事前に purge が必要です:

```bash
LOCATION="japaneast"
OAI_NAME="oai-ehr-nlp-$UNIQUE_SUFFIX"

# 削除されたリソースを確認
az cognitiveservices account list-deleted --query "[?name=='$OAI_NAME']" -o table

# purge（不可逆）
az cognitiveservices account purge \
  --location "$LOCATION" \
  --resource-group "$RG" \
  --name "$OAI_NAME"
```

> [!TIP]
> **同じサブスクで別 quickstart を試すだけ**なら purge 不要（別 `UNIQUE_SUFFIX` を使えば衝突しません）。

## 4. Key Vault の soft-delete

Key Vault も soft-delete 7 日保持です。今回のテンプレートは `enablePurgeProtection: false` なので、必要なら:

```bash
KV_NAME="kv-ehr-nlp-$UNIQUE_SUFFIX"
az keyvault purge --name "$KV_NAME" --location "$LOCATION"
```

## 5. RBAC 割り当ての残骸確認

RG 削除で AI Search / OpenAI / Storage リソースは消えますが、**割り当てられたロールアサインメントは残る**場合があります（既に存在しないリソースを指すため無害だが、Portal でノイズになる）:

```bash
# 削除されたリソースを指す orphan ロール割当を確認
az role assignment list --all --assignee "$(az ad signed-in-user show --query id -o tsv)" \
  --query "[?contains(scope, '$RG')]" -o table

# 個別削除するには assignment id を指定
# az role assignment delete --ids <assignment-id>
```

## 6. コストの確認

削除処理後 8〜24 時間で Cost Analysis に反映されます:

```bash
# 今月分のコスト（RG 別）
az consumption usage list \
  --start-date "$(date -u +%Y-%m-01)" \
  --end-date "$(date -u +%Y-%m-%d)" \
  --query "[?contains(instanceId, '$RG')].{date:usageStart, service:consumedService, cost:pretaxCost}" \
  -o table
```

## 7. 完了チェックリスト

- [ ] `az group show --name $RG` が「Group not found」を返す
- [ ] Azure Portal の RG 一覧に `spread1000-ehr-nlp` が無い
- [ ] Cost Management で今後のコストが増えないことを確認（翌日確認）
- [ ] （必要なら）Cognitive Services / Key Vault を purge
- [ ] ローカルの `.env` を保管 or 削除

---

## 参照

- [Azure Cognitive Services soft-delete と purge](https://learn.microsoft.com/ja-jp/azure/ai-services/recover-purge-resources)
- [Key Vault soft-delete](https://learn.microsoft.com/ja-jp/azure/key-vault/general/soft-delete-overview)
- [`../../../../docs/01-cost-management.md`](../../../../docs/01-cost-management.md) — 予算アラート・タグ運用の詳細
