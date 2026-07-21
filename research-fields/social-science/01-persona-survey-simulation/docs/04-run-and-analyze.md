# 04 — シミュレーションの実行と分析

## シミュレーション実行

```bash
cd research-fields/social-science/01-persona-survey-simulation
source .venv/bin/activate   # Phase 01 で作成した venv

# 環境変数を読み込み (.env を作成済みの場合)
set -a; source .env; set +a
# または明示的に:
# export AZURE_OPENAI_ENDPOINT="https://aoai-spread-social-01.openai.azure.com/"
# export AZURE_OPENAI_DEPLOYMENT="survey-gpt41mini"

python src/simulate.py \
  --personas data/personas-demo.csv \
  --questions data/questions-demo.csv \
  --output data/responses.csv \
  --seed 42 \
  --temperature 0 \
  --concurrency 4
```

5 ペルソナ × 10 質問 = 50 呼び出しで **約 30 秒 〜 2 分**、コスト **$0.008〜0.02**。

出力 CSV の列：

| 列 | 例 |
|---|---|
| `persona_id` | `p001` |
| `question_id` | `q001` |
| `score` | `4` |
| `label` | `ややそう思う` |
| `short_reason` | `新しい技術に慣れやすい世代のため、日常での活用に前向き` |
| `model` | `gpt-4.1-mini-2025-04-14` |
| `system_fingerprint` | `fp_abc123...` |
| `age_group` / `gender` / ... | (ペルソナ列を join 済み) |

## 分析

**デモの 5 ペルソナ × 10 質問**では、各グループに含まれるペルソナは 1 名程度です。同一ペルソナから取得した 10 回答は独立ではないため、**χ² 検定などの推測統計は妥当ではありません（疑似反復 / pseudoreplication）**。したがって `analyze.py` は既定で**記述統計のみ**を出力します。

```bash
python src/analyze.py \
  --responses data/responses.csv \
  --by age_group \
  --output-dir data/analysis/
```

出力：
- `data/analysis/distribution_age_group.csv` — 年齢層 × スコア のクロス集計 (行内正規化)
- `data/analysis/mean_age_group.csv` — 年齢層別の平均スコア・SD・件数
- `data/analysis/histogram_age_group.png` — 年齢層別スコアヒストグラム

`--by` は `age_group` / `gender` / `region` / `urbanicity` / `education` / `income_bracket` / `political_leaning` から選択可。

### 推測統計 (χ²) を出す場合

`--chi2` は **1 質問のみ**に限定した検定を実行します（`--question` 必須）。複数質問をプールすると同一ペルソナ内の相関で疑似反復が起き p 値が無効になるためです。加えて **各群 5 名以上の独立ペルソナ** を推奨します（下回ると `underpowered_warning` が付きます）。

```bash
python src/analyze.py \
  --responses data/responses.csv \
  --by age_group \
  --output-dir data/analysis/ \
  --chi2 --question q001
```

## 期待される出力 (記述統計モード)

```
=== Personas per age_group ===
age_group
20-29    1
30-39    1
40-49    1
50-59    1
60-69    1

score          1    2    3    4    5
age_group
20-29        0.1  0.2  0.3  0.3  0.1
30-39        0.0  0.1  0.2  0.4  0.3
...

[analyze] χ² test skipped (default). Re-run with --chi2 to include it.
```

> [!NOTE]
> `--chi2` を付けても p 値は**参考値**にすぎません。実質的な統計的結論を出すには、**各グループに独立ペルソナを 5 名以上**、**総サンプル 300+**（Batch API 推奨）で追試してください。

## 再現性の確認

同じ `--seed 42` で 2 回実行し、`system_fingerprint` が同じ場合、多くの回答が一致します。ただし完全な決定性は保証されません。**必ず記録**：

```bash
python src/simulate.py \
  --personas data/personas-demo.csv \
  --questions data/questions-demo.csv \
  --output data/responses_run1.csv \
  --seed 42 --temperature 0 --concurrency 4 \
  --run-id "run_$(date +%Y%m%d_%H%M%S)_1"

python src/simulate.py \
  --personas data/personas-demo.csv \
  --questions data/questions-demo.csv \
  --output data/responses_run2.csv \
  --seed 42 --temperature 0 --concurrency 4 \
  --run-id "run_$(date +%Y%m%d_%H%M%S)_2"

# 再現性チェック
python src/compare_runs.py data/responses_run1.csv data/responses_run2.csv
# → agreement_rate: 0.86 (例)
```

`simulate.py` は `<output>.manifest.json` を副次生成し、モデル ID、デプロイ名、region、temperature、seed、system_fingerprint、実行日時、プロンプトハッシュ、スキーマハッシュを記録します。論文・レポート用に必ず添付してください。

## Studio UI で確認

Azure AI Foundry Portal (`https://ai.azure.com/`) の Playground でも同じデプロイを対話利用できますが、Structured Outputs のバッチ処理には本 CLI スクリプトを使ってください。

次: [`05-cleanup.md`](05-cleanup.md)  
必読: [`06-ethics-and-limits.md`](06-ethics-and-limits.md)
