# data/ ディレクトリ

このディレクトリの内容は **すべて `src/prepare_data.py` および `src/train_lora.py` で生成されます** — Git には commit しません（`.gitignore` 済み）。

## 実行後に生成されるファイル

| ファイル | 内容 | 用途 |
|---|---|---|
| `train.jsonl` | dolly-ja からサンプルした chat 形式データ（各行 = 1 会話）| 訓練入力 |
| `train.provenance.json` | データの出所・ライセンス・PII 確認記録 | 再現性・コンプライアンス |
| `eval_prompts.json` | ベース vs LoRA 比較用プロンプト 10 件 | `compare.py` の入力 |
| `adapter/final/` | LoRA アダプタ（`adapter_config.json` + `adapter_model.safetensors`）+ tokenizer | 推論・共有 |
| `adapter/final/metrics.json` | 訓練終了時の指標サマリ (train_loss, eval_loss) | 結果集計 |
| `adapter/checkpoint-*` | epoch ごとの中間チェックポイント | Spot 中断後の再開用 |
| `adapter/manifest.json` | SHA-256 ファイルハッシュ、モデル/データセット revision、ライセンス情報 | 整合性検証・監査 |

> **注**: `adapter/train.log` ファイルは自動生成されません。詳細ログは `metrics.json` と AML Studio の `std_log.txt` を参照してください。

## データセットについて

- **Source**: [kunishou/databricks-dolly-15k-ja](https://huggingface.co/datasets/kunishou/databricks-dolly-15k-ja)
  - 原文: [databricks/databricks-dolly-15k](https://huggingface.co/datasets/databricks/databricks-dolly-15k) (Databricks, CC BY-SA 3.0)
- **License**: CC BY-SA 3.0（**商用利用可、要 ShareAlike**）
- **Pinned revision**: `6391034b0126850543299cda071dc6281c31a6fb`（SHA-256: `f4f814b77074a864ed15859b354470b10b8d970647165dc4e2ed08a6ff139417`）
- **Size**: 15,015 件（本クイックスタートでは既定 1,000 件サンプル）

## chat 形式への変換

各サンプルを以下の TRL prompt/completion 形式に変換して JSONL 化します:

```json
{
  "prompt": [
    {"role": "system", "content": "デフォルト日本語アシスタント指示"},
    {"role": "user", "content": "<instruction> [\n\n[参考情報]\n<input>]"}
  ],
  "completion": [
    {"role": "assistant", "content": "<output>"}
  ]
}
```

## Completion-only loss の説明と制限

`trl.SFTTrainer` は `prompt`/`completion` 対を受け取ると、**prompt トークンに `-100` ラベル**を付け、**completion（assistant 応答）トークンのみを損失計算の対象**にします。これにより:

- モデルは「入力を暗記する」浪費を避け、応答生成能力の学習にリソースを集中
- 推論時のプロンプト形式と学習時が完全一致し、テスト時ミスマッチを回避

**制限**: Prompt トークンへの損失が計算されないことは、**訓練データのメモリゼーション（暗記）を防ぐわけではありません**。特に少量データや多数 epoch では、モデルが応答を丸暗記する可能性があります。`eval_loss` のモニタリングと `EarlyStoppingCallback` による早期停止が重要です。

参考: [TRL SFTTrainer — completion-only loss](https://huggingface.co/docs/trl/main/en/sft_trainer#train-on-completions-only)

## 実データを使う場合

ドメイン特化データ（研究ノート、Q&A ペアなど）で LoRA する場合、`train.jsonl` を同じ chat 形式で置き換えてください。

**必須**: カスタムデータには `train.provenance.json` の作成が必要です（[docs/07-ethics-and-limits.md](../docs/07-ethics-and-limits.md) 参照）。

```bash
python src/prepare_data.py \
    --dataset my-org/my-dataset \
    --dataset-revision <SHA> \
    --data-provenance data/my-dataset.provenance.json
```

データ量の目安:
- **50〜100 件**: 動作確認・スタイル微調整
- **500〜2000 件**: プロダクション品質のドメイン特化
- **10K+ 件**: フルスクラッチに近い調整
