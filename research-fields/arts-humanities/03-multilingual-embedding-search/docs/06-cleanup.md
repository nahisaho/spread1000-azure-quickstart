# 06 — 片付け

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/arts-humanities/03-multilingual-embedding-search"
cd "$SCENARIO_DIR"
source .env  # RG_NAME, AZURE_SEARCH_NAME, AZURE_SEARCH_INDEX_NAME, LOCATION を読み込む
test -f infra/main.bicep || { echo "wrong dir; abort"; exit 1; }

# ── インデックスレベルの削除 (Search サービスを残す場合) ──────────────────
az search index delete \
    --service-name "$AZURE_SEARCH_NAME" \
    --name "${AZURE_SEARCH_INDEX_NAME:-multilingual-docs}" \
    --resource-group "$RG_NAME" \
    --yes

# ── Azure AI Search サービスの削除 ────────────────────────────────────────
az search service delete \
    --name "$AZURE_SEARCH_NAME" \
    --resource-group "$RG_NAME" \
    --yes

# ── Azure OpenAI の削除 ───────────────────────────────────────────────────
# (AOAI_NAME は .env に出力されていない場合は az resource list で確認)
az cognitiveservices account delete \
    --name "$(az cognitiveservices account list -g "$RG_NAME" --query "[0].name" -o tsv)" \
    --resource-group "$RG_NAME"

# ── RG 全体を削除 (このシナリオ専用で作成した場合のみ) ──────────────────
if [[ "${DELETE_RG:-no}" == "yes" ]]; then
    az group delete -n "$RG_NAME" --yes --no-wait
    echo "リソースグループ '$RG_NAME' を削除中 (--no-wait)"
fi

# ── ローカルファイルの削除 ─────────────────────────────────────────────────
rm -rf .venv/ data/index.faiss data/index_meta.json outputs/*
```

## 注意

- `DELETE_RG=yes` は **このシナリオのリソースグループを専用で作成した場合のみ** 設定。
  他のリソースと共有している RG では `az search service delete` / `az cognitiveservices account delete` で個別に削除。
- Azure OpenAI のデプロイメントおよびアカウントは削除しないとプロビジョニング枠を占有するため明示的に削除。
- `text-embedding-3-large` は **トークン従量課金** (使用量がなければコストゼロ)。
  ただし Search サービスは時間課金のため、不要になったら削除推奨。
