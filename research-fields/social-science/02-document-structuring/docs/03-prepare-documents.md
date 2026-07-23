# 03 — デモ PDF の準備

このシナリオは **完全に架空** の 3 種類の日本語 PDF を、ローカルで生成します：

1. `demo-court.pdf` — 架空の判決文 (2 ページ、born-digital テキスト)
2. `demo-factory.pdf` — 架空の工場名簿 (2 ページ、表付き)
3. `demo-factory-scanned.pdf` — 上と同じ内容を **画像化** (OCR テスト用)

## 生成

```bash
cd research-fields/social-science/02-document-structuring
source .venv/bin/activate

python scripts/generate_demo_pdfs.py --output-dir data/
```

出力：

```text
data/
├── demo-court.pdf              (~15 KB, 2 pages)
├── demo-court.answer.json      (期待抽出結果 - 正解)
├── demo-factory.pdf            (~20 KB, 2 pages)
├── demo-factory.answer.json
└── demo-factory-scanned.pdf    (~800 KB, 2 pages 画像化)
```

> [!IMPORTANT]
> 生成される PDF は**すべて架空**（人名、事件番号、企業名、住所すべて捏造、CC0 相当）です。実在の判決や企業情報を含めていません。

## 自分の文書を使う

`data/` に PDF を配置し、次章 `04-run-extraction.md` の実行時に `--input` で指定します：

```bash
python src/extract.py --input data/my-document.pdf --schema court --output data/output/my.json
```

利用可能なスキーマ（トップレベル形状）：

- `court` — 判決文 → `{case_number, court, date, judges[], parties[], holding, reasoning_summary, source_page_range}`
- `factory` — 工場名簿 → `{records: [{factory_name, address, industry_code, employees, established, source_page_range}], source_page_range}`

自前スキーマの追加は [`src/schemas.py`](../src/schemas.py) を参照してください。

## 著作権と個人情報の注意 (実文書利用時)

- **著作権法 13 条**: 法令、告示、通達、判決文自体は著作権対象外ですが、判例集などの**編集著作物**は対象になり得ます
- **個人情報**: 判例中の氏名・住所・勤務先はマスクしてからアップロードしてください
- **要配慮個人情報**: 犯罪歴・病歴等は特に慎重に

詳細は [`docs/06-ethics-and-limits.md`](06-ethics-and-limits.md) を必読。

次: [`04-run-extraction.md`](04-run-extraction.md)
