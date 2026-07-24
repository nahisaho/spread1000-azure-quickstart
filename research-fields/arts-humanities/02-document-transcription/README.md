# 02 — 古文書翻刻 (Document Intelligence + Azure OpenAI)

**分野**: 歴史学、書誌学、古文書学、デジタルアーカイブ  
**手法**: Azure AI Document Intelligence の `prebuilt-layout` で OCR → Azure OpenAI Structured Outputs で書誌情報 JSON 抽出  
**時間**: ~10 分 (リソース作成含む)

## 何が学べるか

- Document Intelligence でスキャン画像/PDF から Markdown 出力
- Azure OpenAI Structured Outputs (Pydantic スキーマ準拠) の使い方
- OCR → LLM の 2 段パイプライン設計
- 誤読への LLM 側での対応 (「推定に自信ない場合は null」プロンプト設計)

## リソース準備

`infra/deploy.sh` で Bicep デプロイ (Entra 認証、キー不要):

```bash
SCENARIO_DIR=$(git rev-parse --show-toplevel)/research-fields/arts-humanities/02-document-transcription
bash "$SCENARIO_DIR/infra/deploy.sh" \
  --resource-group rg-arts02-demo \
  --location eastus
```

または Azure Portal で 2 リソースを手動作成し `.env` を設定:
1. **Document Intelligence** (旧 Form Recognizer) — Standard S0
2. **Azure OpenAI** — `gpt-4o-mini` デプロイメントを作成

```bash
cp .env.example .env
# .env を編集 (キーは不要; DefaultAzureCredential を使用)
```

## 使い方

```bash
SCENARIO_DIR=$(git rev-parse --show-toplevel)/research-fields/arts-humanities/02-document-transcription
cd "$SCENARIO_DIR"
python -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# PDF メタデータをクリア (任意だが推奨)
bash scripts/sanitize_pdf.sh <path-to-your-document.pdf> data/input_clean.pdf

# 書誌情報を抽出
python src/extract.py --input data/input_clean.pdf
```

## コスト (参考値 2026-07 時点、eastus S0)

| 項目 | 単価 | 本デモ (5 ページ) |
|---|---|---|
| Document Intelligence Layout | $10 / 1000 pages | **$0.05** |
| Azure OpenAI gpt-4o-mini | $0.15/1M input, $0.60/1M output | **~$0.01** |
| **合計** | — | **~$0.06** |

> 料金は変更される場合があります。最新値は
> [Azure AI Document Intelligence 料金](https://azure.microsoft.com/pricing/details/ai-document-intelligence/)
> と [Azure OpenAI 料金](https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/) で確認し、
> [Azure 料金計算ツール](https://azure.microsoft.com/pricing/calculator/) で見積もってください。

## ドキュメント

- [01 前提条件](docs/01-prerequisites.md)
- [02 Azure リソース準備](docs/02-provision.md)
- [03 実行](docs/03-run.md)
- [04 結果の解釈](docs/04-understand-results.md)
- [05 自前古文書への適用](docs/05-your-data.md)
- [06 片付け](docs/06-cleanup.md)
- [07 倫理と限界](docs/07-ethics-and-limits.md)
- [トラブルシューティング](troubleshooting.md)

## 参考

- 類似実装: [../../social-science/02-document-structuring/](../../social-science/02-document-structuring/) が Bicep + Managed Identity 版
