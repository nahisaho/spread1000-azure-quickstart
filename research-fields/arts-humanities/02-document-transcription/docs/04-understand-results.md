# 04 — 結果の解釈

## Metadata JSON の各フィールド

| フィールド | 意味 | 空/null になりやすいケース |
|---|---|---|
| `title` | 文書題目の LLM 推定 | 題目が本文中に明示されていない |
| `author` | 著者/筆者 | 匿名文書 (御触書等) |
| `date_estimated` | 推定年代 | 年月表記のない断簡 |
| `document_type` | 種別 (書簡, 記録, 御触書 等) | 常に埋まる |
| `key_topics` | 主要トピック 5 件 | 内容が具体的なほど埋まる |
| `summary` | 200 字要約 | 常に埋まる |
| `difficult_passages` | 判読困難と推定される箇所 | LLM が確信を持てない箇所を挙げる |

## OCR Markdown (`_ocr.md`) の見方

- 段落構造、リスト、表が Markdown 記号で表現される
- 表は `| col1 | col2 |` 形式で復元される
- **手書き文字は精度が大きく落ちる** (印刷木版 > 楷書手書き > 崩し字)

## 崩し字対応

- Document Intelligence prebuilt-layout は現代活字・楷書までは対応
- **崩し字 (草書、変体仮名)** は精度大幅低下
- 代替: **みを (Miwo)** [https://miwo.ninjal.ac.jp/] は崩し字 OCR 専用モデル (無料)
- 併用パターン: 崩し字を Miwo → 得られた翻刻テキストを Azure OpenAI で構造化

## LLM の Hallucination チェック

- `date_estimated` が本文にない年号を勝手に補完することがある
- **必ず元 PDF と照合**、または「推定根拠」を LLM に述べさせる (プロンプト追加)
- 信頼性が critical なら `temperature=0` + system prompt で「根拠がない場合は必ず null」を強調
