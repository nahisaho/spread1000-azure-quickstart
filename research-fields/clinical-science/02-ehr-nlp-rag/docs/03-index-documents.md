# 03. サンプルカルテのインデックス化

## 目的

`inputs/sample-notes/` の合成退院サマリ 3 件を、
1. Azure Blob Storage にアップロード
2. チャンク分割 → embedding
3. Azure AI Search のベクトル + BM25 ハイブリッドインデックスに格納

します。

## 前提

- [02-provision.md](02-provision.md) 完了、`.env` に自動追記された値がある
- Python 仮想環境がアクティブ (`source .venv/bin/activate`)
- `az login` 済み（DefaultAzureCredential が利用）

## 1. 環境変数の再読み込み

```bash
cd research-fields/clinical-science/02-ehr-nlp-rag
set -a && source .env && set +a
echo "STORAGE_ACCOUNT=$STORAGE_ACCOUNT"
echo "SEARCH_ENDPOINT=$SEARCH_ENDPOINT"
echo "OPENAI_ENDPOINT=$OPENAI_ENDPOINT"
```

## 2. Blob にアップロード

```bash
python scripts/upload_docs.py
```

期待される出力:

```
  [uploaded] synth-001-pneumonia.md (1094 bytes)
  [uploaded] synth-002-stemi.md (1442 bytes)
  [uploaded] synth-003-uc.md (1201 bytes)

Done. uploaded=3, skipped=0, total=3
```

Portal 確認: **Storage account → Containers → documents** に 3 ファイルが表示されるはず。

## 3. AI Search インデックス作成 + 埋め込み投入

```bash
python scripts/index_docs.py
```

このスクリプトが行うこと:
1. AI Search に `ehr-notes` インデックスを作成（存在すれば更新）
2. インデックス構成: `id`(key), `source_blob`, `chunk_index`, `content` (BM25, Japanese `ja.microsoft` analyzer), `content_vector` (HNSW 3072-dim cosine)
3. Semantic search 設定 `default-semantic` を付与
4. Blob からドキュメントを取得
5. `tiktoken` (cl100k_base) で 512 token 単位、64 token overlap のチャンクに分割
6. Azure OpenAI `text-embedding-3-large` で埋め込み計算
7. AI Search にバッチアップロード（500 docs/batch）

期待される出力:

```
==> Creating/updating index 'ehr-notes'...
  [ok] index 'ehr-notes' created/updated
==> Downloading blobs from stehrnlp<suffix>/documents ...
  [read] synth-001-pneumonia.md (1094 chars)
  [read] synth-002-stemi.md (1442 chars)
  [read] synth-003-uc.md (1201 chars)
==> Chunking and embedding...
  [embed] synth-001-pneumonia.md: 1 chunks
  [embed] synth-002-stemi.md: 1 chunks
  [embed] synth-003-uc.md: 1 chunks
==> Uploading 3 chunks to index 'ehr-notes'...
  batch 1: 3/3 succeeded
Done.
```

## 4. インデックスの動作確認

```bash
# インデックスに何件入っているか
python3 -c "
import os
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
c = SearchClient(endpoint=os.environ['SEARCH_ENDPOINT'], index_name=os.environ['SEARCH_INDEX'], credential=DefaultAzureCredential())
r = c.search(search_text='*', include_total_count=True, top=0)
print(f'Total docs in index: {r.get_count()}')
"
```

期待: `Total docs in index: 3`

## 5. 独自の合成データを追加する

- `inputs/sample-notes/` に .md ファイルを追加
- `python scripts/upload_docs.py` （既存分は skip、新規のみアップロード）
- `python scripts/index_docs.py` （既存インデックスに追記、同じ id は上書き）

## トラブルシューティング

| 症状 | 原因・対応 |
|---|---|
| `Forbidden`: `AuthorizationPermissionMismatch` (Blob) | Storage Blob Data Contributor が未付与 → `infra/deploy.sh` の RBAC 部分を再実行 |
| `Unauthorized` on Search | Search Index Data Contributor 未付与 → 同上、または `az login` 後に権限伝播まで数分待つ |
| `401 Unauthorized` on OpenAI embedding | Cognitive Services OpenAI User 未付与 → 同上。または AAD 認証エラーなら `az account get-access-token --resource https://cognitiveservices.azure.com` で確認 |
| `The vector field 'content_vector' has dimensionality...` | 過去に別次元でインデックス作成済み → インデックスを削除して再作成。`az search index delete` サブコマンドは存在しないため、次のいずれかを使用: (a) Python SDK: `python -c "import os; from azure.identity import DefaultAzureCredential; from azure.search.documents.indexes import SearchIndexClient; SearchIndexClient(endpoint=os.environ['SEARCH_ENDPOINT'], credential=DefaultAzureCredential()).delete_index(os.environ['SEARCH_INDEX'])"`、(b) REST: `az rest --method delete --url "$SEARCH_ENDPOINT/indexes/$SEARCH_INDEX?api-version=2024-07-01" --resource "https://search.azure.com"`、(c) Portal から削除 |
| `HTTPSConnectionPool ... Read timed out` | ネットワーク不安定、または OpenAI で TPM 超過 → 数分待って再実行 |

→ **[04-query-rag.md](04-query-rag.md) に進む**
