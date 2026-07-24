# 04 — 結果の解釈

## 類似度スコア

コサイン類似度の範囲は **[-1, 1]** です (0-1 ではありません)。

- L2 正規化後の内積 = コサイン類似度
- **絶対値での解釈はモデル・データに依存**するため、普遍的なスコア帯の表は提供しません
- 実際のしきい値は **ラベル付き validation set** から決定してください
- `src/evaluate.py` の per-language MRR / NDCG から派生することを推奨

Azure AI Search のハイブリッド検索スコアは BM25 + ベクトルの RRF (Reciprocal Rank Fusion) スコアであり、
純粋なコサイン類似度とは異なります。

## Cross-lingual 検索の限界

- **同一概念の言い回しが大きく違う場合**は精度低下
  - 例: 日本語「侘び寂び」→ 英語には対応語なし → 検索精度低い
- **固有名詞**は翻字揺れで難しい (「紫式部」/「Murasaki Shikibu」)
- **時代・分野特有語彙**: 古典文法、専門用語は embedding が弱い

## Multi-vector との比較

- 本教材は **1 doc = 1 vector** (Flat Index)
- より長文なら段落単位に分割 (chunking) してから embedding + 平均 or 最大
- 高度: **ColBERT** のように multi-vector で各トークンを保持 (精度上, 保存量大)

## Azure AI Search インデックスの選択肢

| 方式 | 特徴 | 適用規模 |
|---|---|---|
| ローカル FAISS `IndexFlatIP` (本教材 fallback) | 全探索、完全一致 | ~10 万件まで |
| Azure AI Search HNSW (本教材デフォルト) | フルマネージド、ハイブリッド BM25+ベクトル、更新 API | 業務運用 |
| Azure AI Search + セマンティックランキング | 上位 50 件を言語モデルでリランク | 高精度が必要な場合 |

## 参考文献

- OpenAI (2024). *"New embedding models and API updates"* — text-embedding-3 series
- Reimers & Gurevych (2020). *"Making Monolingual Sentence Embeddings Multilingual using Knowledge Distillation"*, EMNLP
- Johnson et al. (2019). *"Billion-scale similarity search with GPUs"* (FAISS), IEEE Big Data
