# 05. クリーンアップと課金停止

> [!WARNING]
> **プールを 0 に縮小せず放置すると 1 週間で ¥227,000 超の課金**が発生します。
> このドキュメントの手順を必ず実施してください。

> [!IMPORTANT]
> このドキュメントのコマンドは基本的に **ローカル PC (もしくは Cloud Shell)** で、`deploy.sh` を実行した本人の Azure アカウント (Owner / Contributor + User Access Administrator) で実行してください。Controller VM の Managed Identity には VM deallocate / management policy 作成 / resource group 削除 / Cost 参照の権限はありません。
>
> ただし **§3 (`nf-work/` の Blob 手動削除)** については、
> - 実行アカウントに `Storage Blob Data Contributor` (もしくは同等の Blob data plane 権限) がある場合 → ローカル PC で実行可
> - 権限がない場合 → **Controller VM 上 (VM deallocate 前)** で実行 (`STORAGE="$AZURE_STORAGE_ACCOUNT"` を先に設定してください)
>
> **§2 (management policy) は Blob data plane 権限では作成できません**。`Contributor` / `Storage Account Contributor` など management plane 権限のあるローカル PC のアカウントで実行してください。
>
> 事前に以下を設定 (`deploy.sh` の出力を参照):
> ```bash
> export AZURE_RESOURCE_GROUP=rg-spread1000-rnaseq-tanaka  # ← 自分の値
> export AZURE_BATCH_ACCOUNT=batspread1000rnaseqtanaka     # ← 自分の値
> export AZURE_STORAGE_ACCOUNT=stspread1000rnaseqtanaka    # ← 自分の値
> az login  # 未ログインの場合
> ```

## 1. 最低限やること (課金停止)

### 1.1 Batch プールを 0 ノードに強制縮小

```bash
az batch account login --resource-group "$AZURE_RESOURCE_GROUP" --name "$AZURE_BATCH_ACCOUNT"

# 既存プール一覧
az batch pool list \
  --query '[].{id:id,currentDedicated:currentDedicatedNodes,currentSpot:currentLowPriorityNodes,state:allocationState}' \
  -o table

# すべてのプールを 0 に強制縮小 (実行中タスクは即時停止される)
for POOL in $(az batch pool list --query "[].id" -o tsv); do
  echo "Disabling autoscale on $POOL..."
  # nf-core/rnaseq のプールは autoscale 有効。resize する前に autoscale を止める必要あり。
  az batch pool autoscale disable --pool-id "$POOL" 2>/dev/null || true

  echo "Resizing pool $POOL to 0..."
  az batch pool resize \
    --pool-id "$POOL" \
    --target-dedicated-nodes 0 \
    --target-low-priority-nodes 0 \
    --node-deallocation-option requeue
done
```

`--node-deallocation-option requeue` は再実行可能。実行中タスクを **完了させてから** 停止したい場合は `taskcompletion` を指定 (時間はかかるが安全)。

### 1.2 Controller VM を停止

Controller VM は Nextflow を動かすためだけの軽量 VM (B2s、¥8.80/h) ですが、常時起動していれば月 ¥6,336 かかります。使わない期間は停止:

```bash
az vm deallocate --resource-group "$AZURE_RESOURCE_GROUP" --name vm-nf-controller
# または: az vm stop で停止のみ (課金は継続する — deallocate が正解)
```

再開: `az vm start --resource-group "$AZURE_RESOURCE_GROUP" --name vm-nf-controller`

## 2. Blob ライフサイクル管理 (自動アーカイブ)

`nf-work/` は解析中に一時的に肥大化します (200 GB 程度)。完了後は必要な出力を確認したら削除するか、Cool tier に移動:

```bash
# ライフサイクル ポリシー: nf-work/ は 7 日で Cool, 60 日で削除
cat > /tmp/lifecycle.json <<'EOF'
{
  "rules": [
    {
      "enabled": true,
      "name": "nf-work-lifecycle",
      "type": "Lifecycle",
      "definition": {
        "filters": {
          "blobTypes": ["blockBlob"],
          "prefixMatch": ["omics/nf-work/"]
        },
        "actions": {
          "baseBlob": {
            "tierToCool": {
              "daysAfterModificationGreaterThan": 7
            },
            "delete": {
              "daysAfterModificationGreaterThan": 60
            }
          }
        }
      }
    }
  ]
}
EOF

az storage account management-policy create \
  --account-name "$AZURE_STORAGE_ACCOUNT" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --policy @/tmp/lifecycle.json
```

