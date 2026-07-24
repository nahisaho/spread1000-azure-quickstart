# 03 — 多言語エンベディング検索 (Azure AI Search + Azure OpenAI)

**分野**: 比較文学、翻訳研究、書誌学、多言語アーカイブ、宗教学  
**手法**: Azure OpenAI `text-embedding-3-large` で 5 言語 (日/英/仏/独/中) を単一ベクトル空間に、Azure AI Search で HNSW ベクトル + BM25 ハイブリッド検索  
**時間**: ~10 分 (リソース作成含む)

## 何が学べるか

- 多言語埋め込みモデルによる **言語横断検索** (日本語クエリで英語文献ヒット)
- Azure AI Search の HNSW ベクトルインデックスと BM25 ハイブリッド検索
- Azure OpenAI Embeddings API (`text-embedding-3-large`) の使い方
- キーレス認証 (DefaultAzureCredential) + RBAC による安全なアクセス制御
- FAISS ローカルフォールバック (オフラインデモ用, `--fallback-faiss`)

## リソース準備

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/arts-humanities/03-multilingual-embedding-search"
cd "$SCENARIO_DIR"

# Bicep + deploy.sh で自動プロビジョニング
bash infra/deploy.sh
```

詳細は [docs/02-provision.md](docs/02-provision.md) を参照。

## 使い方

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/arts-humanities/03-multilingual-embedding-search"
cd "$SCENARIO_DIR"
source .env

python -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 1) 15 文の多言語コーパスを埋め込み + Azure AI Search インデックス作成
python src/build_index.py --search-endpoint "$AZURE_SEARCH_ENDPOINT"

# 2) 任意言語でクエリ (ハイブリッド: BM25 + ベクトル)
python src/search.py --query "紫式部の物語"
python src/search.py --query "Japanese poetry"
python src/search.py --query "Impressionismus"

# 3) 評価 (per-language NDCG / MRR / Recall)
python src/evaluate.py --search-endpoint "$AZURE_SEARCH_ENDPOINT"
```

## ローカル FAISS フォールバック (オフラインデモ)

```bash
python src/build_index.py --fallback-faiss
python src/search.py --query "紫式部の物語" --fallback-faiss
```

## コスト

| 項目 | 単価 | 本デモ (15 doc + 数クエリ) |
|---|---|---|
| text-embedding-3-large | $0.13 / 1M tokens | **< $0.001** |
| Azure AI Search Basic | ~$75/月 (1 SU) | 使用後は削除推奨 |

## ドキュメント

- [01 前提条件](docs/01-prerequisites.md)
- [02 Azure リソース準備](docs/02-provision.md)
- [03 実行](docs/03-run.md)
- [04 結果の解釈](docs/04-understand-results.md)
- [05 自前コーパスへの適用](docs/05-your-data.md)
- [06 片付け](docs/06-cleanup.md)
- [07 倫理と限界](docs/07-ethics-and-limits.md)
- [08 RAG プロンプトインジェクション対策](docs/08-rag-safety.md)
- [トラブルシューティング](troubleshooting.md)
