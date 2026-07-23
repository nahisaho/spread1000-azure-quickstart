# 02 — Azure リソース準備

## 2 リソース作成 (Portal, 各 1 分)

### 1) Document Intelligence

- [Create a resource] → `Document Intelligence` → Create
- Resource group: `rg-kobunsho-demo`
- Region: `japaneast` (東アジアユーザ推奨) または `eastus`
- Pricing: `Standard S0`

### 2) Azure OpenAI

- [Create a resource] → `Azure OpenAI` → Create
- 同じ RG, region
- Pricing: `Standard S0`
- 作成後、**Azure OpenAI Studio** で `gpt-4o-mini` モデルをデプロイ:
  - Deployment name: `gpt-4o-mini`
  - Model version: 最新
  - Deployment type: `Standard` (Global Standard でも可)

## `.env` 設定

各リソースの `Keys and Endpoint` からコピー:

```
AZURE_DOCINT_ENDPOINT=https://kobunsho-docint.cognitiveservices.azure.com/
AZURE_DOCINT_KEY=xxxxxxxxxxxx
AZURE_OPENAI_ENDPOINT=https://kobunsho-aoai.openai.azure.com/
AZURE_OPENAI_KEY=xxxxxxxxxxxx
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-10-21
```

## az CLI で一括作成

```bash
RG=rg-kobunsho-demo
LOC=japaneast

az group create -n $RG -l $LOC

az cognitiveservices account create \
  -n kobunsho-docint$RANDOM -g $RG -l $LOC \
  --kind FormRecognizer --sku S0 --yes

az cognitiveservices account create \
  -n kobunsho-aoai$RANDOM -g $RG -l $LOC \
  --kind OpenAI --sku S0 --yes
```

デプロイメント作成は Portal (Azure OpenAI Studio) から行うのが確実です。

## 本番運用推奨: Managed Identity + Bicep

より本格的な構成は [../../social-science/02-document-structuring/](../../social-science/02-document-structuring/) を参照 (Bicep + MSI + `disableLocalAuth: true`)。
