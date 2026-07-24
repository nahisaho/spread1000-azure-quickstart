# 03 — 実行

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/arts-humanities/03-multilingual-embedding-search"
cd "$SCENARIO_DIR"
source .env
```

## Step 1: インデックス構築

```bash
# Azure AI Search (推奨)
python src/build_index.py \
    --search-endpoint "$AZURE_SEARCH_ENDPOINT" \
    --embed-deployment "$AZURE_OPENAI_EMBED_DEPLOYMENT"

# ローカル FAISS フォールバック (オフラインデモ)
python src/build_index.py --fallback-faiss
```

- `src/corpus.py` の CORPUS (15 文、5 言語) を埋め込み
- Azure AI Search: HNSW インデックスを作成しベクトル + テキストをアップロード
- FAISS: `data/index.faiss` と ID+ハッシュのメタデータを保存

## Step 2: 検索

```bash
# Azure AI Search (ハイブリッド: BM25 + ベクトル)
python src/search.py --query "紫式部の物語"
python src/search.py --query "Japanese poetry" --k 3
python src/search.py --query "Impressionismus"

# ローカル FAISS フォールバック
python src/search.py --query "紫式部の物語" --fallback-faiss
```

## クロスリンガル検索の観察ポイント

- **同じ話題 (源氏物語) は言語横断で上位に集まる**
- **意味的に近い話題 (印象派 → Impressionism → 印象派)** も横断ヒット
- **音節・文字ベース検索では絶対に得られない結果**が embedding では取れる

## Step 3: 評価

```bash
python src/evaluate.py \
    --search-endpoint "$AZURE_SEARCH_ENDPOINT" \
    --eval-file data/eval_queries.jsonl
```

## 参考出力

（以下は参考出力。実行時の順位・スコアは埋め込みモデルとインデックス内容に依存）

```
クエリ: '印象派'  (mode: hybrid)

順位    スコア ID       言語   テキスト
----------------------------------------------------------------------------------------------------
  1   0.0321 fr02     fr   L'impressionnisme est un mouvement artistique français du XIXe siècle...
  2   0.0298 de02     de   Der Impressionismus ist eine französische Kunstströmung des 19. Jah...
  3   0.0287 zh03     zh   印象派是十九世紀法國興起的藝術運動，重視光線與色彩的即時捕捉。
  4   0.0271 en04     en   Impressionism is a 19th-century art movement characterized by small...
  5   0.0234 ja03     ja   俳句は五・七・五の音節構造を持つ日本の短詩形で、季語を含むのが伝統。
```
