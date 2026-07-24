# トラブルシューティング

## `DeploymentNotFound`

- Azure OpenAI Studio でデプロイメント名を再確認
- `.env` の `AZURE_OPENAI_EMBED_DEPLOYMENT` が Studio の「Deployment name」と一致するか

## `Rate limit exceeded`

- text-embedding-3-large のデフォルト quota は 350K tokens/min
- 大量埋め込みは `--batch-size` を下げる、または sleep を入れる
- Portal → Azure OpenAI → Quotas から上限拡張申請可

## 検索結果が偏る (同じ言語ばかり)

- クエリ言語のドキュメントが embedding 空間で近くに集まる傾向あり
- 対策: 各言語同数の doc を用意、または言語別に検索 + マージ

## `faiss-cpu` インストール失敗 (macOS ARM)

- `pip install faiss-cpu` で ARM64 wheel が入る (1.9+)
- 失敗する場合: `conda install -c pytorch faiss-cpu`

## 次元数を減らしたい (省メモリ)

```python
resp = client.embeddings.create(
    model=deployment,
    input=texts,
    dimensions=1024,  # 3072 → 1024
)
```

精度は数 % 低下、保存量は 1/3 に。`--embed-dim 1024` で指定。

## API バージョンエラー

- **Azure OpenAI Embeddings API**: `2024-10-21` が GA 安定版。`v1` データプレーンプレビューも利用可。
  埋め込み呼び出しでエラーが発生する場合は `openai` SDK を最新に更新:
  `pip install --upgrade "openai>=1.55"`
- **Azure AI Search API**: stable `2026-04-01` (または `2024-07-01`)。
  `azure-search-documents>=11.6.0` で自動的に安定 API バージョンが使用されます。

## `AuthorizationFailed` / `403 Forbidden`

- `disableLocalAuth: true` の場合、API キーは使用不可。`az login` または DefaultAzureCredential を使用。
- RBAC ロールが正しく割り当てられているか確認:
  - Search: `Search Service Contributor`, `Search Index Data Contributor`
  - AOAI: `Cognitive Services OpenAI User`
- RBAC 伝播に最大 10 分かかることがある

## `--search-endpoint` が未設定

```
[error] --search-endpoint (or AZURE_SEARCH_ENDPOINT) が未設定
```

- `source .env` を実行するか、`--search-endpoint` を明示指定
- ローカルデモのみの場合は `--fallback-faiss` を追加
