# 03 — ペルソナ・質問の準備

## デモデータ

このシナリオでは **5 ペルソナ × 10 質問 = 50 シミュレーション** のデモデータを同梱しています：

- [`data/personas-demo.csv`](../data/personas-demo.csv) — 5 架空ペルソナ
- [`data/questions-demo.csv`](../data/questions-demo.csv) — 10 Likert 5 段階質問

> [!IMPORTANT]
> ペルソナは**完全に架空**で、実在人物データや個人情報を一切含みません (CC0)。

## ペルソナスキーマ

| 列 | 例 | 説明 |
|---|---|---|
| `persona_id` | `p001` | 一意 ID |
| `age_group` | `30-39` | 年齢層 (18-29 / 30-39 / 40-49 / 50-59 / 60-69 / 70+) |
| `gender` | `女性` | 性別 (自由記述) |
| `region` | `関東` | 地方 (関東/近畿/中部/…) |
| `urbanicity` | `urban` | urban / suburban / rural |
| `education` | `大学卒` | 教育歴 |
| `employment_status` | `フルタイム` | 就業形態 |
| `occupation` | `会社員 (事務)` | 職業 |
| `income_bracket` | `500-700万円` | 世帯年収レンジ |
| `political_leaning` | 空欄 OK | 政治志向 (任意) |
| `values` | `安定志向;家族優先` | 価値観キーワード (セミコロン区切り、任意) |
| `additional_context` | 空欄 OK | その他自由記述 (任意) |

> [!TIP]
> `political_leaning` を含めるとモデルが偏った回答を作りやすくなります。実験目的でない限り空欄推奨。

## 質問スキーマ

| 列 | 例 |
|---|---|
| `question_id` | `q001` |
| `question_text` | `日常生活で AI 技術の利用が増えることは望ましい。` |
| `category` | `tech_attitude` (分析時のグルーピング用、任意) |

Likert 5 段階アンカーは全質問共通で固定：

- `1: まったくそう思わない`
- `2: あまりそう思わない`
- `3: どちらともいえない`
- `4: ややそう思う`
- `5: とてもそう思う`

## 自分のペルソナ・質問を使う

CSV を `data/my-personas.csv` / `data/my-questions.csv` として保存し、次章のシミュレーション実行時に `--personas` / `--questions` オプションで指定します：

```bash
python src/simulate.py \
  --personas data/my-personas.csv \
  --questions data/my-questions.csv \
  --output data/responses.csv
```

## 妥当性の目安

- ペルソナ 5-20 程度 → デモ・パイロット向け
- 20-100 → 予備的探索 (統計検定は参考値)
- 100+ → 本格的比較 (Batch API 推奨)

> [!IMPORTANT]
> **どのサンプルサイズでも、これは実人間データではありません**。人間被験者との比較追試が必要です。詳細は [`docs/06-ethics-and-limits.md`](06-ethics-and-limits.md)。

次: [`04-run-and-analyze.md`](04-run-and-analyze.md)
