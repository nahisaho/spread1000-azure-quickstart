# 02 — Azure ML ワークスペースと GPU コンピュートを作成

所要 15 分（うち待機 8〜12 分）。ここでは Azure ML の Workspace と、GPU 付きの Compute Instance を作成します。

3 通りの方法から選べます。**初めての方は方法 A** を推奨します。

- [方法 A: Azure CLI スクリプト（最速）](#方法-a-azure-cli-スクリプト最速)
- [方法 B: Bicep（IaC）](#方法-b-bicepiac)
- [方法 C: Azure Portal（GUI）](#方法-c-azure-portalgui)

---

## 方法 A: Azure CLI スクリプト（最速）

### 1. リポジトリを取得

作業 PC で以下を実行：

```bash
git clone https://github.com/nahisaho/spread1000-azure-quickstart.git
cd spread1000-azure-quickstart/research-fields/life-pharma-science/01-molecular-generation-tamgen/infra
```

### 2. `deploy.sh` を編集

エディタで `deploy.sh` を開き、**「変更するのはここだけ」ブロック** の 4 行を書き換えてください。

```bash
YOUR_NAME="taro"                          # ★ 自分のエイリアス
LOCATION="japaneast"                      # そのままで OK
OWNER_EMAIL="taro@example.ac.jp"          # ★ 自分のメール
COMPUTE_SIZE="Standard_NC24ads_A100_v4"   # A100 80GB. 予算重視なら Standard_NC8as_T4_v3
```

### 3. 実行

```bash
chmod +x deploy.sh
./deploy.sh
```

確認プロンプトで `y` → 8〜12 分で完了します。スクリプトは以下を自動実行します：

1. リソースプロバイダー登録（`Microsoft.MachineLearningServices` 他）
2. リソースグループ作成
3. Azure ML Workspace 作成
4. **依存リソース（Storage / KV / App Insights / ACR）にもタグを伝播**（`az ml workspace create` は本体しかタグ付けしないため）
5. GPU Compute Instance 作成（サインイン中の自分に自動割当）

最後に Workspace の URL と、次のステップのコマンドが表示されます。

---

## 方法 B: Bicep（IaC）

再現性重視、CI/CD 展開、チームで運用する場合は Bicep を使います。方法 A と違い、**Compute Instance の担当ユーザー (`assignedUser`) を明示指定する必要があります**（CI/CD の service principal では Jupyter が使えないため）。

### 1. パラメータを準備

```bash
cd research-fields/life-pharma-science/01-molecular-generation-tamgen/infra
cp parameters.example.json parameters.json

# 実際に Jupyter を使うユーザーの Object ID と Tenant ID を取得して parameters.json に埋め込む
MY_OID=$(az ad signed-in-user show --query id -o tsv)
MY_TID=$(az account show --query tenantId -o tsv)

# エディタで parameters.json を編集
#   yourName / ownerEmail / assignedUserObjectId=$MY_OID / assignedUserTenantId=$MY_TID / computeSize
```

### 2. 事前チェック（`--what-if`）

**必ず実行してください。** 何が作られるかを事前に確認できます。

```bash
YOUR_NAME="taro"
LOCATION="japaneast"
RG="rg-spread1000-tamgen-drug-discovery-${YOUR_NAME}"

az group create --name "${RG}" --location "${LOCATION}"

az deployment group what-if \
  --resource-group "${RG}" \
  --template-file main.bicep \
  --parameters @parameters.json
```

### 3. デプロイ

```bash
az deployment group create \
  --resource-group "${RG}" \
  --template-file main.bicep \
  --parameters @parameters.json \
  --name "deploy-tamgen-$(date +%Y%m%d-%H%M)"
```

### 4. アイドル停止設定の検証

`idleTimeBeforeShutdown` は Bicep の型定義には正式登録されていませんが ARM 側でサポートされています。**デプロイ後に必ず設定が反映されたか確認**してください。

```bash
CI=$(az ml compute list -g "${RG}" -w "$(az ml workspace list -g "${RG}" --query '[0].name' -o tsv)" --query "[?type=='ComputeInstance'].name | [0]" -o tsv)
az ml compute show -g "${RG}" -w "$(az ml workspace list -g "${RG}" --query '[0].name' -o tsv)" -n "${CI}" \
  --query "{name:name, idle:idle_time_before_shutdown, size:size}"
```

`idle` が `PT60M` 相当（`60`）でなければ、Studio の GUI から手動で設定してください。

---

## 方法 C: Azure Portal（GUI）

CLI が使えない、まず画面で理解したい方向け。

### 1. Azure ML Workspace 作成

1. [Azure Portal](https://portal.azure.com) → 上部検索窓に `Azure Machine Learning` → **サービス** から選択
2. **+ 作成** → **新しいワークスペース**
3. 入力：
   - **サブスクリプション**: 自分のもの
   - **リソースグループ**: **新規作成** → `rg-spread1000-tamgen-drug-discovery-<yourname>`
   - **リージョン**: **Japan East**
   - **ワークスペース名**: `mlw-tamgen-<yourname>`
4. **タグ** タブで以下を追加：
   | 名前 | 値 |
   |---|---|
   | project | spread1000 |
   | field | life-pharma-science |
   | category | foundation-model-science |
   | scenario | tamgen-drug-discovery |
   | owner | `<自分のメール>` |
5. **確認および作成** → **作成**（5〜8 分待機）

### 2. GPU Compute Instance 作成

1. 作成完了通知の **リソースに移動** をクリック
2. ワークスペースの **スタジオの起動** → 新しいタブで [Azure ML Studio](https://ml.azure.com) が開く
3. 左メニュー **コンピューティング** → **コンピューティング インスタンス** タブ → **+ 新規**
4. 入力：
   - **コンピューティング名**: `ci-tamgen-<yourname>`（リージョン内で一意）
   - **仮想マシンの種類**: **GPU**
   - **仮想マシンのサイズ**: **すべてのオプションから選択** → `Standard_NC24ads_A100_v4`（推奨）または `Standard_NC8as_T4_v3`（低コスト）
5. **次: スケジュール** → **アイドル シャットダウン** を **有効** にし、**60 分** を設定（**課金対策で必須**）
6. **確認および作成** → **作成**（3〜5 分待機）

---

## 完了チェック

Azure ML Studio → **コンピューティング** で以下が **実行中** になっていれば OK。

- [ ] Compute Instance `ci-tamgen-<yourname>-<suffix>` が **実行中** で GPU アイコンが表示されている
- [ ] 依存リソース（Storage / KV / App Insights / ACR）にも `scenario=tamgen-drug-discovery` タグが付いている（Portal → リソースグループ → 各リソース → タグ）

**次**: [03-run-tamgen.md](03-run-tamgen.md) — TamGen をセットアップして推論を実行

