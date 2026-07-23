# data/ ディレクトリ

このディレクトリの内容は **すべて `src/prepare_data.py` で生成されます** — Git には commit しません（`.gitignore` 済み）。

## 実行後に生成されるファイル

| ファイル | 内容 | 用途 |
|---|---|---|
| `train.jsonl` | dolly-ja からサンプルした chat 形式データ（各行 = 1 会話）| 訓練入力 |
| `eval_prompts.json` | ベース vs LoRA 比較用プロンプト 10 件 | `compare.py` の入力 |
| `adapter/final/` | LoRA アダプタ（`adapter_config.json` + `adapter_model.safetensors`）+ tokenizer | 推論・共有 |
| `adapter/checkpoint-*` | epoch ごとの中間チェックポイント | 途中復帰用 |
| `adapter/train.log` | 訓練ログ（loss, lr） | デバッグ・可視化 |
| `adapter/metrics.json` | 訓練終了時の指標サマリ | 結果集計 |

## データセットについて

- **Source**: [kunishou/databricks-dolly-15k-ja](https://huggingface.co/datasets/kunishou/databricks-dolly-15k-ja)
- **License**: CC BY-SA 3.0（**商用利用可、要 ShareAlike**）
- **Size**: 15,015 件（本クイックスタートでは既定 1,000 件サンプル）
- **フィールド**:
  - `instruction`: ユーザからの指示・質問
  - `input` / `context`: 補助情報（多くは空文字）
  - `output` / `response`: 期待される回答
  - `category`: `open_qa`, `closed_qa`, `general_qa`, `summarization`, `creative_writing`, `brainstorming`, `classification`, `information_extraction` の 8 種

## chat 形式への変換

各サンプルを以下の TRL prompt/completion 形式に変換して JSONL 化します:

```json
{
  "prompt": [
    {"role": "system", "content": "デフォルト日本語アシスタント指示"},
    {"role": "user", "content": "<instruction> [\\n\\n[参考情報]\\n<input>]"}
  ],
  "completion": [
    {"role": "assistant", "content": "<output>"}
  ]
}
```

**なぜ `messages` ではなく `prompt`/`completion` か**:
`trl.SFTTrainer` は `prompt`/`completion` 対を受け取ると **completion-only loss**（assistant 部分のみを学習対象とし、system・user 部分は損失計算から除外）を自動的に有効化します。これにより「入力を暗記する」浪費を避け、モデルは応答生成に集中できます。単一 `messages` フィールドだと系全体に LM loss がかかります。

## 実データを使う場合

ドメイン特化データ（研究ノート、Q&A ペアなど）で LoRA する場合、`train.jsonl` を同じ chat 形式で置き換えてください。目安:

- **50〜100 件**: 最初の動作確認・スタイル微調整には十分
- **500〜2000 件**: プロダクション品質のドメイン特化
- **10K+ 件**: フルスクラッチに近い調整（LoRA では過学習の可能性、`r`, `lora_alpha` を大きく）
