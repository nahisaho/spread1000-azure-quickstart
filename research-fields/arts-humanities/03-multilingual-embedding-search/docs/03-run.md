# 03 — 実行

## Step 1: インデックス構築

```bash
python src/build_index.py
```

- `src/corpus.py` の CORPUS (15 文、5 言語) を API に送信
- 結果 vectors を L2 正規化して `data/index.faiss` に保存
- メタデータ (id, lang, text) を `data/index_meta.json` に保存

## Step 2: 検索

```bash
python src/search.py --query "紫式部の物語"
python src/search.py --query "Japanese poetry" --k 3
python src/search.py --query "印象派" --k 10
```

## クロスリンガル検索の観察ポイント

- **同じ話題 (源氏物語) は言語横断で上位に集まる**
- **意味的に近い話題 (印象派 → Impressionism → 印象派)** も横断ヒット
- **音節・文字ベース検索では絶対に得られない結果**が embedding では取れる

## 期待出力 (「印象派」クエリ)

```
順位  類似度  ID    言語  テキスト
  1  0.7621  ja(*) ja  (該当なし場合はスキップ、fr02/de02/zh03 が上位)
  1  0.7532  fr02  fr  L'impressionnisme est un mouvement artistique français...
  2  0.7401  de02  de  Der Impressionismus ist eine französische Kunstströmung...
  3  0.7288  zh03  zh  印象派是十九世紀法國興起的藝術運動...
  4  0.7104  en04  en  Impressionism is a 19th-century art movement...
```
