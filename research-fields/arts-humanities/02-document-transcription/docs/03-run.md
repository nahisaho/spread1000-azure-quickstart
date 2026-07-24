# 03 — 実行

```bash
SCENARIO_DIR=$(git rev-parse --show-toplevel)/research-fields/arts-humanities/02-document-transcription
cd "$SCENARIO_DIR"
```

## PDF メタデータのクリア (推奨)

PDF には著者名・組織名・GPS・更新日時などのメタデータが埋め込まれていることがあります。
クラウド送信前に `scripts/sanitize_pdf.sh` でクリアしてください。

```bash
# 依存ツールのインストール (初回のみ)
sudo apt install libimage-exiftool-perl qpdf

# メタデータ除去 (exiftool + qpdf rewrite)
bash "$SCENARIO_DIR/scripts/sanitize_pdf.sh" original.pdf data/input_clean.pdf

# 画像ファイル (JPEG/PNG/TIFF) の場合
exiftool -all= --icc_profile:all= image.jpg
```

> **補足**: exiftool の編集だけでは PDF オブジェクトストリームに残留メタデータが
> 残ることがあります。qpdf による構造リライトでほぼ除去できますが、
> 完全な除去が必要な場合は PDF/A 変換または再スキャンを検討してください。

## 抽出実行

```bash
python src/extract.py --input data/input_clean.pdf
```

オプション:

```
--max-pages 20          DI 送信ページ上限 (default 20)
--max-cost-usd 0.50     推定コスト上限 (default $0.50)
--yes                   コスト確認プロンプトをスキップ
--save-markdown         OCR Markdown を outputs/ に保存
--retain-service-side   DI サーバー側結果を削除しない
--reject-truncation     --max-chars 超過時にエラー終了
```

## サンプル PDF がない場合

- **国立国会図書館デジタルコレクション**: https://dl.ndl.go.jp/
  - 「江戸時代」「明治」で検索 → 各アイテムのライセンスを確認してダウンロード
- **国立公文書館デジタルアーカイブ**: https://www.digital.archives.go.jp/

## 期待出力

```
[cost] estimated ≈ $0.0500 USD (参考値 2026-07 時点 eastus S0)
[docint] analyzing input_clean.pdf
[docint] extracted 4231 chars from 3 pages
[docint] deleted server-side result xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
[aoai] 1 chunk(s) → gpt-4o-mini
[aoai] chunk 1/1

=== extracted metadata ===
{
  "title": "御触書 (推定: 火の用心に関する町触)",
  "author": null,
  "date_estimated": "享保十六年 (1731)",
  "document_type": "御触書",
  "key_topics": ["火の用心", "町内取締", "江戸町奉行"],
  "summary": "享保十六年に江戸町奉行から出された、...",
  "difficult_passages": ["OCR 誤読と推定: 「〜候處」の判読困難な箇所"]
}

[done] outputs/input_clean_metadata.json, outputs/manifest.json
```

## 出力

- `outputs/<name>_metadata.json` — LLM が抽出した書誌情報 JSON
- `outputs/<name>_ocr.md` — `--save-markdown` 指定時のみ生成
- `outputs/manifest.json` — 処理の Provenance (SHA-256, API バージョン, トークン数等)
