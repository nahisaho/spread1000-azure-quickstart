# 02 — Azure ML Workspace と GPU Compute の作成

所要 10〜15 分。ここでは Bicep（推奨）で Workspace と Compute Instance を作成します。

## 方法 A: `infra/deploy.sh` でワンクリック（推奨）

```bash
cd quickstarts/molecular-gnn/esmfold-structure-prediction/infra

# 環境変数で上書き（省略時はスクリプト内のデフォルト値を使用）
export YOUR_NAME=taro                        # 半角小文字英数字 3-8 文字
export OWNER_EMAIL=taro@example.ac.jp        # 課金追跡タグ
export LOCATION=japaneast                    # 既定
export COMPUTE_SIZE=Standard_NC8as_T4_v3     # 低コスト
# export COMPUTE_SIZE=Standard_NC24ads_A100_v4  # 長鎖・バッチ用

bash deploy.sh
```

`deploy.sh` は以下を順に実行し、**完了時に RG / WS / CI 名を表示** します（クリーンアップで使うのでメモしてください）：
1. リソースプロバイダー登録（並行キック + 必須 3 プロバイダーのポーリング、5 分デッドライン）
2. リソースグループ作成
3. Azure ML Workspace + 依存リソース（Storage/KV/AppInsights/ACR）作成（5〜8 分）
4. 依存リソースへのタグ伝播（プロジェクト単位でコスト集計するため）
5. Compute Instance（GPU 付き）作成（3〜5 分）

**assignedUser は `az ad signed-in-user show` から自動取得** されます。CI/CD で回す場合は Object ID + Tenant ID を明示指定してください（[main.bicep](../infra/main.bicep) の `assignedUserObjectId` / `assignedUserTenantId` パラメータ）。

## 方法 B: Bicep を直接 az deployment で

```bash
cd quickstarts/molecular-gnn/esmfold-structure-prediction/infra

MY_OID=$(az ad signed-in-user show --query id -o tsv)
MY_TID=$(az account show --query tenantId -o tsv)

az group create --name rg-esmfold-jp --location japaneast \
  --tags project=spread1000 field=life-pharma-science category=molecular-gnn \
         scenario=esmfold-structure-prediction owner=taro@example.ac.jp

# パラメータをコマンドラインで直接指定（parameters.example.json は編集不要）
az deployment group create \
  --resource-group rg-esmfold-jp \
  --template-file main.bicep \
  --parameters \
      yourName=taro \
      ownerEmail=taro@example.ac.jp \
      assignedUserObjectId="${MY_OID}" \
      assignedUserTenantId="${MY_TID}" \
      computeSize=Standard_NC8as_T4_v3
```

もしくは `parameters.example.json` を **jq で** 書き換えてから使う：

```bash
cp parameters.example.json parameters.json
jq --arg oid "${MY_OID}" --arg tid "${MY_TID}" \
   '.parameters.assignedUserObjectId.value = $oid |
    .parameters.assignedUserTenantId.value = $tid' \
   parameters.example.json > parameters.json

az deployment group create \
  --resource-group rg-esmfold-jp \
  --template-file main.bicep \
  --parameters @parameters.json
```

## 作成されるリソース

| リソース | 名前規則 | 用途 |
|---|---|---|
| Azure ML Workspace | `mlw-esmfold-<suffix>` | 実験・モデル管理の中枢 |
| Storage Account | `stesmfold<suffix>` | データセット・ノートブック保存 |
| Key Vault | `kv-esmfold-<suffix>` | 接続情報・シークレット |
| App Insights | `appi-esmfold-<suffix>` | メトリクス・ログ |
| Container Registry | `cresmfold<suffix>` | カスタム環境イメージ |
| Compute Instance | `ci-esmfold-<user>` | GPU 付き Jupyter/VS Code 実行環境 |

`<suffix>` は `uniqueString(subscription().id, resourceGroup().name)` で 5 文字生成されます（衝突回避）。

## 動作確認

`deploy.sh` の最後に出力された `RG=... / WS=... / CI=...` の値を使います。

```bash
# 上記出力から控えた値を貼り付け
RG=<deploy.sh が出力した RG>
WS=<deploy.sh が出力した WS>
CI=<deploy.sh が出力した CI>

# Workspace 一覧
az ml workspace list --resource-group "${RG}" -o table

# Compute Instance の状態
az ml compute show \
  --name "${CI}" \
  --resource-group "${RG}" \
  --workspace-name "${WS}" \
  --query "{name:name, state:state, size:size, idle_time_before_shutdown_minutes:idle_time_before_shutdown_minutes}" \
  -o table
```

`state` が **Running**、`size` が指定した GPU SKU になっていれば成功です。

## Compute Instance の自動停止設定を確認

`deploy.sh` / Bicep は `idle_time_before_shutdown_minutes = 30`（30 分アイドルで停止）を既定で設定します。ただし現在の Bicep API バージョン（2024-04-01）では `idleTimeBeforeShutdown` の型スキーマが未整備で、`az bicep build` が BCP037 警告を出すことがあります。ARM 側では受け付けられるため実効的には動作しますが、以下で必ず確認してください：

```bash
az ml compute show \
  --name "${CI}" \
  --resource-group "${RG}" \
  --workspace-name "${WS}" \
  --query "idle_time_before_shutdown_minutes" -o tsv
```

**空欄または `0` の場合は Azure ML Studio から手動設定してください**：Azure ML Studio → **コンピューティング** → 該当 CI 選択 → **アクション** → **アイドル シャットダウンの編集** で 30 分を設定。

> [!IMPORTANT]
> **Azure ML のアイドル シャットダウンは Workspace のマネージド ID がその Workspace 上の Compute リソースを操作できる権限を必要とします。** この Bicep はマネージド ID の有効化のみを行い、ロール割当は行いません。手動で以下のロール割当を追加してください。
>
> **⚠ このコマンド自体を実行するには `Owner` または `User Access Administrator` が必要です**（`Contributor` では権限不足で `AuthorizationFailed` になります）。所属機関の管理者に依頼するか、以下のいずれかで対応してください：
>
> **選択肢 1: Owner 権限がある場合**
>
> ```bash
> WS_MI_OID=$(az ml workspace show --name "${WS}" --resource-group "${RG}" \
>   --query identity.principalId -o tsv)
> WS_ID=$(az ml workspace show --name "${WS}" --resource-group "${RG}" --query id -o tsv)
> az role assignment create \
>   --assignee-object-id "${WS_MI_OID}" \
>   --assignee-principal-type ServicePrincipal \
>   --role "Contributor" \
>   --scope "${WS_ID}"
> ```
>
> **選択肢 2: Contributor しか持たない場合**
>
> ロール割当をスキップし、代わりに手動で必ず停止する運用にします。作業終了時に必ず：
>
> ```bash
> az ml compute stop --name "${CI}" --resource-group "${RG}" --workspace-name "${WS}"
> ```
>
> または Azure ML Studio → **コンピューティング** → 該当 CI → **停止**。停止し忘れると T4 で **月 ¥110,000（24 時間稼働）** の課金が発生します。

## 完了チェック

- [ ] `az ml workspace list` に Workspace が表示される
- [ ] `az ml compute show` で `state=Running` かつ GPU SKU が正しい
- [ ] `idle_time_before_shutdown_minutes` が 30 に設定されている

**次**: [03-run-esmfold.md](03-run-esmfold.md) — ESMFold 環境構築と推論実行
