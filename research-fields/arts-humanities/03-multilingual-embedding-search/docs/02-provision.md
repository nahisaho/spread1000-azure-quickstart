# 02 — Azure リソース準備

## 推奨: Bicep + deploy.sh (キーレス認証)

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/arts-humanities/03-multilingual-embedding-search"
cd "$SCENARIO_DIR"

# 1) Object ID を確認
az ad signed-in-user show --query id -o tsv

# 2) infra/parameters.example.json を infra/parameters.json にコピーして deployerObjectId を設定
cp infra/parameters.example.json infra/parameters.json
# --- infra/parameters.json を編集 ---

# 3) デプロイ実行 (preflight + Bicep デプロイ + .env 生成)
bash infra/deploy.sh
```

`infra/deploy.sh` は以下を自動で行います:

- `az login` / サブスクリプション確認
- リソースプロバイダー登録 (Microsoft.Search, Microsoft.CognitiveServices)
- リソースグループ作成
- Bicep デプロイ (冪等)
  - Azure AI Search (Basic SKU, 1 replica, 1 partition, `disableLocalAuth: true`)
  - Azure OpenAI (Standard S0, `text-embedding-3-large`, `disableLocalAuth: true`)
  - RBAC 割り当て (デプロイヤー + Search サービス MI)
- `.env` 書き出し (chmod 600)

## 手動設定 (参考)

自動デプロイを使わない場合は以下を参照:

1. Portal → [Azure AI Search] → Basic SKU で作成、ローカル認証を無効化
2. Portal → [Azure OpenAI] → Standard S0 → `text-embedding-3-large` をデプロイ
3. アクセス制御 (IAM) → 自アカウントに必要なロールを付与

## `.env`

`infra/deploy.sh` が自動生成します。手動設定の場合:

```
AZURE_SEARCH_ENDPOINT=https://<name>.search.windows.net
AZURE_SEARCH_INDEX_NAME=multilingual-docs
AZURE_OPENAI_ENDPOINT=https://<name>.openai.azure.com/
AZURE_OPENAI_EMBED_DEPLOYMENT=text-embedding-3-large
AZURE_OPENAI_EMBED_DIM=3072
AZURE_OPENAI_API_VERSION=2024-10-21
```

> **セキュリティ**: `AZURE_OPENAI_KEY` はキーレス認証 (DefaultAzureCredential) が推奨。
> キーを使う場合は `.env` をコミットしないこと (`.gitignore` に記載済み)。

## 料金

| モデル | 単価 |
|---|---|
| text-embedding-3-large (3072d) | $0.13 / 1M tokens |
| text-embedding-3-small (1536d) | $0.02 / 1M tokens |
| Azure AI Search Basic | ~$75/月 (1 SU = 1 replica × 1 partition) |

**dimensions パラメータで縮小可能** (例: 3072 → 1024 で精度と保存量のトレードオフ)。

## text-embedding-3 系の多言語性能

- 100+ 言語で単一空間に埋め込み
- MIRACL (多言語検索ベンチ) で高スコア
- 日本語 ↔ 英語 ↔ 中国語のクロスリンガル検索は**小規模デモでの動作確認済み**。
  実運用適用にはドメイン特化の relevance judgments による評価が必須。
  詳細は `src/evaluate.py` と `docs/07-ethics-and-limits.md` を参照。
