# 01 — 前提条件と権限

所要 5 分。ここでは Azure サブスクリプションと権限、必要なローカルツールを確認します。

## 1. Azure サブスクリプション

- **アカウント**: 個人 or 所属機関の Microsoft Entra ID アカウント
- **サブスクリプション**: SPReAD-1000 で配布される Azure サブスクリプション、または科研費・自費のいずれか
- サブスクリプションで **課金が有効** になっていること（無料試用でも可、ただし GPU クォータの確認は下記参照）

## 2. RBAC ロール（必要な権限）

本クイックスタートで必要な権限は以下です。方法（A/B/C）によって異なります。

| 実行する操作 | 必要ロール |
|---|---|
| リソースグループ作成 | `Owner` または `Contributor` (サブスクリプション スコープ) |
| Workspace および依存リソース作成（方法 A/B/C 共通） | `Contributor` (リソースグループ スコープで OK) |
| Compute Instance にサインインし Jupyter を使う | 作成時に **assignedUser** としてあなた自身を指定する必要あり（方法 A はサインイン中の自分に自動割当） |

> [!NOTE]
> **`AzureML Compute Operator` だけでは足りません**（Workspace 本体や Storage 等の作成権限がないため）。個人サブスクリプションの初期状態（`Owner`）であればすべて満たされます。

**確認コマンド:**

```bash
# 自分のオブジェクト ID
MY_OID=$(az ad signed-in-user show --query id -o tsv)

# サブスクリプション スコープの割当 (グループ・継承分も含める)
az role assignment list --assignee "${MY_OID}" \
  --scope /subscriptions/$(az account show --query id -o tsv) \
  --include-inherited --include-groups \
  --query "[].roleDefinitionName" -o tsv
```

## 3. リソースプロバイダーの登録

新規サブスクリプションでは、Microsoft 系リソースプロバイダーが未登録のことがあります。以下を一括登録してください（既に登録済みなら即座に完了）。

```bash
for RP in Microsoft.MachineLearningServices Microsoft.Storage Microsoft.KeyVault \
          Microsoft.Insights Microsoft.ContainerRegistry Microsoft.Network \
          Microsoft.Compute; do
  echo "→ ${RP}"
  az provider register --namespace "${RP}"
done

# ステータス確認 (Registered になっていれば OK)
az provider list --query "[?namespace=='Microsoft.MachineLearningServices'].{Namespace:namespace, State:registrationState}" -o table
```

## 4. GPU クォータ（重要・見落とし多発ポイント）

新規サブスクリプションでは **GPU クォータが 0** に設定されていることが多く、この状態では GPU コンピュートが作成できません。以下を確認してください。

**Azure ML Compute Instance / Compute Cluster のクォータ確認**（VM 一般のクォータとは別枠、Workspace 作成前でも確認可能）：

```bash
SUB_ID=$(az account show --query id -o tsv)
LOC=japaneast

# サブスクリプション×リージョンの ML クォータ (usages API)
az rest --method get \
  --url "https://management.azure.com/subscriptions/${SUB_ID}/providers/Microsoft.MachineLearningServices/locations/${LOC}/usages?api-version=2024-04-01" \
  --query "value[?contains(name.value, 'A100') || contains(name.value, 'T4') || contains(name.value, 'H100')].{Name:name.localizedValue, Current:currentValue, Limit:limit}" \
  -o table
```

**利用可能な GPU SKU をリージョンで確認**（Workspace 作成前でも確認可能）：

```bash
az rest --method get \
  --url "https://management.azure.com/subscriptions/${SUB_ID}/providers/Microsoft.MachineLearningServices/locations/${LOC}/vmSizes?api-version=2024-04-01" \
  --query "value[?gpus > \`0\`].{Name:name, GPUs:gpus, vCPU:vCPUs, RAM_GB:memoryGB}" \
  -o table
```

出力例：

```
Name                                     Current    Limit
---------------------------------------  ---------  -------
Standard NCADSA100v4 Family Cluster ...  0          0
```

`Limit` が `0` の場合は **クォータ増加リクエスト** が必要です。

### クォータ増加リクエスト（Azure Portal 推奨）

CLI 経由の申請は現在エラーが多く、**Portal からの申請が最も確実** です（承認は通常 1〜2 営業日）。

1. [Azure Portal](https://portal.azure.com) → **サブスクリプション** → 該当サブスクリプションを開く
2. 左メニュー **使用量 + クォータ**
3. **プロバイダー**: `Machine Learning` に切り替え（Compute ではありません）
4. 検索窓に `A100` と入力 → `Standard NCADSA100v4 Family Cluster Dedicated vCPUs`（japaneast）行の右端の 🖉 アイコンをクリック
5. **新しい上限** に `24` を入力（A100 × 1 台分＝24 vCPU）→ **送信**

> [!TIP]
> どの GPU SKU を申請するか迷ったら、**まず `NCadsA100_v4` を 24 vCPU 分** 申請してください。TamGen 100M パラメータの推論には十分で、A100 は現在の推奨 SKU です。予算重視なら **T4 (`NCasT4_v3`)** を 8 vCPU 分。

## 5. ローカル PC のツール

作業 PC に以下をインストールしてください（Windows/Mac/Linux 共通）。

| ツール | バージョン | 用途 |
|---|---|---|
| **Azure CLI** | 2.67 以上 | Azure リソース操作 |
| **Azure CLI ml 拡張** | 最新 (`az extension add --name ml`) | Azure ML 操作 |
| **Git** | 2.30 以上 | クイックスタート取得 |
| **VS Code**（推奨） | 最新 | Jupyter 実行 & リモート開発 |

インストール確認：

```bash
az version
az extension show --name ml --query version -o tsv
git --version
```

Azure CLI 未インストールの場合は [公式手順](https://learn.microsoft.com/ja-jp/cli/azure/install-azure-cli) を参照。

## 6. サインイン

```bash
az login
# ブラウザが開くので所属機関アカウントで認証

# 複数サブスクリプションを持っている場合、使いたい方を選択
az account list --query "[].{Name:name, Id:id}" -o table
az account set --subscription "<Subscription Name または ID>"

# 確認
az account show --query "{name:name, id:id, tenant:tenantId}" -o table
```

## 完了チェック

以下がすべて Yes なら次に進めます。

- [ ] `az account show` で自分のサブスクリプションが表示される
- [ ] リソースグループ作成権限（`Owner` または `Contributor`）がある
- [ ] `Microsoft.MachineLearningServices` を含む必要プロバイダーが **Registered**
- [ ] `japaneast` の Azure ML GPU クォータ（`NCadsA100_v4` または相当）が **24 以上**
- [ ] Azure CLI 2.67 以上、ml 拡張、Git インストール済み

**次**: [02-provision-aml.md](02-provision-aml.md) — Azure ML ワークスペースと GPU コンピュートを作成

