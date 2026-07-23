# トラブルシューティング

## `DeploymentNotFound`

- Azure OpenAI Studio でデプロイメント名を再確認
- `.env` の `AZURE_OPENAI_EMBED_DEPLOYMENT` が Studio の「Deployment name」と一致するか

## `Rate limit exceeded`

- text-embedding-3-large のデフォルト quota は 350K tokens/min
- 大量埋め込みは batch_size を下げる、または sleep を入れる
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

精度は数 % 低下、保存量は 1/3 に。

## API version が古い

- `2024-10-21` 以降を推奨 (Structured Outputs, dimensions パラメータ対応)
- 古い version では `dimensions` パラメータが無視される