> [!NOTE]
> Cool tier は最低 30 日保存を前提とし、早期削除料金・データ取得料金が発生します。**論文投稿後に再解析予定がなければ、Cool 経由せず直接削除するのが最も安価** です。参考: [Blob access tiers](https://learn.microsoft.com/en-us/azure/storage/blobs/access-tiers-overview)

## 3. 手動で古い nf-work を削除

```bash
# ローカル PC で実行する場合は事前に $AZURE_STORAGE_ACCOUNT が設定済みであること。
# Controller VM 上で実行する場合は先に:
#   export AZURE_STORAGE_ACCOUNT=<自分の値>

# 30 日以上経過した nf-work プレフィクスを列挙
az storage blob list \
  --account-name "$AZURE_STORAGE_ACCOUNT" \
  --auth-mode login \
  --container-name omics \
  --prefix "nf-work/" \
  --query "[?properties.lastModified < '$(date -d '30 days ago' -Iseconds)'].name" \
  -o tsv > /tmp/old-workdirs.txt

# 対話確認
head /tmp/old-workdirs.txt
wc -l /tmp/old-workdirs.txt

# 削除 (対話確認後)
read -rp "上記を削除しますか？ [y/N] " ANS
if [[ "$ANS" == "y" ]]; then
  cat /tmp/old-workdirs.txt | xargs -P 8 -I{} az storage blob delete \
    --account-name "$AZURE_STORAGE_ACCOUNT" \
    --auth-mode login \
    --container-name omics \
    --name "{}"
fi
```

## 4. リソースグループごと削除 (プロジェクト終了時)

```bash
# 事前に Key Vault 名を控える (削除後にパージするため)
KV_NAMES=($(az keyvault list --resource-group "$AZURE_RESOURCE_GROUP" --query "[].name" -o tsv))
RG_LOCATION=$(az group show --name "$AZURE_RESOURCE_GROUP" --query location -o tsv 2>/dev/null || echo "")
echo "対象 Key Vault: ${KV_NAMES[@]:-(なし)} (location: ${RG_LOCATION})"

# 削除実行 (5-15 分)
az group delete --name "$AZURE_RESOURCE_GROUP" --yes

# Key Vault は soft-delete 保護が残る (7 日間)。放置しても課金は発生しない
for KV in "${KV_NAMES[@]}"; do
  read -rp "Key Vault '${KV}' をパージしますか？ [y/N] " ANS
  if [[ "${ANS}" == "y" ]]; then
    az keyvault purge --name "${KV}" --location "${RG_LOCATION}"
  fi
done
```

> [!CAUTION]
> **`az keyvault list-deleted` を検索して自動パージしてはいけません**。別プロジェクト・別ユーザーの Vault を巻き込む事故が発生します。必ずリソースグループから取得した名前のみをパージ対象にし、対話確認を挟んでください。

## 5. 課金確認 (完了 24 時間後)

```bash
az consumption usage list \
  --start-date $(date -d '7 days ago' +%Y-%m-%d) \
  --end-date $(date +%Y-%m-%d) \
  --query "[?tags.project=='spread1000' && tags.scenario=='rnaseq-nextflow'].{svc:instanceName,cost:pretaxCost,unit:usageQuantity}" \
  -o table
```

または Azure Portal → **コスト管理 + 請求** → **コスト分析** → タグフィルタ `scenario=rnaseq-nextflow`。

> [!TIP]
> **差次的発現解析 (DE) を続ける場合の手順は [`docs/04-real-data.md` の「§8 差次的発現解析 (DE) を続ける場合」](04-real-data.md#8-差次的発現解析-de-を続ける場合)** に移動しました (Controller VM 上でクリーンアップより先に実行するため)。

## チェックリスト (課金停止確認)

- [ ] すべての Batch プールが `currentDedicatedNodes: 0` かつ `currentLowPriorityNodes: 0` (Spot ノードも課金対象)
- [ ] Controller VM が `PowerState/deallocated`
- [ ] `nf-work/` にライフサイクル管理設定済み、または手動削除済み
- [ ] Blob 容量が想定内 (Azure Portal → Storage account → Metrics で確認)
- [ ] 課金レポートで `scenario=rnaseq-nextflow` タグの日次コストが想定内

## 次のステップ

- 別の実験を回す → `docs/04-real-data.md` に戻る
- Azure ML で DE 解析を統合したい → 別クイックスタート予定
