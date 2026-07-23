# 04 — 抽出実行

Document Intelligence (`prebuilt-layout`) で PDF → Markdown、Azure OpenAI Structured Outputs で Markdown → JSON。

## 抽出

```bash
cd research-fields/social-science/02-document-structuring
source .venv/bin/activate
set -a; source .env; set +a

# 判決文
python src/extract.py \
  --input data/demo-court.pdf \
  --schema court \
  --output data/output/demo-court.json

# 工場名簿
python src/extract.py \
  --input data/demo-factory.pdf \
  --schema factory \
  --output data/output/demo-factory.json

# 画像化された工場名簿 (OCR テスト、pdf2image インストール時のみ生成される)
if [ -f data/demo-factory-scanned.pdf ]; then
  python src/extract.py \
    --input data/demo-factory-scanned.pdf \
    --schema factory \
    --output data/output/demo-factory-scanned.json
else
  echo "demo-factory-scanned.pdf not generated (pdf2image/poppler not installed). See docs/01-prerequisites.md."
fi
```

`data/output/` の中身：

- `demo-court.json` — 抽出結果 JSON
- `demo-court.markdown.txt` — Doc Intelligence の Markdown 中間出力 (デバッグ用)
- `demo-court.manifest.json` — メタデータ (モデル、fingerprint、ページ数、コスト、実行日時)

## 期待される出力

```jsonc
// demo-court.json (例)
{
  "case_number": "令和8年 (ワ) 第12345号",
  "court": "東京地方裁判所民事第32部",
  "date": "2026-05-15",
  "judges": ["山田太郎", "佐藤花子", "鈴木一郎"],
  "parties": ["原告 株式会社サンプル商事", "被告 架空製造株式会社"],
  "holding": "被告は原告に対し金3000万円及びこれに対する令和8年1月1日から支払済みまで年6分の割合による金員を支払え。",
  "reasoning_summary": "…",
  "source_page_range": "1-2"
}
```

## 抽出結果の検証

```bash
# 生成された answer.json と比較 (正解データ付き PDF のみ)
# 構造化フィールド (完全一致想定) と、要約など LLM 表現が揺れるフィールド (存在確認 + 長さ範囲)
python -c "
import json
a = json.load(open('data/demo-court.answer.json'))
b = json.load(open('data/output/demo-court.json'))
LENIENT = {'reasoning_summary': (100, 800), 'holding': (30, 500)}
for k in a:
    if k in LENIENT:
        lo, hi = LENIENT[k]
        val = b.get(k) or ''
        match = '≈' if lo <= len(val) <= hi else '✗'
        print(f'{match} {k}: len={len(val)} (expected {lo}-{hi} chars)')
    else:
        match = '✓' if a[k] == b.get(k) else '✗'
        print(f'{match} {k}: {b.get(k)!r} (expected: {a[k]!r})')
"
```

## コスト確認

```bash
cat data/output/demo-court.manifest.json | python -m json.tool | grep -E '(pages|tokens|cost)'
```

期待値：
- 2 ページ × $10/1000 = $0.02
- ~5K input + ~500 output tokens ≈ $0.006

## デバッグ

Markdown 中間出力を見ると、Doc Intelligence が実際に何を認識したか確認できます：

```bash
head -50 data/output/demo-court.markdown.txt
```

Structured Outputs の refusal やスキーマ検証エラーは stderr に出力されます。詳細ログは `--verbose` を付けてください。

## 表付き文書の注意

`prebuilt-layout` は表を HTML `<table>` として Markdown に埋め込みます。**複数ページに跨る表は別 `table` オブジェクトに分割される**ため、本デモの `src/extract.py` は個別の `table` を LLM 用 Markdown にそのまま渡すだけで、機械的な結合処理は行いません。実文書で 3 ページ以上の連続表を扱う場合は、[Cross-page table merge sample](https://github.com/Azure-Samples/document-intelligence-code-samples/blob/main/Python%28v4.0%29/Retrieval_Augmented_Generation_%28RAG%29_samples/sample_identify_and_merge_cross_page_tables.py) を参考に列数と `bounding_regions` で結合するロジックを追加してください。

次: [`05-cleanup.md`](05-cleanup.md)  
必読: [`06-ethics-and-limits.md`](06-ethics-and-limits.md)
