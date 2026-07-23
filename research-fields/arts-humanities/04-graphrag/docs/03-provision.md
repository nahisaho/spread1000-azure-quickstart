# 03 — Azure リソース準備

## 1. Azure OpenAI リソース作成

```bash
RG="rg-graphrag-quickstart"
LOC="japaneast"
NAME="aoai-graphrag-$RANDOM"

az group create -n $RG -l $LOC
az cognitiveservices account create \
    --name $NAME --resource-group $RG --location $LOC \
    --kind OpenAI --sku S0
```

## 2. モデルのデプロイ

Azure OpenAI Studio (https://oai.azure.com) を開き、以下 2 つをデプロイ:

| Deployment 名 | Model | Version | Capacity |
|---|---|---|---|
| `gpt-4o-mini` | gpt-4o-mini | latest | 100K TPM |
| `text-embedding-3-small` | text-embedding-3-small | latest | 100K TPM |

`gpt-4o` (高精度・高コスト版) を使う場合は `gpt-4o` デプロイを追加。

## 3. `.env` を作成

```bash
cp .env.example .env
```

`.env` を編集:
```bash
GRAPHRAG_API_KEY=<Azure OpenAI キー>
GRAPHRAG_API_BASE=https://<リソース名>.openai.azure.com
GRAPHRAG_API_VERSION=2024-10-21
GRAPHRAG_LLM_MODEL=gpt-4o-mini
GRAPHRAG_LLM_DEPLOYMENT_NAME=gpt-4o-mini
GRAPHRAG_EMBEDDING_MODEL=text-embedding-3-small
GRAPHRAG_EMBEDDING_DEPLOYMENT_NAME=text-embedding-3-small
```

API キーは Azure Portal → リソース → 「キーとエンドポイント」で取得。

## 4. 動作確認

```bash
source .venv/bin/activate
python -c "
import os, dotenv; dotenv.load_dotenv()
from openai import AzureOpenAI
c = AzureOpenAI(
    azure_endpoint=os.environ['GRAPHRAG_API_BASE'],
    api_key=os.environ['GRAPHRAG_API_KEY'],
    api_version=os.environ['GRAPHRAG_API_VERSION'],
)
r = c.chat.completions.create(
    model=os.environ['GRAPHRAG_LLM_DEPLOYMENT_NAME'],
    messages=[{'role':'user','content':'Hello'}])
print(r.choices[0].message.content)
"
```

`Hello!` 相当が返れば準備完了。

## 認証代替: Managed Identity

本番運用では API キーではなく **Managed Identity** を推奨:
- `settings.yaml` で `auth_type: azure_managed_identity`
- Azure ML/App Service に User-Assigned MI をアタッチ
- MI に **Cognitive Services OpenAI User** ロールを割り当て
