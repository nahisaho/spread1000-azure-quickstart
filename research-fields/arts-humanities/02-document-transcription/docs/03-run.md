# 03 — 実行

```bash
python src/extract.py --input data/sample_kobunsho.pdf
```

## サンプル PDF がない場合

- **国立国会図書館デジタルコレクション**: https://dl.ndl.go.jp/
  - 「江戸時代」「明治」で検索 → 著作権切れ PDF をダウンロード
- **国立公文書館デジタルアーカイブ**: https://www.digital.archives.go.jp/

## 期待出力

```
[docint] analyzing sample_kobunsho.pdf
[docint] extracted 4231 chars from 3 pages
[aoai] extracting metadata with gpt-4o-mini

=== extracted metadata ===
{
  "title": "御触書 (推定: 火の用心に関する町触)",
  "author": null,
  "date_estimated": "享保十六年 (1731)",
  "document_type": "御触書",
  "key_topics": ["火の用心", "町内取締", "江戸町奉行"],
  "summary": "享保十六年に江戸町奉行から出された、...",
  "difficult_passages": [
    "OCR 誤読と推定: 「〜候處」の判読困難な箇所",
    ...
  ]
}

[done] outputs/sample_kobunsho_metadata.json, sample_kobunsho_ocr.md
```

## 出力

- `outputs/<name>_ocr.md` — Document Intelligence の Markdown OCR
- `outputs/<name>_metadata.json` — LLM が抽出した Pydantic スキーマ準拠 JSON
