# 02 — Azure リソース準備

## 推奨: Bicep + Entra 認証 (キー不要)

```bash
SCENARIO_DIR=$(git rev-parse --show-toplevel)/research-fields/arts-humanities/02-document-transcription

# What-if で確認 (変更なし)
bash "$SCENARIO_DIR/infra/deploy.sh" \
  --resource-group rg-arts02-demo \
  --location eastus \
  --what-if

# 実際のデプロイ
bash "$SCENARIO_DIR/infra/deploy.sh" \
  --resource-group rg-arts02-demo \
  --location eastus \
  --yes
```

デプロイ完了後、`$SCENARIO_DIR/.env` (chmod 600) が自動生成されます。
認証は `DefaultAzureCredential` が担うため API キーは不要です (`az login` 済みであること)。

## 手動作成 (Portal)

### 1) Document Intelligence

- [Create a resource] → `Document Intelligence` → Create
- Resource group: `rg-arts02-demo`
- Region: `eastus` または `japaneast`
- Pricing: `Standard S0`
- **認証**: `Keys and Endpoint` のキーは使わず、IAM で自分のアカウントに
  **Cognitive Services User** ロール (`a97b65f3-24c7-4388-baec-2e87135dc908`) を付与

### 2) Azure OpenAI

- [Create a resource] → `Azure OpenAI` → Create
- 同じ RG, region
- Pricing: `Standard S0`
- 作成後、**Azure OpenAI Studio** で `gpt-4o-mini` モデルをデプロイ:
  - Deployment name: `gpt-4o-mini`
  - Model version: 最新
  - Deployment type: `GlobalStandard`
- IAM で **Cognitive Services OpenAI User** ロール (`5e0bd9bd-7b93-4f28-af87-19fc36ad61bd`) を付与

## `.env` 設定 (手動作成時)

```bash
cp .env.example .env
# エンドポイントのみ編集 (キーは設定しない)
```

```
AZURE_DOCINT_ENDPOINT=https://docint-<suffix>.cognitiveservices.azure.com/
AZURE_OPENAI_ENDPOINT=https://aoai-<suffix>.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-10-21
```
