# 01. 前提条件

## 1. Azure サブスクリプションと権限

- 課金アクティブな Azure サブスクリプション (`az account show` で確認)
- **サブスクリプション スコープ**で以下いずれかのロール:
  - `Owner`
  - `Contributor` + `User Access Administrator` (Bicep で RBAC 割り当てを行うため両方必要)

```bash
# 自分のロール確認
az role assignment list \
  --assignee "$(az ad signed-in-user show --query id -o tsv)" \
  --scope "/subscriptions/$(az account show --query id -o tsv)" \
  --query '[].roleDefinitionName' -o tsv
```

## 2. ローカル ツール

| ツール | バージョン | インストール |
|---|---|---|
| Azure CLI | 2.60+ | https://learn.microsoft.com/cli/azure/install-azure-cli |
| bash / WSL | — | Windows は WSL2 (Ubuntu 24.04) 推奨 |
| jq | 1.6+ | `sudo apt install jq` |
| git | — | `sudo apt install git` |

Nextflow / Java は **Controller VM 上に** インストールします (ローカルには不要)。理由: Cloud Shell は 20 分でタイムアウトし長時間ワークフローを実行できないため。

## 3. リソースプロバイダー登録

初回のみ以下のプロバイダーを登録します (10 分以内に完了):

```bash
az account set --subscription "<YOUR-SUBSCRIPTION-ID>"

for RP in Microsoft.Batch Microsoft.Storage Microsoft.Compute Microsoft.Network Microsoft.ManagedIdentity; do
  az provider register --namespace "$RP"
done

# 登録完了確認 (すべて Registered になるまで待つ)
az provider list --query "[?namespace=='Microsoft.Batch' || namespace=='Microsoft.Storage' || namespace=='Microsoft.Compute' || namespace=='Microsoft.Network' || namespace=='Microsoft.ManagedIdentity'].{ns:namespace,state:registrationState}" -o table
```

## 4. Batch アカウントの Core Quota 確認

**新規サブスクリプションでは Batch の dedicated core quota が 0 の場合があります**。以下でリージョン別に確認:

```bash
LOCATION=japaneast

# 現在サブスクリプションで Batch account が既にあれば表示
az batch account list --query "[?location=='${LOCATION}'].{name:name,rg:resourceGroup}" -o table

# 参考: そのリージョンの VM ファミリ別 quota (Batch はこれとは別枠だが目安)
az vm list-usage --location "${LOCATION}" \
  --query "[?contains(name.value,'standardDDSv5Family') || contains(name.value,'standardEDSv5Family')]" -o table
```

Batch アカウント作成後の quota 確認は `docs/02-provision-batch.md` の末尾で行います。

### Quota が不足していた場合

**Batch service mode では総 dedicated core quota に加え、VM ファミリ別 quota が個別に強制**されます (`dedicatedCoreQuotaPerVMFamilyEnforced=true` の場合)。本テンプレートは `machineType='Standard_D*ds_v5,Standard_E*ds_v5'` を使うため、**Ddsv5 と Edsv5 の両ファミリの quota が必要**です。

代表的な要件 (シナリオ試算):

| 用途 | 必要 core (dedicated) | 主な VM ファミリ |
|---|---:|---|
| デモ (D8ds_v5 × 2) | 16 | Standard Ddsv5 |
| 本番 (E16ds_v5 × 6) | 96 | Standard Edsv5 |

nf-azure の auto-pool モードでは工程 (STAR / Salmon / QC など) ごとに別プールが作られることがあり、`maxVmCount=10` は **プール単位** の上限であるため、実際は表以上の core が一時的に必要になり得ます。まず 96 core で申請し、実行後に Batch metrics で実消費を確認して増減してください。

Batch account 側の quota 確認は Bicep デプロイ後に `docs/02-provision-batch.md` §「Batch アカウントの quota 確認」で行います。不足時:

1. Azure Portal → 対象 Batch アカウント → **クォータ** → **クォータの要求**
2. 用途に「SPReAD-1000 grant, nf-core/rnaseq for academic research」と記載
3. Ddsv5 と Edsv5 それぞれのファミリを別行で要求 (Family 別 quota が有効な場合)
4. 通常 **1〜3 営業日**で承認されます (無料)

参考: [Batch service quotas](https://learn.microsoft.com/en-us/azure/batch/batch-quota-limit)

## 5. Storage 容量の見積り

デモは 30 GB で足ります。本番運用の目安:

| 項目 | サイズ (Human 6 samples) |
|---:|---|
| raw FASTQ (paired, gzipped) | 30 GB |
| Reference (FASTA + GTF + STAR index) | 40 GB |
| Nextflow work dir (中間) | 200 GB |
| Results (BAM 除く MultiQC + counts) | 5〜20 GB |
| **合計 (実行中ピーク)** | **約 270 GB** |

## 6. デモが完了することのチェックリスト

以下がすべて Yes になれば `docs/02-provision-batch.md` に進めます:

- [ ] `az account show` でサブスクリプションが確認できる
- [ ] Owner または (Contributor + User Access Administrator) を保持
- [ ] `az version` が 2.60 以上
- [ ] `jq --version` が動く
- [ ] 上記 5 プロバイダーがすべて `Registered`
- [ ] 対象リージョン (Japan East 推奨) を決めた

## 次のステップ

→ [02-provision-batch.md](02-provision-batch.md) — Bicep で Batch + Storage + Controller VM をデプロイ
