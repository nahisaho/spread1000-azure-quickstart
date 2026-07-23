# トラブルシューティング

## `graphrag init` でエラー

- Python バージョン確認: 3.10-3.12 (3.13 未対応の可能性)
- `pip install -U graphrag==2.4.0` で明示バージョン指定

## `settings.yaml` が読み込めない (`Input should be a valid string`)

- `api_version: 2024-10-21` を **ダブルクォート** で囲む (`api_version: "2024-10-21"`)
- YAML の date auto-parse を回避するため、本 repo の `settings.yaml` は既に対処済

## `graphrag index` が途中で失敗

### 認証エラー (401 Unauthorized)
- `.env` の `GRAPHRAG_API_KEY` を Azure Portal で再確認・再取得
- `GRAPHRAG_API_BASE` が末尾スラッシュなしの `https://<name>.openai.azure.com` か確認
  - `az cognitiveservices account show --name <NAME> --resource-group <RG> --query properties.endpoint -o tsv` で正しいエンドポイントを取得
  - エンドポイントが `<region>.api.cognitive.microsoft.com` 形式の場合はリソース作成時に `--custom-domain` が未指定 → リソース再作成が必要 (`docs/03-provision.md` 参照)

### モデル未デプロイ (404 DeploymentNotFound)
- Azure OpenAI Studio でデプロイ名を確認
- `.env` の `GRAPHRAG_LLM_DEPLOYMENT_NAME` とデプロイ名が完全一致か

### 設定検証エラー (Managed Identity 使用時)
- `auth_type: azure_managed_identity` に切り替えた場合、`api_key:` の行を settings.yaml の**両モデル**から削除する必要あり (併記するとエラー)

### レート制限 (429 Too Many Requests)
- `src/settings.yaml` の `concurrent_requests: 4` を 2 に減らす
- Azure OpenAI のクォータ増加を申請 (Portal → クォータ)

### コスト超過が心配
- 中断: Ctrl+C で停止 → `ragtest/cache/` に途中結果が残る
- 再開: `python -m graphrag index --root ./ragtest` (キャッシュから再開、追加コストは残工程分のみ)

## `graphrag query` で「no data available」

- インデックス構築が完了していない、`ragtest/output/` に parquet が全て揃っているか確認
- vector store (`ragtest/output/lancedb/`) が空でないか確認

## 日本語コーパスで英語出力になる

- デフォルト prompt が英語のため
- `ragtest/prompts/*.txt` を日本語版に置換、または `graphrag prompt-tune` で自動生成

## `pyarrow` インストール失敗

- `pip install pyarrow` を明示的に実行
- Windows で失敗する場合は Microsoft C++ Build Tools が必要

## `lancedb` のインポートエラー

- WSL/Linux で glibc バージョンが古い場合に発生
- Ubuntu 22.04+ を推奨
