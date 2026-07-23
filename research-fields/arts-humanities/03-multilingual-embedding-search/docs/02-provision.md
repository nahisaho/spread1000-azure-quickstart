# 02 — Azure リソース準備

## Azure OpenAI (1 リソースのみ必要)

1. Portal → [Create a resource] → `Azure OpenAI`
2. Region: `japaneast` または `eastus` (embedding-3 対応リージョン)
3. Pricing: Standard S0
4. 作成後 Azure OpenAI Studio (`https://oai.azure.com/`) を開く:
   - `Deployments` → `+ Create new deployment`
   - Model: **text-embedding-3-large** (3072 dim)
   - Deployment name: `text-embedding-3-large`
   - Deployment type: `Standard` (Global Standard でも可)

## `.env`

```
AZURE_OPENAI_ENDPOINT=https://<name>.openai.azure.com/
AZURE_OPENAI_KEY=xxxxxxxx
AZURE_OPENAI_EMBED_DEPLOYMENT=text-embedding-3-large
AZURE_OPENAI_API_VERSION=2024-10-21
```

## 料金

| モデル | 単価 |
|---|---|
| text-embedding-3-large (3072d) | $0.13 / 1M tokens |
| text-embedding-3-small (1536d) | $0.02 / 1M tokens |
| text-embedding-ada-002 (旧, 1536d) | $0.10 / 1M tokens |

**dimensions パラメータで縮小可能** (例: 3072 → 1024 で精度と保存量のトレードオフ)。

## text-embedding-3 系の多言語性能

- 100+ 言語で単一空間に埋め込み
- MIRACL (多言語検索ベンチ) で高スコア
- 日本語 <-> 英語 <-> 中国語の cross-lingual 検索が実用レベル
