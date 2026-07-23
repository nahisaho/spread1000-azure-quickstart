# 04 — 結果の解釈

## 類似度スコア (0-1)

- L2 正規化後の内積 = cosine similarity
- **絶対値の解釈**: モデルとデータに依存、絶対閾値は不安定
- **相対順位** (top-k) で判断するのが基本

## スコアの目安 (text-embedding-3-large)

| 範囲 | 意味 |
|---|---|
| > 0.75 | 非常に近い (同一話題、翻訳ペア) |
| 0.5 - 0.75 | 関連あり (同一分野、関連トピック) |
| 0.3 - 0.5 | 弱い関連 |
| < 0.3 | ほぼ無関係 |

**ドメインごとに再測定** (自コーパスで既知ペアを検索して閾値決定)

## Cross-lingual 検索の限界

- **同一概念の言い回しが大きく違う場合**は精度低下
  - 例: 日本語「侘び寂び」→ 英語には対応語なし → 検索精度低い
- **固有名詞**は翻字揺れで難しい (「紫式部」/「Murasaki Shikibu」/「紫式部」)
- **時代・分野特有語彙**: 古典文法、専門用語は embedding が弱い

## Multi-vector との比較

- 本教材は **1 doc = 1 vector** (Flat Index)
- より長文なら段落単位に分割 (chunking) してから embedding + 平均 or 最大
- 高度: **ColBERT** のように multi-vector で各トークンを保持 (精度上, 保存量大)

## FAISS Index の選択

| Index 種別 | 特徴 | 適用規模 |
|---|---|---|
| `IndexFlatIP` (本教材) | 全探索、完全一致 | ~10 万件まで |
| `IndexIVFFlat` | クラスタ + Flat、高速検索 | 10 万〜1000 万 |
| `IndexHNSWFlat` | グラフベース、超高速 | 1000 万〜 |
| Azure AI Search | フルマネージド、更新 API 付き | 業務運用 |

## 参考文献

- OpenAI (2024). *"New embedding models and API updates"* — text-embedding-3 series
- Reimers & Gurevych (2020). *"Making Monolingual Sentence Embeddings Multilingual using Knowledge Distillation"*, EMNLP
- Johnson et al. (2019). *"Billion-scale similarity search with GPUs"* (FAISS), IEEE Big Data
