# 05 — クリーンアップ（課金停止）

所要 5 分。目的別に手順を選んでください。

## 課金される主なリソース

| リソース | 課金モデル | 停止方法 |
|---|---|---|
| **Compute Instance (GPU VM)** | **停止** | 起動中のみ。T4 なら 約 **¥160/h**、A100 なら 約 **¥860/h** |
| Compute Instance の OS ディスク | **削除** | 停止中でも Premium SSD 120GB ≒ ¥2,500/月 |
| 静的パブリック IP | **削除** | 停止中でも ≒ ¥400/月 |
| Storage / Key Vault / App Insights / ACR | **削除** | 合計 月数百〜千円 |
| Workspace 本体 | 無料 | 削除しても課金には影響しない |

> [!IMPORTANT]
> **Compute Instance を停止しても、OS ディスク・静的 IP・依存リソースの課金は残ります。** 数週間〜1 か月使わない場合は Compute Instance の **削除**、プロジェクト完了時は **リソースグループごと削除** を選んでください。

## 対象リソースの特定（タグベース）

`deploy.sh` は全リソースに `scenario=esmfold-structure-prediction` タグを付与しています。

> [!IMPORTANT]
> **同じサブスクリプションを複数人で使っている場合、他のユーザーの ESMFold RG が候補に出ることがあります。**必ず `owner` タグと目視で自分の RG を確認してから削除してください。

```bash
# タグで候補 RG を列挙 (owner タグも表示)
az group list \
  --query "[?tags.scenario=='esmfold-structure-prediction' && tags.project=='spread1000'].{name:name, owner:tags.owner, location:location}" \
  -o table
```

出力例：

```
Name                                            Owner                Location
----------------------------------------------  -------------------  ----------
rg-spread1000-esmfold-structure-prediction-taro taro@example.ac.jp   japaneast
rg-spread1000-esmfold-structure-prediction-hana hana@example.ac.jp   japaneast   ← 他人の RG
```

**必ず自分の RG 名を明示的に指定してください**：

```bash
RG=rg-spread1000-esmfold-structure-prediction-taro   # ← 自分の RG 名に置き換え

# 一致するか確認
az group show --name "${RG}" \
  --query "{name:name, owner:tags.owner, scenario:tags.scenario}" -o table

# Workspace と Compute Instance を取得
WS=$(az ml workspace list --resource-group "${RG}" --query "[0].name" -o tsv)
CI=$(az ml compute list --resource-group "${RG}" --workspace-name "${WS}" \
  --query "[?type=='computeinstance'].name" -o tsv | head -1)
echo "WS=${WS}  CI=${CI}"
```

## 選択肢

### A. 一時停止（当日中にまた使う）

Compute Instance の GPU/CPU 課金だけ止めます。数分で再起動できます。**ディスク・IP 課金は残ります。**

```bash
az ml compute stop \
  --name "${CI}" \
  --resource-group "${RG}" \
  --workspace-name "${WS}"
```

再開：

```bash
az ml compute start \
  --name "${CI}" \
  --resource-group "${RG}" \
  --workspace-name "${WS}"
```

### B. Compute Instance を削除（1 週間〜1 か月使わない）

Workspace と HuggingFace キャッシュ（Storage 上）は残し、GPU VM だけ削除します。

> [!WARNING]
> **Compute Instance を削除すると OS ディスクごと消えます。** conda 環境と `output/` の推論結果は失われます。次回は `setup-esmfold.sh` を再実行し、conda 環境構築（10 分程度）が必要になります。
>
> **HuggingFace 重みは `~/cloudfiles/hf_cache` （Workspace 共有 Storage）に保存されているため再ダウンロード不要** です（setup-esmfold.sh がこの配置を行います）。
>
> **削除前に必ず結果を保存**（Compute Instance 上の Jupyter ターミナルで実行）:
>
> ```bash
> mkdir -p ~/cloudfiles/code/Users/$(whoami)/esmfold-archive
> cp -r ~/spread1000-azure-quickstart/research-fields/life-pharma-science/02-protein-structure-esmfold/output \
>    ~/cloudfiles/code/Users/$(whoami)/esmfold-archive/
> ```

```bash
az ml compute delete \
  --name "${CI}" \
  --resource-group "${RG}" \
  --workspace-name "${WS}" \
  --yes
```

これで OS ディスクと静的 IP の課金も止まります。**ただし Storage / KV / ACR / App Insights は残り、合計月数百〜千円程度の課金は続きます。**

### C. すべて削除（プロジェクト完了）

> [!WARNING]
> **これはリソースグループ内の全リソースを削除します。取り消せません。** 実行前に必要な結果を Blob Storage や自分の PC にコピーしてください。

```bash
# 上記「対象リソースの特定」で取得した RG を使う

# 1. リソースグループ内の Key Vault 名を先に控える (削除後にパージするため)
KV_NAMES=($(az keyvault list --resource-group "${RG}" --query "[].name" -o tsv))
echo "対象 Key Vault: ${KV_NAMES[@]:-(なし)}"

# 2. リソースグループごと削除 (完了まで 5-15 分)
az group delete --name "${RG}" --yes

# 3. Key Vault はソフト削除保護 (7 日) が残る。放置しても課金は発生しない
for KV in "${KV_NAMES[@]}"; do
  read -rp "Key Vault '${KV}' をパージしますか？ [y/N] " ANS
  if [[ "${ANS}" == "y" ]]; then
    az keyvault purge --name "${KV}" --location japaneast
  fi
done
```

> [!CAUTION]
> **`az keyvault list-deleted` を検索して自動パージしてはいけません。** 別プロジェクト・別ユーザーの Vault を巻き込む事故が発生します。必ずリソースグループから取得した名前のみをパージ対象にし、対話確認を挟んでください。

## 課金の確認

Azure Portal → **コスト管理 + 請求** → **コスト分析** で、`tags: scenario=esmfold-structure-prediction` によるフィルタリングが可能です（`deploy.sh` が付与するタグ）。

CLI で確認したい場合は Cost Management REST API を `az rest` で直接叩きます：

```bash
SUB_ID=$(az account show --query id -o tsv)
FROM=$(date -d '30 days ago' -u +%Y-%m-%dT00:00:00Z)
TO=$(date -u +%Y-%m-%dT00:00:00Z)

az rest --method post \
  --url "https://management.azure.com/subscriptions/${SUB_ID}/providers/Microsoft.CostManagement/query?api-version=2023-11-01" \
  --body "{
    \"type\": \"Usage\",
    \"timeframe\": \"Custom\",
    \"timePeriod\": {\"from\": \"${FROM}\", \"to\": \"${TO}\"},
    \"dataset\": {
      \"granularity\": \"Daily\",
      \"aggregation\": {\"totalCost\": {\"name\": \"Cost\", \"function\": \"Sum\"}},
      \"grouping\": [{\"type\": \"Dimension\", \"name\": \"ResourceGroup\"}]
    }
  }"
```

## 完了チェック

- [ ] Compute Instance が **停止** または **削除** 済み
- [ ] （プロジェクト完了時のみ）リソースグループごと削除済み
- [ ] （必要なら）Key Vault のパージが完了
- [ ] Azure Portal の **コスト分析** で当該 RG の当日課金がゼロ／低額になっている

**戻る**: [../README.md](../README.md)
