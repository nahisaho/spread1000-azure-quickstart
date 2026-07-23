# 02. Azure リソースの払い出し

`infra/main.bicep` は次を作成します:

- Azure OpenAI アカウント (Japan East、S0、`disableLocalAuth: true`、`customSubDomainName` 必須)
- Embedding デプロイ `embed-small` (`text-embedding-3-small` v1、Standard、30K TPM)
- Cluster ラベル生成用 GPT デプロイ `label-gpt54mini` (`gpt-5.4-mini` v2026-03-17、GlobalStandard、30K TPM)
- 実行ユーザに `Cognitive Services OpenAI User` ロール (GUID `5e0bd9bd-7b93-4f28-af87-19fc36ad61bd`)

## デプロイ手順

```bash
export AZURE_RESOURCE_GROUP=rg-spread-social-03
export AZURE_LOCATION=japaneast    # 既定

cd infra
./deploy.sh
```

`deploy.sh` は以下を行います:

1. リソースグループを (存在しなければ) 作成
2. Bicep を `az deployment group create` で適用
3. 出力エンドポイント・デプロイ名を上位ディレクトリの `.env` に書き出す
4. ロール割当伝播を 30 秒待機

## 生成される `.env`

```bash
AZURE_OPENAI_ENDPOINT=https://aoai-social-03-<hash>.openai.azure.com/
AZURE_OPENAI_EMBED_DEPLOYMENT=embed-small
AZURE_OPENAI_LABEL_DEPLOYMENT=label-gpt54mini
AZURE_OPENAI_LOCATION=japaneast
AZURE_OPENAI_EMBED_DEPLOYMENT_TYPE=Standard
AZURE_OPENAI_LABEL_DEPLOYMENT_TYPE=GlobalStandard
```

利用前に `set -a && source .env && set +a` で環境変数に読み込むか、`python-dotenv` でロードしてください。

## パラメータ調整

- 別リージョン (East US 2 など): `AZURE_LOCATION=eastus2 ./deploy.sh`
- 名前を変えたい: `infra/parameters.example.json` を `parameters.json` にコピーして編集
- TPM を増やしたい: `parameters.json` の `embedCapacityK` / `labelCapacityK` を調整 (Portal クォータ内)

> [!IMPORTANT]
> Sweden Central は `text-embedding-3-small` の **Regional Standard** をサポートしません。同リージョンで使う場合は `sku.name: 'GlobalStandard'` に変更してください。
