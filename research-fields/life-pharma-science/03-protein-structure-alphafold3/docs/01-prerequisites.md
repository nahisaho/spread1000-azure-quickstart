# 01 — 前提条件と権限

所要 10 分（重み申請は数日前に開始）。ここでは Azure サブスクリプション、権限、必要なローカルツールに加え、
**AF3 モデル重みの申請**を先行で開始します。

## 1. ⚠ 最初にやること: AF3 モデル重みの申請

AF3 の重み `af3.bin` は **Google のフォーム申請** が必要です。承認まで **2〜3 営業日**。
Azure リソース作成の **数日前** に申請しておいてください。

1. 公式リポジトリの [Obtaining Model Parameters](https://github.com/google-deepmind/alphafold3#obtaining-model-parameters) を開く
2. リンクされた Google フォーム <https://forms.gle/svvpY4u2jsHEwWYS6> にアクセス
3. 以下の点を正確に記入:
   - **所属機関**: 大学・非営利研究機関の正式名称（英語）
   - **利用目的**: SPReAD-1000 の研究課題名（例: "Structural study of ..."）
   - **eligible non-commercial research** であることを明記
   - **個人利用** か **機関代表者としての利用** かを正しく選択
4. 承認メール受領後、リンクから `af3.bin` (約 1 GB) をローカルにダウンロード

> [!IMPORTANT]
> **`af3.bin` は絶対に GitHub / Blob 公開 / Docker イメージ / Slack 等に置かないでください。**
> Terms of Use により、承認組織外への再配布は禁止されています。
> 個人承認の場合は同僚とも共有できません。

> [!NOTE]
> **企業共同研究や委託研究に AF3 を使う予定がある場合は、必ず所属機関の法務レビューを受けてください。**
> 商用利用は禁止されており、SPReAD-1000 単独プロジェクトでも共同研究者の所属によっては制限がかかる可能性があります。

---

## 2. Azure サブスクリプション

- **アカウント**: 個人 or 所属機関の Microsoft Entra ID アカウント
- **サブスクリプション**: SPReAD-1000 で配布される Azure サブスクリプション、または科研費・自費のいずれか
- サブスクリプションで **課金が有効** になっていること

## 3. RBAC ロール（必要な権限）

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

## 4. リソースプロバイダーの登録

```bash
for RP in Microsoft.MachineLearningServices Microsoft.Storage Microsoft.KeyVault \
          Microsoft.Insights Microsoft.ContainerRegistry Microsoft.Network \
          Microsoft.Compute; do
  echo "→ ${RP}"
  az provider register --namespace "${RP}"
done

az provider list --query "[?namespace=='Microsoft.MachineLearningServices'].{Namespace:namespace, State:registrationState}" -o table
```

## 5. GPU クォータ（重要）

AF3 は **H100 80GB または A100 80GB クラスの GPU が実質必須**です。
新規サブスクリプションでは **GPU クォータが 0** に設定されています。

**Azure ML クォータ確認**（Workspace 作成前でも実行可能）：

```bash
SUB_ID=$(az account show --query id -o tsv)
LOC=japaneast

az rest --method get \
  --url "https://management.azure.com/subscriptions/${SUB_ID}/providers/Microsoft.MachineLearningServices/locations/${LOC}/usages?api-version=2024-04-01" \
  --query "value[?contains(name.value, 'H100') || contains(name.value, 'A100')].{Name:name.localizedValue, Current:currentValue, Limit:limit}" \
  -o table
```

**利用可能な GPU SKU の確認**：

```bash
az rest --method get \
  --url "https://management.azure.com/subscriptions/${SUB_ID}/providers/Microsoft.MachineLearningServices/locations/${LOC}/vmSizes?api-version=2024-04-01" \
  --query "value[?gpus > \`0\` && (contains(name, 'H100') || contains(name, 'A100'))].{Name:name, GPUs:gpus, vCPU:vCPUs, RAM_GB:memoryGB}" \
  -o table
```

### クォータ増加リクエスト（Azure Portal 推奨）

1. [Azure Portal](https://portal.azure.com) → **サブスクリプション** → 該当サブスクリプションを開く
2. 左メニュー **使用量 + クォータ**
3. **プロバイダー**: `Machine Learning` に切り替え
4. 検索窓に `H100` と入力 → 該当行の 🖉 アイコン
5. **新しい上限** を入力 → **送信**

**申請目安**:

| 用途 | SKU | 申請 vCPU |
|------|-----|-----------|
| 推奨（H100, 最速） | `Standard NCadsH100v5 Family Cluster Dedicated vCPUs` | **40** (H100 × 1 台) |
| フォールバック (A100 80GB) | `Standard NCADSA100v4 Family Cluster Dedicated vCPUs` | **24** (A100 × 1 台) |

> [!TIP]
> 両方申請しておくことをお勧めします。承認は Azure 側の判断で数時間〜数営業日かかります。
> クォータが承認されても、実際の物理容量が不足していると起動時にエラーになる場合があります。
> エラーが出た場合はフォールバック SKU またはリージョン (`eastus2`, `westeurope`) を試してください。

### capacity 事前確認（クォータ承認後）

```bash
az vm list-skus --location "${LOC}" --resource-type virtualMachines \
  --query "[?name=='Standard_NC40ads_H100_v5' || name=='Standard_NC24ads_A100_v4'].{Name:name, Restrictions:restrictions[].reasonCode}" \
  -o table
```

`Restrictions` 列が空なら利用可能。`NotAvailableForSubscription` 等が出ていたらリージョン変更を検討してください。

## 6. ローカル PC のツール

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

## 7. サインイン

```bash
az login
az account list --query "[].{Name:name, Id:id}" -o table
az account set --subscription "<Subscription Name または ID>"
az account show --query "{name:name, id:id, tenant:tenantId}" -o table
```

## 完了チェック

- [ ] AF3 重みの Google フォーム申請を **送信済み**（数日前推奨）
- [ ] 承認メール受領・`af3.bin` を **ローカルに保管済み**（ワークショップ当日までに）
- [ ] `az account show` で自分のサブスクリプションが表示される
- [ ] リソースグループ作成権限（`Owner` または `Contributor`）がある
- [ ] `Microsoft.MachineLearningServices` を含む必要プロバイダーが **Registered**
- [ ] `japaneast` の H100 または A100 クォータが **申請 vCPU 数以上**
- [ ] `az vm list-skus` で対象 SKU に `Restrictions` が無い（capacity あり）
- [ ] Azure CLI 2.67 以上、ml 拡張、Git インストール済み

**次**: [02-provision-aml.md](02-provision-aml.md) — Azure ML ワークスペースと H100 コンピュートを作成
