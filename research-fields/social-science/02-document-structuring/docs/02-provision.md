# 02 — プロビジョニング

Bicep で **Document Intelligence** + **Azure OpenAI アカウント + gpt-5.4-mini デプロイ** + **RBAC (両方への `Cognitive Services User` / `OpenAI User`)** を一括作成します。

## パラメータファイル

```bash
cd research-fields/social-science/02-document-structuring
cp infra/parameters.example.json infra/parameters.json
```

`infra/parameters.json` の中身：

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "docIntelName":           { "value": "docintel-spread-social-02" },
    "aoaiAccountName":        { "value": "aoai-spread-social-02" },
    "location":               { "value": "japaneast" },
    "aoaiDeploymentName":     { "value": "extract-gpt54mini" },
    "aoaiModelName":          { "value": "gpt-5.4-mini" },
    "aoaiModelVersion":       { "value": "2026-03-17" },
    "aoaiDeploymentCapacity": { "value": 10 }
  }
}
```

> [!NOTE]
> `docIntelName` と `aoaiAccountName` は Azure グローバルで一意（小文字英数字 + ハイフン、2-24 文字）。衝突したら任意の接尾辞を付けて、以下の環境変数もそれに合わせてください。

環境変数：

```bash
export DOC_RG="spread-social-doc-rg"
export DOC_INTEL_NAME="docintel-spread-social-02"   # ← parameters.json と一致
export AOAI_ACCOUNT_NAME="aoai-spread-social-02"    # ← parameters.json と一致
export AOAI_DEPLOYMENT_NAME="extract-gpt54mini"     # ← parameters.json と一致
```

## デプロイ

```bash
az account show --query "{name:name, id:id}" -o table

az group create -n "$DOC_RG" -l japaneast

./infra/deploy.sh "$DOC_RG" infra/parameters.json
```

`deploy.sh` の動作：
- 現ユーザーの Object ID を取得
- `az deployment group create` で Bicep 適用 (3〜5 分)
- 出力: `docIntelEndpoint`, `aoaiEndpoint`, `aoaiDeploymentName` など

## 環境変数として保存

以降の抽出スクリプトで使うため、実リソースから取得します：

```bash
export DOCUMENT_INTELLIGENCE_ENDPOINT="$(az cognitiveservices account show \
  -g "$DOC_RG" -n "$DOC_INTEL_NAME" \
  --query properties.endpoint -o tsv)"

export AZURE_OPENAI_ENDPOINT="$(az cognitiveservices account show \
  -g "$DOC_RG" -n "$AOAI_ACCOUNT_NAME" \
  --query properties.endpoint -o tsv)"

export AZURE_OPENAI_DEPLOYMENT="$AOAI_DEPLOYMENT_NAME"

AOAI_LOCATION="$(az cognitiveservices account show \
  -g "$DOC_RG" -n "$AOAI_ACCOUNT_NAME" --query location -o tsv)"

AOAI_DEPLOYMENT_TYPE="$(az cognitiveservices account deployment show \
  -g "$DOC_RG" -n "$AOAI_ACCOUNT_NAME" \
  --deployment-name "$AOAI_DEPLOYMENT_NAME" \
  --query sku.name -o tsv)"
```

`.env` ファイル：

```bash
cat > .env <<EOF
DOC_RG=$DOC_RG
DOC_INTEL_NAME=$DOC_INTEL_NAME
AOAI_ACCOUNT_NAME=$AOAI_ACCOUNT_NAME
AOAI_DEPLOYMENT_NAME=$AOAI_DEPLOYMENT_NAME
DOCUMENT_INTELLIGENCE_ENDPOINT=$DOCUMENT_INTELLIGENCE_ENDPOINT
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
az cognitiveservices account list -g "$DOC_RG" -o table

az account get-access-token --resource https://cognitiveservices.azure.com \
  --query accessToken -o tsv | head -c 40; echo
```

次: [`03-prepare-documents.md`](03-prepare-documents.md)
