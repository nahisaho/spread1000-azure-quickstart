# 05 — 自前コーパスへの適用

## 手順

1. 自分の文書を `data/input/` に配置 (`.txt` 形式)
2. `bash src/run.sh` を再実行 → 新規インデックスが構築される

## 対応フォーマット

デフォルトは `.txt` のみ。他フォーマットは前処理が必要:

| 元 | 前処理 |
|---|---|
| PDF | `pdftotext file.pdf file.txt` (Poppler) or Azure Document Intelligence (本 repo 02-document-transcription 参照) |
| Word/Excel | `pandoc` or Document Intelligence Layout |
| HTML | `beautifulsoup4` + `html2text` |
| JSON | `settings.yaml` の `input.file_type: json` に変更 |

## 日本語コーパス

- 日本語入力も動作しますが、GraphRAG のデフォルト prompt は英語。日本語出力を安定させるには:
  - `ragtest/prompts/extract_graph.txt` などの prompt を日本語に手動翻訳、または
  - `graphrag prompt-tune --root ./ragtest --domain "日本史文書"` で自動生成 (別途 LLM コスト発生)

## エンティティタイプのカスタマイズ

`src/settings.yaml`:
```yaml
extract_graph:
  entity_types: [person, organization, place, event, work, concept]
```

分野に応じて調整:
- 化学: `[compound, reaction, catalyst, method, journal_article]`
- 医学: `[disease, drug, gene, symptom, patient_group, trial]`
- 法学: `[case, party, judge, statute, article]`

## スケール指針

| コーパス規模 | 推奨 chat model | 推定コスト |
|---|---|---|
| < 10K words | gpt-4o-mini | < $1 |
| 10K-100K words | gpt-4o-mini | $1-10 |
| 100K-1M words | gpt-4o-mini (夜間バッチ) | $10-100 |
| 1M+ words | gpt-4o-mini + 前処理で絞り込み | $100+ |

## 並列度の調整

`src/settings.yaml`:
```yaml
models:
  default_chat_model:
    concurrent_requests: 4   # AOAI TPM/RPM に応じて調整
    tokens_per_minute: auto
    requests_per_minute: auto
```

Standard S0 は既定で **60 RPM / 60K TPM**。増枠は Azure Portal から「クォータ増加リクエスト」。

## 更新運用

新規文書追加:
```bash
cp new_doc.txt ragtest/input/
python -m graphrag update --root ./ragtest
```

`update` は差分だけ処理するため、フル `index` より安価。

## 応用例

### 化学文献 (SPReAD-1000 想定例)

- 論文コーパスから「化合物 A — 触媒 B — 溶媒 C — 温度 X」を関係抽出
- global search: "この分野で最も報告例の多い反応系は?"
- local search: "化合物 X を合成した論文と条件は?"

### 歴史文書 (人物ネットワーク)

- 日記・書簡から人物 - 場所 - 出来事のネットワーク構築
- global search: "この期間の中心人物と派閥は?"
- ゲフの視覚化: `entities.parquet` + `relationships.parquet` を Gephi や pyvis で描画

### 法学 (判例関係)

- 判例文から「原告 - 被告 - 争点 - 参照法令」を抽出
- 参照ネットワークから重要判例を発見
