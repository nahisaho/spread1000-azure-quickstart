# 05 — 自前コーパスへの適用

## `src/corpus.py` の差し替え

```python
CORPUS = [
    {"id": "book001_p001", "lang": "ja", "text": "…"},
    {"id": "letter042", "lang": "fr", "text": "Cher Monsieur, ..."},
    ...
]
```

- `id` は自由 (ページ番号、Section 名、URI 何でも)
- `lang` は ISO 639-1 (`ja`, `en`, `fr`, `de`, `zh`, `ko`, `es` 等)
- `text` は 8000 トークン以内 (embedding-3-large の上限)

## 長文の Chunking

論文/書籍レベルの長文は、段落や sliding window で分割:

```python
def chunk_text(text: str, max_chars: int = 1500, overlap: int = 200) -> list[str]:
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i + max_chars])
        i += max_chars - overlap
    return chunks
```

各 chunk を別レコードとして CORPUS に追加。検索結果は「同一 doc の複数 chunk」が上位に来る → doc レベルで集約 (max score / MMR).

## Bulk 埋め込み (数千件)

Azure OpenAI Embeddings API は 1 リクエストで最大 2048 入力を受け付けます:

```python
def batch_embed(texts, client, deployment, batch_size=100):
    vectors = []
    for i in range(0, len(texts), batch_size):
        resp = client.embeddings.create(model=deployment, input=texts[i:i+batch_size])
        vectors.extend(e.embedding for e in resp.data)
    return np.array(vectors, dtype=np.float32)
```

## 応用例

| ドメイン | 用途 |
|---|---|
| 比較文学 | 日本古典と欧文翻訳のパラレル探索 |
| 翻訳研究 | 訳語選択の類似事例検索 |
| 宗教学 | 経典間の類似節検索 (パーリ語ローマ字化 + 英訳 + 和訳) |
| 書誌学 | タイトル・要旨からの類似文献発見 |
| 民俗学 | 世界の口承文学モチーフ比較 |

## スケール時の選択肢

- **~10 万件**: FAISS Flat (本教材)
- **10 万〜1000 万**: FAISS IVF+PQ
- **1000 万〜**: **Azure AI Search** (ベクトル + BM25 ハイブリッド, 増分更新)
  - Azure AI Search は本シナリオの CORPUS を上げるだけで同等機能 + REST API
  - スケーラビリティが必要になったら移行

## FAISS Index の再構築 vs 増分更新

- `IndexFlatIP` は追加のみ可能 (`index.add()`, 削除不可)
- 全再構築が必要になったら **バッチジョブ化**、または Azure AI Search に切替
