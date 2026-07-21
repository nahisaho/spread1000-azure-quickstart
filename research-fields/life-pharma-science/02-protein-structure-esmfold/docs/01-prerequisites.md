# 01 — 前提条件と権限

所要 5 分。ここでは Azure サブスクリプションと権限、必要なローカルツールを確認します。

## 1. Azure サブスクリプション

- **アカウント**: 個人 or 所属機関の Microsoft Entra ID アカウント
- **サブスクリプション**: SPReAD-1000 で配布される Azure サブスクリプション、または科研費・自費のいずれか
- サブスクリプションで **課金が有効** になっていること

## 2. RBAC ロール（必要な権限）

| 実行する操作 | 必要ロール |
|---|---|
| リソースグループ作成 | `Owner` または `Contributor` (サブスクリプション スコープ) |
| Workspace および依存リソース作成 | `Contributor` (リソースグループ スコープで OK) |
| Compute Instance にサインインし Jupyter を使う | 作成時に **assignedUser** としてあなた自身を指定する必要あり（deploy.sh はサインイン中の自分に自動割当） |
| **アイドル自動停止のためのロール割当**（推奨） | `Owner` または `User Access Administrator` （Workspace スコープ）が必要。`Contributor` のみの場合はスキップし手動停止運用に |

> [!NOTE]
> **`AzureML Compute Operator` だけでは足りません**。個人サブスクリプション初期状態（`Owner`）であればすべて満たされます。

**確認コマンド:**

```bash
MY_OID=$(az ad signed-in-user show --query id -o tsv)
az role assignment list --assignee "${MY_OID}" \
  --scope /subscriptions/$(az account show --query id -o tsv) \
  --include-inherited --include-groups \
  --query "[].roleDefinitionName" -o tsv
```

## 3. リソースプロバイダーの登録

```bash
for RP in Microsoft.MachineLearningServices Microsoft.Storage Microsoft.KeyVault \
          Microsoft.Insights Microsoft.ContainerRegistry Microsoft.Network \
          Microsoft.Compute; do
  echo "→ ${RP}"
  az provider register --namespace "${RP}"
done

az provider list --query "[?namespace=='Microsoft.MachineLearningServices'].{Namespace:namespace, State:registrationState}" -o table
```

## 4. GPU クォータ（重要）

新規サブスクリプションでは **GPU クォータが 0** に設定されています。

**Azure ML クォータ確認**（Workspace 作成前でも実行可能）：

```bash
SUB_ID=$(az account show --query id -o tsv)
LOC=japaneast

az rest --method get \
  --url "https://management.azure.com/subscriptions/${SUB_ID}/providers/Microsoft.MachineLearningServices/locations/${LOC}/usages?api-version=2024-04-01" \
  --query "value[?contains(name.value, 'T4') || contains(name.value, 'A100') || contains(name.value, 'H100')].{Name:name.localizedValue, Current:currentValue, Limit:limit}" \
  -o table
```

**利用可能な GPU SKU 一覧**：

```bash
az rest --method get \
  --url "https://management.azure.com/subscriptions/${SUB_ID}/providers/Microsoft.MachineLearningServices/locations/${LOC}/vmSizes?api-version=2024-04-01" \
  --query "value[?gpus > \`0\`].{Name:name, GPUs:gpus, vCPU:vCPUs, RAM_GB:memoryGB}" \
  -o table
```

### クォータ増加リクエスト（Azure Portal 推奨）

1. [Azure Portal](https://portal.azure.com) → **サブスクリプション** → 該当サブスクリプションを開く
2. 左メニュー **使用量 + クォータ**
3. **プロバイダー**: `Machine Learning` に切り替え
4. 検索窓に `T4` と入力 → `Standard NCASv3_T4 Family Cluster Dedicated vCPUs`（japaneast）行の 🖉 アイコン
5. **新しい上限** に `8` を入力（T4 × 1 台分＝8 vCPU）→ **送信**

> [!TIP]
> ESMFold は **T4 (16 GB) で 300〜600 aa の予測が可能** です。まずは T4 (`NCASv3_T4`) を **8 vCPU 分** 申請してください。長鎖（>700 aa）や高速バッチ推論が必要なら A100 (`NCadsA100_v4`) を **24 vCPU 分** 追加申請。

## 5. ローカル PC のツール

| ツール | バージョン | 用途 |
|---|---|---|
| **Azure CLI** | 2.67 以上 | Azure リソース操作 |
| **Azure CLI ml 拡張** | 最新 (`az extension add --name ml`) | Azure ML 操作 |
| **Git** | 2.30 以上 | このリポジトリ取得 |
| **VS Code**（推奨） | 最新 | Jupyter / リモート開発 |

```bash
az version
az extension show --name ml --query version -o tsv
git --version
```

## 6. サインイン

```bash
az login
az account list --query "[].{Name:name, Id:id}" -o table
az account set --subscription "<Subscription Name または ID>"
az account show --query "{name:name, id:id, tenant:tenantId}" -o table
```

## 完了チェック

- [ ] `az account show` で自分のサブスクリプションが表示される
- [ ] リソースグループ作成権限（`Owner` または `Contributor`）がある
- [ ] `Microsoft.MachineLearningServices` を含む必要プロバイダーが **Registered**
- [ ] `japaneast` の Azure ML GPU クォータ（`NCASv3_T4` または相当）が **8 以上**
- [ ] Azure CLI 2.67 以上、ml 拡張、Git インストール済み

**次**: [02-provision-aml.md](02-provision-aml.md) — Azure ML ワークスペースと GPU コンピュートを作成
