# 02. Azure Batch + Storage + Controller VM のデプロイ

このドキュメントでは、Bicep で以下のリソースを一括デプロイします:

- **Batch アカウント** (Batch service allocation mode、追加料金なし)
- **Storage アカウント** + Blob コンテナ `omics` (LRS、Hot tier)
- **Controller VM** (Standard_B2s, Nextflow を動かす軽量ヘッド) + Public IP (Standard, static) + OS ディスク (Standard SSD 64 GB)
- **RBAC**: Controller VM の system-assigned MI に `Storage Blob Data Contributor` (Blob 読み書き) + `Azure Batch Data Contributor` (Batch data plane: pool create/update/delete, autoscale enable/disable, job/task, および `az batch account login` 用の account read) を付与

> [!NOTE]
> Batch pool ノードから Blob へのアクセスは、Controller が発行する **短期 SAS トークン** (本テンプレートでは 96 時間に延長) を経由します。プールに UAMI を直接付ける方式 (Fusion filesystem 用) は初心者向けクイックスタートでは採用していません。
> 参考: [Nextflow Azure — Managed identities](https://docs.seqera.io/nextflow/azure) / [Managed identities in Batch pools](https://learn.microsoft.com/en-us/azure/batch/managed-identity-pools)

## デプロイ手順

### 方法 A: 対話的シェルスクリプト (推奨、初心者向け)

```bash
cd research-fields/life-pharma-science/04-transcriptomics-rnaseq/infra

# 対話モードで実行
./deploy.sh
```

`deploy.sh` は以下を対話で確認します:

1. **サブスクリプション ID** (`az account show` の値をデフォルト表示)
2. **リージョン** (デフォルト `japaneast`)
3. **リソースグループ名** (デフォルト `rg-spread1000-rnaseq-${USER}`)
4. **SSH 公開鍵** (`~/.ssh/id_ed25519.pub` を自動検出、なければ生成)
5. **確認プロンプト**を挟んだ上で `az deployment group create` を実行

完了時に以下が表示されます:

```
✅ デプロイ完了
  Resource Group:       rg-spread1000-rnaseq-tanaka
  Batch Account:        batspread1000rnaseqtanaka
  Storage Account:      stspread1000rnaseqtanaka
  Blob Container:       omics
  Controller VM:        vm-nf-controller
  Controller Public IP: 20.xx.xx.xx

次のステップ:
  1. ssh azureuser@20.xx.xx.xx
  2. curl -sSL https://raw.githubusercontent.com/.../install-nextflow.sh | bash
  3. 環境変数を ~/.bashrc に追加 (deploy.sh 出力より):
       export AZURE_LOCATION=japaneast
       export AZURE_RESOURCE_GROUP=rg-spread1000-rnaseq-tanaka
       export AZURE_BATCH_ACCOUNT=batspread1000rnaseqtanaka
       export AZURE_STORAGE_ACCOUNT=stspread1000rnaseqtanaka
       export NXF_VER=26.04.6
  4. docs/03-run-demo.md へ
```

### 方法 B: Bicep を直接呼び出す (CI/CD 向け)

```bash
cd research-fields/life-pharma-science/04-transcriptomics-rnaseq/infra

# パラメータテンプレートをコピーして値を埋める
cp parameters.example.json parameters.json
# エディタで parameters.json を編集

RG=rg-spread1000-rnaseq-$(whoami)
LOCATION=japaneast

az group create --name "$RG" --location "$LOCATION" \
  --tags project=spread1000 field=life-pharma-science scenario=rnaseq-nextflow

# what-if で差分確認 (実行しない)
az deployment group what-if \
  --resource-group "$RG" \
  --template-file main.bicep \
  --parameters @parameters.json

# 本番デプロイ
az deployment group create \
  --resource-group "$RG" \
  --template-file main.bicep \
  --parameters @parameters.json
```

## デプロイ後の検証

### Batch アカウントの quota 確認

```bash
BATCH_ACCOUNT=$(az batch account list --resource-group "$RG" --query "[0].name" -o tsv)

az batch account show \
  --resource-group "$RG" \
  --name "$BATCH_ACCOUNT" \
  --query '{
    dedicatedCoreQuota:dedicatedCoreQuota,
    lowPriorityCoreQuota:lowPriorityCoreQuota,
    familyEnforced:dedicatedCoreQuotaPerVMFamilyEnforced,
    perFamily:dedicatedCoreQuotaPerVMFamily,
    poolQuota:poolQuota,
    activeJobAndJobScheduleQuota:activeJobAndJobScheduleQuota
  }' -o jsonc
```

- **dedicatedCoreQuota**: 総 dedicated core 数。シナリオ試算では デモ 16 / 本番 96 が目安 (auto-pool が複数プールを作るケースがあるため余裕を持たせる)
- **lowPriorityCoreQuota**: Spot 使用時に必要 (本番 Spot なら 96 以上を目安)
- **familyEnforced=true** の場合: `perFamily` に **`Standard Ddsv5 Family` と `Standard Edsv5 Family` の両方**が十分な core 数で載っていること。片方が 0 だとその工程で `AllocationTimedOut` になる
- **poolQuota**: 最低 1 (auto-pool が同時に複数生成されるケースを見越すなら 5〜10 を推奨)
- **activeJobAndJobScheduleQuota**: 最低 10 (nf-azure は Nextflow セッションごとに 1 個の Batch job を作成するため、通常は 10 で足りますが、同時に複数のパイプラインを回す予定があれば 20〜50 を要求)

不足時は Azure Portal → Batch アカウント → **クォータ** から要求 (1-3 営業日で承認、無料)。

### Blob コンテナと RBAC の確認

```bash
STORAGE=$(az storage account list --resource-group "$RG" --query "[0].name" -o tsv)
CONTROLLER_MI_ID=$(az vm show --resource-group "$RG" --name vm-nf-controller \
  --query identity.principalId -o tsv)

# Controller VM の system-assigned MI に Storage Blob Data Contributor が付与されているか
az role assignment list \
  --assignee "$CONTROLLER_MI_ID" \
  --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RG/providers/Microsoft.Storage/storageAccounts/$STORAGE" \
  --query '[].roleDefinitionName' -o tsv
# → Storage Blob Data Contributor

# Batch account 側にも Azure Batch Data Contributor が付与されているか
BATCH_ACCOUNT=$(az batch account list --resource-group "$RG" --query "[0].name" -o tsv)
az role assignment list \
  --assignee "$CONTROLLER_MI_ID" \
  --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RG/providers/Microsoft.Batch/batchAccounts/$BATCH_ACCOUNT" \
  --query '[].roleDefinitionName' -o tsv
# → Azure Batch Data Contributor
```

### Controller VM へ SSH

```bash
VM_IP=$(az vm show --resource-group "$RG" --name vm-nf-controller \
  --show-details --query publicIps -o tsv)

ssh -o StrictHostKeyChecking=accept-new azureuser@"$VM_IP"
```

Controller VM 上で:

```bash
# Nextflow + Java + jq をインストール
curl -sSL https://raw.githubusercontent.com/nahisaho/spread1000-azure-quickstart/main/research-fields/life-pharma-science/04-transcriptomics-rnaseq/scripts/install-nextflow.sh | bash

# バージョン確認
nextflow -version   # → 26.04.6 が表示されること
java -version       # → 17 以上
```

## チェックリスト

- [ ] `az deployment group show` で `provisioningState=Succeeded`
- [ ] Batch アカウントの dedicated core quota が要件を満たす
- [ ] Blob コンテナ `omics` が Blob Data Contributor 権限で見える
- [ ] Controller VM に SSH できる
- [ ] Controller VM で `nextflow -version` が 26.04.6

## 次のステップ

→ [03-run-demo.md](03-run-demo.md) — nf-core/rnaseq test プロファイルで動作確認
