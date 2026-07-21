# 02 — Azure OpenAI のプロビジョニング

Bicep で **Azure OpenAI アカウント** + **gpt-4.1-mini モデルデプロイ** + **Cognitive Services OpenAI User ロール割り当て** を一括作成します。

## 事前確認

[`docs/01-prerequisites.md`](01-prerequisites.md) の Resource Provider 登録と AOAI 利用登録が済んでいることを確認してください。

## パラメータファイルを作成

```bash
cd research-fields/social-science/01-persona-survey-simulation
cp infra/parameters.example.json infra/parameters.json
```

`infra/parameters.json` の中身：

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "accountName":       { "value": "aoai-spread-social-01" },
    "location":          { "value": "japaneast" },
    "deploymentName":    { "value": "survey-gpt41mini" },
    "modelName":         { "value": "gpt-4.1-mini" },
    "modelVersion":      { "value": "2025-04-14" },
    "deploymentCapacity":{ "value": 10 }
  }
}
```

> [!NOTE]
> `accountName` は Azure グローバルで一意である必要があります (小文字英数字 + ハイフン、2-24 文字)。既存名と衝突したら任意の接尾辞を付けてください。**変更した場合は、以下の `AOAI_ACCOUNT_NAME` 環境変数も同じ名前に合わせてください。**

環境変数を先に決めておくと以降のコマンドが簡潔になります：

```bash
export AOAI_RG="spread-social-rg"
export AOAI_ACCOUNT_NAME="aoai-spread-social-01"   # ← parameters.json の accountName と一致させる
export AOAI_DEPLOYMENT_NAME="survey-gpt41mini"     # ← parameters.json の deploymentName と一致させる
```

## デプロイ

```bash
# サブスクリプションを再確認
az account show --query "{name:name, id:id}" -o table

# リソースグループを作成
az group create -n "$AOAI_RG" -l japaneast

# Bicep をデプロイ (現ユーザーに Cognitive Services OpenAI User を付与)
./infra/deploy.sh "$AOAI_RG" infra/parameters.json
```

`deploy.sh` の中身：
- 現ユーザーの Object ID を取得
- `az deployment group create` で Bicep 適用 (3〜5 分)
- 出力: `endpoint`, `deploymentName`, `accountName`

## 環境変数として保存

以降のシミュレーションで使うため：

```bash
export AZURE_OPENAI_ENDPOINT="$(az cognitiveservices account show \
  -g "$AOAI_RG" -n "$AOAI_ACCOUNT_NAME" \
  --query properties.endpoint -o tsv)"
export AZURE_OPENAI_DEPLOYMENT="$AOAI_DEPLOYMENT_NAME"

echo "$AZURE_OPENAI_ENDPOINT"
# https://<accountName>.openai.azure.com/
```

`.env` ファイルに書いておくと `python-dotenv` で自動読み込みできます。`AZURE_OPENAI_LOCATION` と `AZURE_OPENAI_DEPLOYMENT_TYPE` は再現性メタデータに **必須** で、`simulate.py` は未設定だとエラー終了します。実際のデプロイから取得してください：

```bash
AOAI_LOCATION="$(az cognitiveservices account show \
  -g "$AOAI_RG" -n "$AOAI_ACCOUNT_NAME" \
  --query location -o tsv)"

AOAI_DEPLOYMENT_TYPE="$(az cognitiveservices account deployment show \
  -g "$AOAI_RG" -n "$AOAI_ACCOUNT_NAME" \
  --deployment-name "$AOAI_DEPLOYMENT_NAME" \
  --query sku.name -o tsv)"
# 例: Standard / GlobalStandard / DataZoneStandard

cat > .env <<EOF
AOAI_RG=$AOAI_RG
AOAI_ACCOUNT_NAME=$AOAI_ACCOUNT_NAME
AOAI_DEPLOYMENT_NAME=$AOAI_DEPLOYMENT_NAME
AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_DEPLOYMENT=$AZURE_OPENAI_DEPLOYMENT
AZURE_OPENAI_LOCATION=$AOAI_LOCATION
AZURE_OPENAI_DEPLOYMENT_TYPE=$AOAI_DEPLOYMENT_TYPE
EOF
```

> [!WARNING]
> `.env` はコミットしないでください。`.gitignore` に既に含まれています。

## デプロイの確認

```bash
# モデルデプロイ一覧
az cognitiveservices account deployment list \
  -g "$AOAI_RG" -n "$AOAI_ACCOUNT_NAME" -o table

# 動作テスト (AAD トークン取得)
az account get-access-token --resource https://cognitiveservices.azure.com \
  --query accessToken -o tsv | head -c 40; echo
```

## トラブル

- `AuthorizationFailed`: Owner または User Access Administrator が必要 → [`troubleshooting.md`](../troubleshooting.md#deploy-sh-が-authorizationfailed-で止まる)
- `SpecialFeatureOrQuotaIdRequired`: AOAI 未申請 → <https://aka.ms/oai/access>
- モデルバージョン非対応: → [`troubleshooting.md`](../troubleshooting.md#model-gpt-41-mini-version-2025-04-14-is-not-available-in-region-japaneast)

次: [`03-prepare-personas.md`](03-prepare-personas.md)
