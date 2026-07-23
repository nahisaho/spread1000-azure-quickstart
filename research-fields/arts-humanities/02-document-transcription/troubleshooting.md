# トラブルシューティング

## `Unauthorized: 401`

- Document Intelligence の Endpoint と Key の組み合わせを再確認
- Endpoint は `https://<name>.cognitiveservices.azure.com/` 形式 (末尾 `/` 必要)

## `DeploymentNotFound` (Azure OpenAI)

- Azure OpenAI Studio でデプロイメント名を再確認
- `.env` の `AZURE_OPENAI_DEPLOYMENT` はデプロイメント名 (モデル名ではない)

## `The response contains parsed data but it was cutoff`

- 入力 Markdown が長すぎて LLM の max_tokens に達した
- `extract.py` は `markdown[:8000]` で切っている、長文書はチャンク分割が必要

## OCR 精度が低い

- スキャン解像度不足 → 300 DPI 以上で再スキャン
- 崩し字 → Miwo 等の専用 OCR を使う (docs/04)
- 画像回転 → Document Intelligence は自動補正するが、傾き大きいと失敗

## `max_tokens` エラー

- Structured Outputs は `max_tokens` 指定不要 (自動設定)
- gpt-4o-mini のコンテキスト長は 128K なので通常は問題ない

## Azure OpenAI 利用申請が未承認

- Azure Portal → Azure OpenAI resource → 「Request access」から申請
- 承認まで数営業日
- 承認前でも gpt-4o-mini は自動承認されることが多い (最新情報は要確認)
